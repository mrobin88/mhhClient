"""
Views for Worker Portal API
Provides endpoints for workers to access their assignments, submit call-outs, and manage service requests
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from datetime import date, timedelta, datetime
import logging

from .models import Client
from .models_extensions import (
    WorkerAccount, WorkAssignment, ClientAvailability, 
    ServiceRequest, WorkSite, CallOutLog
)
from .serializers import (
    WorkerLoginSerializer, WorkerAccountSerializer,
    WorkerAssignmentSerializer, WorkAssignmentSerializer,
    ClientAvailabilitySerializer, ServiceRequestSerializer,
    WorkerServiceRequestSerializer, CallOutSerializer,
    WorkSiteSerializer
)

logger = logging.getLogger(__name__)


# Simple session-based authentication token
class WorkerSession:
    """Simple session storage for worker authentication"""
    _sessions = {}  # In production, use Redis or database
    
    @classmethod
    def create_session(cls, worker_account):
        """Create a new session for a worker"""
        import uuid
        token = str(uuid.uuid4())
        cls._sessions[token] = {
            'worker_account_id': worker_account.id,
            'client_id': worker_account.client.id,
            'created_at': timezone.now()
        }
        return token
    
    @classmethod
    def get_session(cls, token):
        """Get session data by token"""
        return cls._sessions.get(token)
    
    @classmethod
    def delete_session(cls, token):
        """Delete a session"""
        if token in cls._sessions:
            del cls._sessions[token]


@api_view(['POST'])
def worker_login(request):
    """
    Worker login endpoint - authenticate with phone + PIN
    
    POST /api/worker/login/
    {
        "phone": "415-555-1234",
        "pin": "1234"
    }
    
    Returns:
    {
        "token": "session-token",
        "worker_account": {...},
        "message": "Login successful"
    }
    """
    serializer = WorkerLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        worker_account = serializer.validated_data['worker_account']
        token = WorkerSession.create_session(worker_account)
        
        return Response({
            'token': token,
            'worker_account': WorkerAccountSerializer(worker_account).data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def worker_logout(request):
    """
    Worker logout endpoint
    
    POST /api/worker/logout/
    Headers: Authorization: Token <session-token>
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    WorkerSession.delete_session(token)
    
    return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def worker_profile(request):
    """
    Get worker profile information
    
    GET /api/worker/profile/
    Headers: Authorization: Token <session-token>
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    session = WorkerSession.get_session(token)
    
    if not session:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        worker_account = WorkerAccount.objects.select_related('client').get(id=session['worker_account_id'])
        return Response(WorkerAccountSerializer(worker_account).data)
    except WorkerAccount.DoesNotExist:
        return Response({'error': 'Worker account not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def worker_assignments(request):
    """
    Get worker's assignments
    
    GET /api/worker/assignments/?filter=upcoming|today|past
    Headers: Authorization: Token <session-token>
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    session = WorkerSession.get_session(token)
    
    if not session:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
    
    client_id = session['client_id']
    filter_type = request.GET.get('filter', 'upcoming')
    
    today = date.today()
    
    # Base queryset
    assignments = WorkAssignment.objects.filter(
        client_id=client_id
    ).select_related('work_site').order_by('-assignment_date', 'start_time')
    
    # Apply filters
    if filter_type == 'today':
        assignments = assignments.filter(assignment_date=today)
    elif filter_type == 'upcoming':
        assignments = assignments.filter(assignment_date__gte=today)
    elif filter_type == 'past':
        assignments = assignments.filter(assignment_date__lt=today)
    
    serializer = WorkerAssignmentSerializer(assignments, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def worker_confirm_assignment(request, assignment_id):
    """
    Confirm an assignment
    
    POST /api/worker/assignments/<id>/confirm/
    Headers: Authorization: Token <session-token>
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    session = WorkerSession.get_session(token)
    
    if not session:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        assignment = WorkAssignment.objects.get(
            id=assignment_id,
            client_id=session['client_id']
        )
        
        assignment.confirmed_by_client = True
        assignment.confirmed_at = timezone.now()
        if assignment.status == 'pending':
            assignment.status = 'confirmed'
        assignment.save()
        
        return Response({
            'message': 'Assignment confirmed',
            'assignment': WorkerAssignmentSerializer(assignment).data
        })
    except WorkAssignment.DoesNotExist:
        return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def worker_call_out(request):
    """
    Submit a call-out for an assignment
    
    POST /api/worker/call-out/
    {
        "assignment_id": 123,
        "reason": "I'm sick",
        "advance_notice_hours": 4
    }
    Headers: Authorization: Token <session-token>
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    session = WorkerSession.get_session(token)
    
    if not session:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = CallOutSerializer(data=request.data)
    
    if serializer.is_valid():
        assignment_id = serializer.validated_data['assignment_id']
        reason = serializer.validated_data['reason']
        advance_notice_hours = serializer.validated_data['advance_notice_hours']
        
        try:
            assignment = WorkAssignment.objects.get(
                id=assignment_id,
                client_id=session['client_id']
            )
            
            # Update assignment
            assignment.status = 'called_out'
            assignment.called_out_at = timezone.now()
            assignment.callout_reason = reason
            assignment.save()
            
            # Create call-out log
            CallOutLog.objects.create(
                assignment=assignment,
                reported_by='Worker Portal',
                reason=reason,
                advance_notice_hours=advance_notice_hours
            )
            
            return Response({
                'message': 'Call-out submitted successfully',
                'assignment': WorkerAssignmentSerializer(assignment).data
            })
        except WorkAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
def worker_availability(request):
    """
    Get or update worker's availability
    
    GET /api/worker/availability/
    PUT /api/worker/availability/
    Headers: Authorization: Token <session-token>
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    session = WorkerSession.get_session(token)
    
    if not session:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
    
    client_id = session['client_id']
    
    if request.method == 'GET':
        availability = ClientAvailability.objects.filter(client_id=client_id)
        serializer = ClientAvailabilitySerializer(availability, many=True)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Expect array of availability objects
        # [{"day_of_week": "monday", "available": true, "preferred_time_slots": ["6-12"]}, ...]
        availability_data = request.data
        
        if not isinstance(availability_data, list):
            return Response({'error': 'Expected array of availability objects'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update or create availability for each day
        for day_data in availability_data:
            day_of_week = day_data.get('day_of_week')
            if not day_of_week:
                continue
            
            availability, created = ClientAvailability.objects.get_or_create(
                client_id=client_id,
                day_of_week=day_of_week
            )
            
            availability.available = day_data.get('available', True)
            availability.preferred_time_slots = day_data.get('preferred_time_slots', [])
            availability.notes = day_data.get('notes', '')
            availability.save()
        
        # Return updated availability
        updated_availability = ClientAvailability.objects.filter(client_id=client_id)
        serializer = ClientAvailabilitySerializer(updated_availability, many=True)
        return Response(serializer.data)


@api_view(['GET', 'POST'])
def worker_service_requests(request):
    """
    Get worker's service requests or submit a new one
    
    GET /api/worker/service-requests/
    POST /api/worker/service-requests/
    Headers: Authorization: Token <session-token>
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    session = WorkerSession.get_session(token)
    
    if not session:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
    
    client_id = session['client_id']
    
    if request.method == 'GET':
        service_requests = ServiceRequest.objects.filter(
            submitted_by_id=client_id
        ).select_related('work_site').order_by('-created_at')
        
        serializer = ServiceRequestSerializer(service_requests, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = WorkerServiceRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            service_request = serializer.save(submitted_by_id=client_id)
            
            return Response(
                ServiceRequestSerializer(service_request).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def worker_work_sites(request):
    """
    Get list of active work sites
    
    GET /api/worker/work-sites/
    Headers: Authorization: Token <session-token>
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    session = WorkerSession.get_session(token)
    
    if not session:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
    
    work_sites = WorkSite.objects.filter(is_active=True).order_by('name')
    serializer = WorkSiteSerializer(work_sites, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def worker_dashboard(request):
    """
    Get dashboard summary for worker
    
    GET /api/worker/dashboard/
    Headers: Authorization: Token <session-token>
    
    Returns:
    {
        "today_assignments": [...],
        "upcoming_assignments": [...],
        "recent_service_requests": [...],
        "stats": {
            "total_assignments_this_month": 10,
            "completed_assignments": 8,
            "pending_service_requests": 2
        }
    }
    """
    token = request.headers.get('Authorization', '').replace('Token ', '')
    session = WorkerSession.get_session(token)
    
    if not session:
        return Response({'error': 'Invalid or expired session'}, status=status.HTTP_401_UNAUTHORIZED)
    
    client_id = session['client_id']
    today = date.today()
    
    # Today's assignments
    today_assignments = WorkAssignment.objects.filter(
        client_id=client_id,
        assignment_date=today
    ).select_related('work_site')
    
    # Upcoming assignments (next 7 days)
    upcoming_assignments = WorkAssignment.objects.filter(
        client_id=client_id,
        assignment_date__gt=today,
        assignment_date__lte=today + timedelta(days=7)
    ).select_related('work_site').order_by('assignment_date', 'start_time')
    
    # Recent service requests
    recent_service_requests = ServiceRequest.objects.filter(
        submitted_by_id=client_id
    ).select_related('work_site').order_by('-created_at')[:5]
    
    # Stats
    first_day_of_month = today.replace(day=1)
    total_assignments_this_month = WorkAssignment.objects.filter(
        client_id=client_id,
        assignment_date__gte=first_day_of_month,
        assignment_date__lte=today
    ).count()
    
    completed_assignments = WorkAssignment.objects.filter(
        client_id=client_id,
        assignment_date__gte=first_day_of_month,
        assignment_date__lte=today,
        status='completed'
    ).count()
    
    pending_service_requests = ServiceRequest.objects.filter(
        submitted_by_id=client_id,
        status__in=['open', 'acknowledged', 'in_progress']
    ).count()
    
    return Response({
        'today_assignments': WorkerAssignmentSerializer(today_assignments, many=True).data,
        'upcoming_assignments': WorkerAssignmentSerializer(upcoming_assignments, many=True).data,
        'recent_service_requests': ServiceRequestSerializer(recent_service_requests, many=True).data,
        'stats': {
            'total_assignments_this_month': total_assignments_this_month,
            'completed_assignments': completed_assignments,
            'pending_service_requests': pending_service_requests
        }
    })
