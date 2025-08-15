from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Client, CaseNote
from .serializers import ClientSerializer, CaseNoteSerializer
from django.utils import timezone

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'training_interest', 'neighborhood', 'sf_resident', 'employment_status']
    search_fields = ['first_name', 'last_name', 'phone', 'ssn']
    ordering_fields = ['created_at', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['get'])
    def case_notes(self, request, pk=None):
        """Get case notes for a specific client"""
        client = self.get_object()
        case_notes = CaseNote.objects.filter(client=client).order_by('-created_at')
        serializer = CaseNoteSerializer(case_notes, many=True)
        return Response(serializer.data)

class CaseNoteViewSet(viewsets.ModelViewSet):
    queryset = CaseNote.objects.all()
    serializer_class = CaseNoteSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['note_type', 'staff_member', 'client']
    search_fields = ['content', 'staff_member', 'client__first_name', 'client__last_name']
    ordering_fields = ['created_at', 'follow_up_date']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def overdue_followups(self, request):
        """Get case notes with overdue follow-ups"""
        overdue_notes = CaseNote.objects.filter(
            follow_up_date__lt=timezone.now().date()
        ).exclude(follow_up_date__isnull=True)
        serializer = self.get_serializer(overdue_notes, many=True)
        return Response(serializer.data)
