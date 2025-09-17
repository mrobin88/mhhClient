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
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Client, CaseNote, Document, PitStopApplication
from .serializers import ClientSerializer, CaseNoteSerializer, PitStopApplicationSerializer
from .storage import generate_document_sas_url

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
from django.utils import timezone

class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing clients with full CRUD operations
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]
    
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
        """Generate PDF summary report for a specific client"""
        if not WEASYPRINT_AVAILABLE:
            return JsonResponse({
                'error': 'PDF generation not available. WeasyPrint is not installed.'
            }, status=500)
        
        client = self.get_object()
        
        # Get related data
        case_notes = client.casenotes.all()[:10]  # Latest 10 case notes
        documents = client.documents.all()
        
        # Render HTML template
        html_content = render_to_string('clients/client_summary.html', {
            'client': client,
            'case_notes': case_notes,
            'documents': documents,
            'generated_at': datetime.now(),
            'generated_by': request.user.get_full_name() or request.user.username
        })
        
        # Generate PDF
        try:
            pdf_buffer = io.BytesIO()
            HTML(string=html_content).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)
            
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            filename = f"client_summary_{client.first_name}_{client.last_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return JsonResponse({
                'error': f'PDF generation failed: {str(e)}'
            }, status=500)


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
    """
    Secure document download view with SAS URL generation
    """
    
    def get(self, request, pk):
        """Generate and return a secure download URL for the document"""
        try:
            document = get_object_or_404(Document, pk=pk)
            
            # Check if user has permission to access this document
            # You can add more sophisticated permission checking here
            if not request.user.is_authenticated:
                raise Http404("Document not found")
            
            # Generate SAS URL for secure download
            if document.file:
                try:
                    # Extract blob name from file path
                    blob_name = document.file.name
                    sas_url = generate_document_sas_url(blob_name, expiry_minutes=15)
                    
                    return JsonResponse({
                        'download_url': sas_url,
                        'filename': document.title,
                        'expires_in_minutes': 15
                    })
                    
                except Exception as e:
                    return JsonResponse({
                        'error': f'Failed to generate download URL: {str(e)}'
                    }, status=500)
            else:
                return JsonResponse({
                    'error': 'Document file not found'
                }, status=404)
                
        except Document.DoesNotExist:
            raise Http404("Document not found")


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
