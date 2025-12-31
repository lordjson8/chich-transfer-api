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

from .models import KYCProfile, KYCDocument, KYCVerificationLog,KYCLevel, KYCDocumentType
from .serializers import (
    KYCProfileSerializer,
    CreateKYCProfileSerializer,
    UploadKYCDocumentSerializer,
    KYCDocumentSerializer,
    DocumentSide,
    KYCLevelRequirementsSerializer,
    DocumentCompletenessSerializer
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


# apps/kyc/views.py

# apps/kyc/views.py

class KYCDocumentUploadView(APIView):
    """Upload KYC documents including selfie"""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = [KYCThrottle]
    
    @transaction.atomic
    def post(self, request):
        """
        Upload KYC document
        
        POST /api/kyc/documents/upload/
        Content-Type: multipart/form-data
        
        For selfie:
        {
            "document_type": "selfie",
            "document_file": <image file>
        }
        
        For two-sided documents (National ID, Driver's License):
        {
            "document_type": "national_id",
            "document_side": "front",  # or "back"
            "document_file": <file>,
            "document_number": "CM123456789",
            "issue_date": "2020-01-01",
            "expiry_date": "2030-01-01"
        }
        
        For single-sided documents (Passport, Proof of Address):
        {
            "document_type": "passport",
            "document_file": <file>,
            "document_number": "P123456789",
            ...
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
        
        document_type = serializer.validated_data['document_type']
        document_side = serializer.validated_data.get('document_side', DocumentSide.SINGLE)
        
        # For selfie, only allow one upload
        if KYCDocument.is_selfie(document_type):
            existing_selfie = KYCDocument.objects.filter(
                kyc_profile=kyc_profile,
                document_type=KYCDocumentType.SELFIE,
            ).first()
            
            if existing_selfie:
                # Replace old selfie
                existing_selfie.document_file.delete()
                existing_selfie.delete()
        else:
            # Check if this side already exists
            existing_doc = KYCDocument.objects.filter(
                kyc_profile=kyc_profile,
                document_type=document_type,
                document_side=document_side,
            ).first()
            
            if existing_doc:
                # Replace old document
                existing_doc.document_file.delete()
                existing_doc.delete()
        
        document = serializer.save(kyc_profile=kyc_profile)
        
        # Log action
        action_desc = 'Selfie' if KYCDocument.is_selfie(document_type) else f'{document.get_document_type_display()} ({document.get_document_side_display()})'
        
        KYCVerificationLog.objects.create(
            kyc_profile=kyc_profile,
            action='document_added',
            reason=f'Uploaded {action_desc}',
            ip_address=get_client_ip(request)
        )
        
        # Check completeness
        if KYCDocument.is_selfie(document_type):
            completeness = {
                'complete': True,
                'has_front': True,
                'has_back': True,
            }
        else:
            completeness = KYCDocument.get_document_completeness(
                kyc_profile, document_type
            )
        
        logger.info(
            f"Document uploaded for user: {request.user.id} - "
            f"Type: {document_type}, Side: {document_side}"
        )
        
        doc_serializer = KYCDocumentSerializer(document)
        
        return Response({
            'success': True,
            'message': 'Document uploaded successfully',
            'data': {
                **doc_serializer.data,
                'completeness': completeness,
            }
        }, status=status.HTTP_201_CREATED)


class KYCLevelRequirementsView(APIView):
    """Check requirements for KYC level upgrade"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Check requirements for target KYC level
        
        POST /api/kyc/level-requirements/
        {
            "target_level": "advanced"
        }
        """
        try:
            kyc_profile = request.user.kyc_profile
        except KYCProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'KYC profile not found',
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = KYCLevelRequirementsSerializer(
            data=request.data,
            context={'kyc_profile': kyc_profile}
        )
        serializer.is_valid(raise_exception=True)
        
        requirements = serializer.validated_data['requirements']
        target_level = serializer.validated_data['target_level']
        
        return Response({
            'success': True,
            'data': {
                'current_level': kyc_profile.kyc_level,
                'target_level': target_level,
                'target_level_display': dict(KYCLevel.choices)[target_level],
                **requirements,
            }
        }, status=status.HTTP_200_OK)

class KYCDocumentCompletenessView(APIView):
    """Check if document upload is complete"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Check document completeness
        
        POST /api/kyc/documents/completeness/
        {
            "document_type": "national_id"
        }
        """
        try:
            kyc_profile = request.user.kyc_profile
        except KYCProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'KYC profile not found',
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DocumentCompletenessSerializer(
            data=request.data,
            context={'kyc_profile': kyc_profile}
        )
        serializer.is_valid(raise_exception=True)
        
        completeness = serializer.validated_data['completeness']
        document_type = serializer.validated_data['document_type']
        
        return Response({
            'success': True,
            'data': {
                'document_type': document_type,
                'requires_both_sides': KYCDocument.requires_both_sides(document_type),
                **completeness,
            }
        }, status=status.HTTP_200_OK)

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
