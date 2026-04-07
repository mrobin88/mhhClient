import csv
import io
from datetime import datetime

from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Client, CaseNote, Document, PitStopApplication
from .serializers import ClientSerializer, CaseNoteSerializer, PitStopApplicationSerializer
from .storage import generate_document_sas_url
import logging

from django.utils import timezone

class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing clients with full CRUD operations
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def get_permissions(self):
        # Allow public client registration (create); require auth otherwise
        if self.action in ['create']:
            return [AllowAny()]
        return super().get_permissions()

    def get_authenticators(self):
        # Skip SessionAuthentication (and its CSRF check) for public create
        if getattr(self, 'action', None) == 'create':
            return []
        return super().get_authenticators()

    def create(self, request, *args, **kwargs):
        """
        Accept extra multipart fields for optional documents without breaking
        ClientSerializer validation.

        We persist the extra files in perform_create() via the Document model.
        """
        data = request.data.copy()
        for key in (
            'doc_sf_residency',
            'doc_hs_diploma',
            'doc_id',
            'doc_photo_release',
            'doc_other',
            'doc_other_name',
        ):
            if key in data:
                data.pop(key)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        Public client registration can include optional supporting documents.

        Frontend sends files in multipart form-data:
        - doc_sf_residency
        - doc_hs_diploma
        - doc_id
        - doc_photo_release
        - doc_other (+ optional doc_other_name)
        """
        client = serializer.save()

        files = getattr(self.request, 'FILES', None)
        if not files:
            return

        upload_map = [
            ('doc_sf_residency', 'sf_residency', 'Proof of SF Residency'),
            ('doc_hs_diploma', 'hs_diploma', 'High School Diploma / GED'),
            ('doc_id', 'id', 'Government ID'),
            ('doc_photo_release', 'photo_release', 'Photo Release Form'),
            ('doc_other', 'other', None),
        ]

        uploaded_by = (
            (self.request.user.get_full_name() or self.request.user.username)
            if getattr(self.request, 'user', None) and self.request.user.is_authenticated
            else 'public'
        )

        other_name = (self.request.data.get('doc_other_name') or '').strip()

        for form_key, doc_type, default_title in upload_map:
            f = files.get(form_key)
            if not f:
                continue

            # Store under a client-scoped prefix in blob storage.
            # This keeps documents organized per client.
            try:
                original = f.name
                f.name = f"clients/{client.pk}/{doc_type}/{original}"
            except Exception:
                pass

            title = default_title
            if doc_type == 'other':
                title = other_name or 'Other Document'

            try:
                Document.objects.create(
                    client=client,
                    title=title,
                    doc_type=doc_type,
                    file=f,
                    uploaded_by=uploaded_by,
                )
            except Exception as exc:
                logging.getLogger('clients').warning(
                    'Failed to save supporting document %s for Client %s: %s',
                    doc_type, client.pk, exc
                )
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export all clients to CSV format"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="clients_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # CSV Headers
        writer.writerow([
            'ID', 'First Name', 'Last Name', 'Date of Birth', 'Phone', 'Gender',
            'SF Resident', 'Neighborhood', 'Demographic Info', 'Language',
            'Education Level', 'Employment Status', 'Training Interest',
            'Referral Source', 'Status', 'Staff Name', 'Has Resume',
            'Case Notes Count', 'Documents Count', 'Created At', 'Updated At'
        ])
        
        # Client data rows
        for client in self.get_queryset():
            writer.writerow([
                client.id,
                client.first_name,
                client.last_name,
                client.dob.strftime('%Y-%m-%d') if client.dob else '',
                client.phone,
                client.get_gender_display(),
                client.get_sf_resident_display(),
                client.get_neighborhood_display(),
                client.get_demographic_info_display(),
                client.get_language_display(),
                client.get_highest_degree_display(),
                client.get_employment_status_display(),
                client.get_training_interest_display(),
                client.get_referral_source_display(),
                client.get_status_display(),
                client.staff_name or '',
                'Yes' if client.has_resume else 'No',
                client.case_notes_count,
                client.documents_count,
                client.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                client.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    
    @action(detail=True, methods=['get'])
    def summary_pdf(self, request, pk=None):
        """Generate PDF summary report for a specific client - DISABLED (WeasyPrint removed)"""
        return JsonResponse({
            'error': 'PDF generation is not available. WeasyPrint has been removed from the project.'
        }, status=503)


class CaseNoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing case notes
    """
    queryset = CaseNote.objects.all()
    serializer_class = CaseNoteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter case notes by client if specified"""
        queryset = super().get_queryset()
        client_id = self.request.query_params.get('client', None)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset


@method_decorator(login_required, name='dispatch')
class DocumentDownloadView(View):
    """Secure document download - redirects to Azure SAS URL."""
    
    def get(self, request, pk):
        from django.shortcuts import redirect
        
        document = get_object_or_404(Document, pk=pk)
        
        if not document.file:
            return HttpResponse(
                '<h2>No file attached</h2>'
                '<p>This document record exists but has no file attached.</p>'
                '<p><a href="javascript:history.back()">Go back</a></p>',
                status=404, content_type='text/html'
            )
        
        try:
            sas_url = document.generate_sas_download_url(expiry_minutes=15)
            return redirect(sas_url)
        except FileNotFoundError:
            filename = document.file.name.split('/')[-1]
            edit_url = f'/admin/clients/document/{document.pk}/change/'
            return HttpResponse(
                f'<h2>File Missing from Storage</h2>'
                f'<p>The file <strong>{filename}</strong> is not in Azure Storage.</p>'
                f'<p>It may have been uploaded locally and never synced, or was deleted.</p>'
                f'<h3>To fix:</h3>'
                f'<ol>'
                f'<li><a href="{edit_url}">Edit this document</a></li>'
                f'<li>Click "Choose File" to re-upload</li>'
                f'<li>Click Save</li>'
                f'</ol>'
                f'<p><a href="javascript:history.back()">Go back</a></p>',
                status=404, content_type='text/html'
            )
        except Exception as e:
            logging.getLogger('clients').error('Download failed for Document %s: %s', document.pk, e)
            return HttpResponse(
                f'<h2>Download Error</h2>'
                f'<p>Could not generate download link: {str(e)}</p>'
                f'<p><a href="javascript:history.back()">Go back</a></p>',
                status=500, content_type='text/html'
            )


@method_decorator(login_required, name='dispatch')
class ResumeDownloadView(View):
    """Secure resume download - redirects to Azure SAS URL."""
    
    def get(self, request, pk):
        from django.shortcuts import redirect
        
        client = get_object_or_404(Client, pk=pk)
        
        if not client.resume:
            return HttpResponse(
                '<h2>No Resume</h2>'
                '<p>This client does not have a resume uploaded.</p>'
                '<p><a href="javascript:history.back()">Go back</a></p>',
                status=404, content_type='text/html'
            )
        
        try:
            sas_url = client.resume_download_url
            if not sas_url:
                raise FileNotFoundError("Resume file not found in storage")
            return redirect(sas_url)
        except FileNotFoundError:
            filename = client.resume.name.split('/')[-1]
            edit_url = f'/admin/clients/client/{client.pk}/change/'
            return HttpResponse(
                f'<h2>Resume Missing from Storage</h2>'
                f'<p>The file <strong>{filename}</strong> is not in Azure Storage.</p>'
                f'<p>It may have been uploaded locally and never synced, or was deleted.</p>'
                f'<h3>To fix:</h3>'
                f'<ol>'
                f'<li><a href="{edit_url}">Edit this client</a></li>'
                f'<li>Scroll to Documents section</li>'
                f'<li>Click "Choose File" to re-upload the resume</li>'
                f'<li>Click Save</li>'
                f'</ol>'
                f'<p><a href="javascript:history.back()">Go back</a></p>',
                status=404, content_type='text/html'
            )
        except Exception as e:
            logging.getLogger('clients').error('Resume download failed for Client %s: %s', client.pk, e)
            return HttpResponse(
                f'<h2>Download Error</h2>'
                f'<p>Could not generate download link: {str(e)}</p>'
                f'<p><a href="javascript:history.back()">Go back</a></p>',
                status=500, content_type='text/html'
            )


@require_http_methods(["GET"])
@login_required
def client_dashboard_stats(request):
    """
    API endpoint for dashboard statistics
    """
    stats = {
        'total_clients': Client.objects.count(),
        'active_clients': Client.objects.filter(status='active').count(),
        'pending_clients': Client.objects.filter(status='pending').count(),
        'completed_clients': Client.objects.filter(status='completed').count(),
        'total_case_notes': CaseNote.objects.count(),
        'total_documents': Document.objects.count(),
        'clients_with_resume': Client.objects.exclude(resume='').count(),
    }
    
    return JsonResponse(stats)

    def overdue_followups(self, request):
        """Get case notes with overdue follow-ups"""
        overdue_notes = CaseNote.objects.filter(
            follow_up_date__lt=timezone.now().date()
        ).exclude(follow_up_date__isnull=True)
        serializer = self.get_serializer(overdue_notes, many=True)
        return Response(serializer.data)


class PitStopApplicationViewSet(viewsets.ModelViewSet):
    queryset = PitStopApplication.objects.select_related('client').all()
    serializer_class = PitStopApplicationSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employment_desired', 'can_work_us', 'is_veteran']
    search_fields = ['client__first_name', 'client__last_name', 'position_applied_for']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def report(self, request):
        """Simple report of pit stop applicants for staff/funders"""
        qs = self.get_queryset()
        data = [
            {
                'client': obj.client.full_name,
                'phone': obj.client.phone,
                'email': obj.client.email,
                'position': obj.position_applied_for,
                'start_date': obj.available_start_date,
                'employment_desired': obj.employment_desired,
                'created_at': obj.created_at,
            }
            for obj in qs
        ]
        return Response(data)
