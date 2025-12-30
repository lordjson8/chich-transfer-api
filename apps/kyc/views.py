from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.db import transaction
import logging

from .models import KYCProfile, KYCDocument, KYCVerificationLog
from .serializers import (
    KYCProfileSerializer,
    CreateKYCProfileSerializer,
    UploadKYCDocumentSerializer,
    KYCDocumentSerializer,
)

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class KYCThrottle(UserRateThrottle):
    """5 KYC submissions per hour"""
    scope = 'kyc'


class KYCProfileView(APIView):
    """Get or create KYC profile"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get user's KYC profile
        
        GET /api/kyc/profile/
        """
        try:
            kyc_profile = request.user.kyc_profile
        except KYCProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'KYC profile not found',
                'error_code': 'KYC_NOT_FOUND',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = KYCProfileSerializer(kyc_profile)
        
        return Response({
            'success': True,
            'message': 'KYC profile retrieved',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    @transaction.atomic
    def post(self, request):
        """
        Create or update KYC profile
        
        POST /api/kyc/profile/
        {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "nationality": "Cameroonian",
            "address_line_1": "123 Main St",
            "city": "Douala",
            "state_province": "Littoral",
            "postal_code": "2700",
            "country": "Cameroon"
        }
        """
        serializer = CreateKYCProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            kyc_profile = request.user.kyc_profile
            # Update existing profile
            for field, value in serializer.validated_data.items():
                setattr(kyc_profile, field, value)
            kyc_profile.save()
            
            action = 'resubmitted'
        except KYCProfile.DoesNotExist:
            # Create new profile
            kyc_profile = KYCProfile.objects.create(
                user=request.user,
                **serializer.validated_data
            )
            action = 'submitted'
        
        # Mark as submitted
        kyc_profile.submitted_at = timezone.now()
        kyc_profile.verification_status = 'under_review'
        kyc_profile.save(update_fields=['submitted_at', 'verification_status'])
        
        # Log action
        KYCVerificationLog.objects.create(
            kyc_profile=kyc_profile,
            action=action,
            ip_address=get_client_ip(request)
        )
        
        logger.info(f"KYC profile {action} for user: {request.user.id}")
        
        response_serializer = KYCProfileSerializer(kyc_profile)
        
        return Response({
            'success': True,
            'message': f'KYC profile {action} for review',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)


class KYCDocumentUploadView(APIView):
    """Upload KYC documents"""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = [KYCThrottle]
    
    @transaction.atomic
    def post(self, request):
        """
        Upload KYC document
        
        POST /api/kyc/documents/upload/
        Content-Type: multipart/form-data
        
        {
            "document_type": "national_id",
            "document_file": <file>,
            "document_number": "12345678",
            "issue_date": "2020-01-01",
            "expiry_date": "2025-01-01"
        }
        """
        try:
            kyc_profile = request.user.kyc_profile
        except KYCProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Complete your basic KYC profile first',
                'error_code': 'KYC_PROFILE_NOT_FOUND',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = UploadKYCDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if document type already exists
        existing_doc = KYCDocument.objects.filter(
            kyc_profile=kyc_profile,
            document_type=serializer.validated_data['document_type'],
            status='approved'
        ).first()
        
        if existing_doc:
            return Response({
                'success': False,
                'error': f'{serializer.validated_data["document_type"]} already verified',
                'error_code': 'DOCUMENT_ALREADY_VERIFIED',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        document = serializer.save(kyc_profile=kyc_profile)
        
        # Log action
        KYCVerificationLog.objects.create(
            kyc_profile=kyc_profile,
            action='document_added',
            reason=f'Uploaded {document.get_document_type_display()}',
            ip_address=get_client_ip(request)
        )
        
        logger.info(
            f"Document uploaded for user: {request.user.id} - Type: {document.document_type}"
        )
        
        doc_serializer = KYCDocumentSerializer(document)
        
        return Response({
            'success': True,
            'message': 'Document uploaded successfully',
            'data': doc_serializer.data
        }, status=status.HTTP_201_CREATED)


class KYCDocumentsListView(APIView):
    """List user's KYC documents"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        List all KYC documents
        
        GET /api/kyc/documents/
        """
        try:
            kyc_profile = request.user.kyc_profile
        except KYCProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'KYC profile not found',
            }, status=status.HTTP_404_NOT_FOUND)
        
        documents = kyc_profile.documents.all()
        serializer = KYCDocumentSerializer(documents, many=True)
        
        return Response({
            'success': True,
            'message': 'Documents retrieved',
            'data': serializer.data,
            'count': documents.count()
        }, status=status.HTTP_200_OK)


class KYCVerificationStatusView(APIView):
    """Check KYC verification status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get KYC verification status
        
        GET /api/kyc/status/
        """
        try:
            kyc_profile = request.user.kyc_profile
        except KYCProfile.DoesNotExist:
            return Response({
                'success': True,
                'data': {
                    'is_verified': False,
                    'kyc_level': 'basic',
                    'verification_status': 'pending',
                    'needs_kyc': True,
                    'transaction_limits': {
                        'monthly_limit': 500_000,
                        'daily_limit': 100_000,
                        'transaction_limit': 50_000,
                    }
                }
            }, status=status.HTTP_200_OK)
        
        serializer = KYCProfileSerializer(kyc_profile)
        
        return Response({
            'success': True,
            'data': {
                'is_verified': kyc_profile.is_verified(),
                'kyc_level': kyc_profile.kyc_level,
                'verification_status': kyc_profile.verification_status,
                'needs_kyc': kyc_profile.verification_status == 'pending',
                'verification_details': serializer.data,
                'transaction_limits': kyc_profile.get_transaction_limit(),
            }
        }, status=status.HTTP_200_OK)
