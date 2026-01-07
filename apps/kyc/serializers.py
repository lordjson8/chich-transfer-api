# apps/kyc/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import KYCProfile, KYCDocument,DocumentSide, KYCLevel,KYCDocumentType,KYCVerificationLog,KYCVerificationStatus
import hashlib


# class KYCDocumentSerializer(serializers.ModelSerializer):
#     """Serialize KYC documents"""
    
#     document_type_display = serializers.CharField(
#         source='get_document_type_display',
#         read_only=True
#     )
#     document_side_display = serializers.CharField(
#         source='get_document_side_display',
#         read_only=True
#     )
#     status_display = serializers.CharField(
#         source='get_status_display',
#         read_only=True
#     )
#     is_expired = serializers.SerializerMethodField()
#     requires_both_sides = serializers.SerializerMethodField()
    
#     class Meta:
#         model = KYCDocument
#         fields = [
#             'id',
#             'document_type',
#             'document_type_display',
#             'document_side',
#             'document_side_display',
#             'document_number',
#             'issue_date',
#             'expiry_date',
#             'is_expired',
#             'status',
#             'status_display',
#             'requires_both_sides',
#             'created_at',
#         ]
#         read_only_fields = ['id', 'status', 'created_at']
    
#     def get_is_expired(self, obj):
#         return obj.is_expired()
    
#     def get_requires_both_sides(self, obj):
#         return KYCDocument.requires_both_sides(obj.document_type)

class KYCDocumentSerializer(serializers.ModelSerializer):
    """Serialize KYC documents"""
    
    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    document_side_display = serializers.CharField(
        source='get_document_side_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_expired = serializers.SerializerMethodField()
    requires_selfie = serializers.SerializerMethodField()
    
    class Meta:
        model = KYCDocument
        fields = [
            'id',
            'document_type',
            'document_type_display',
            'document_side',
            'document_side_display',
            'document_number',
            'issue_date',
            'expiry_date',
            'is_expired',
            'status',
            'status_display',
            'requires_selfie',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_requires_selfie(self, obj):
        return KYCDocument.requires_selfie(obj.document_type)

class KYCProfileSerializer(serializers.ModelSerializer):
    """Serialize KYC profile with document requirements"""
    
    kyc_level_display = serializers.CharField(
        source='get_kyc_level_display',
        read_only=True
    )
    verification_status_display = serializers.CharField(
        source='get_verification_status_display',
        read_only=True
    )
    documents = KYCDocumentSerializer(many=True, read_only=True)
    transaction_limits = serializers.SerializerMethodField()
    level_requirements = serializers.SerializerMethodField()  # NEW
    
    class Meta:
        model = KYCProfile
        fields = [
            'id',
            'first_name',
            'last_name',
            'middle_name',
            'date_of_birth',
            'gender',
            'nationality',
            'address_line_1',
            'address_line_2',
            'city',
            'state_province',
            'postal_code',
            'country',
            'kyc_level',
            'kyc_level_display',
            'verification_status',
            'verification_status_display',
            'is_verified',
            'submitted_at',
            'verified_at',
            'rejected_at',
            'rejection_reason',
            'documents',
            'transaction_limits',
            'level_requirements',  # NEW
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'kyc_level',
            'verification_status',
            'is_verified',
            'submitted_at',
            'verified_at',
            'rejected_at',
            'rejection_reason',
            'created_at',
            'updated_at',
        ]
    
    def get_transaction_limits(self, obj):
        return obj.get_transaction_limit()
    
    def get_level_requirements(self, obj):
        """Get requirements for next KYC level"""
        current_level = obj.kyc_level
        
        level_order = [KYCLevel.BASIC, KYCLevel.INTERMEDIATE, KYCLevel.ADVANCED]
        current_index = level_order.index(current_level)
        
        if current_index < len(level_order) - 1:
            next_level = level_order[current_index + 1]
            requirements = KYCDocument.check_level_requirements(obj, next_level)
            return {
                'next_level': next_level,
                'next_level_display': dict(KYCLevel.choices)[next_level],
                **requirements,
            }
        
        return {
            'next_level': None,
            'next_level_display': 'Maximum level reached',
            'eligible': True,
            'missing_documents': [],
            'uploaded_documents': [],
        }



class CreateKYCProfileSerializer(serializers.ModelSerializer):
    """Create/Update KYC profile"""
    
    class Meta:
        model = KYCProfile
        fields = [
            'first_name',
            'last_name',
            'middle_name',
            'date_of_birth',
            'gender',
            'nationality',
            'address_line_1',
            'address_line_2',
            'city',
            'state_province',
            'postal_code',
            'country',
        ]
    
    def validate_date_of_birth(self, value):
        """Validate user is at least 18 years old"""
        from datetime import date
        today = date.today()
        age = today.year - value.year - (
            (today.month, today.day) < (value.month, value.day)
        )
        
        if age < 18:
            raise serializers.ValidationError(
                "You must be at least 18 years old to complete KYC."
            )
        
        return value






class UploadKYCDocumentSerializer(serializers.ModelSerializer):
    """Upload KYC document - back is optional, selfie required for ID docs"""
    
    class Meta:
        model = KYCDocument
        fields = [
            'document_type',
            'document_side',
            'document_file',
            'document_number',
            'issue_date',
            'expiry_date',
        ]
    
    def validate(self, attrs):
        """Validate document upload"""
        document_type = attrs.get('document_type')
        document_side = attrs.get('document_side', DocumentSide.SINGLE)
        
        # Selfie should always be SINGLE
        if KYCDocument.is_selfie(document_type):
            attrs['document_side'] = DocumentSide.SINGLE
            attrs['document_number'] = ''
            attrs['issue_date'] = None
            attrs['expiry_date'] = None
        
        # ID documents (national_id, drivers_license, passport)
        elif KYCDocument.requires_selfie(document_type):
            # Only allow 'front' or 'back' - default to 'front' if not specified
            if document_side == DocumentSide.SINGLE:
                attrs['document_side'] = DocumentSide.FRONT
            
            if document_side not in [DocumentSide.FRONT, DocumentSide.BACK]:
                attrs['document_side'] = DocumentSide.FRONT
        
        # Other documents (proof_of_address, bank_statement)
        else:
            attrs['document_side'] = DocumentSide.SINGLE
        
        return attrs
    
    def validate_document_file(self, value):
        """Validate file size and type"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "File size must not exceed 10MB."
            )
        
        # Check file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Only PDF, JPEG, and PNG files are allowed."
            )
        
        # Selfie must be image (not PDF)
        document_type = self.initial_data.get('document_type')
        if document_type == KYCDocumentType.SELFIE and value.content_type == 'application/pdf':
            raise serializers.ValidationError(
                "Selfie must be an image (JPEG or PNG), not PDF."
            )
        
        return value
    
    def create(self, validated_data):
        """Create document with file hash"""
        document_file = validated_data['document_file']
        
        # Calculate file hash
        import hashlib
        file_hash = hashlib.sha256()
        for chunk in document_file.chunks():
            file_hash.update(chunk)
        
        validated_data['file_hash'] = file_hash.hexdigest()
        validated_data['file_size'] = document_file.size
        
        return super().create(validated_data)




class DocumentCompletenessSerializer(serializers.Serializer):
    """Check document upload completeness - back optional, selfie required"""
    
    document_type = serializers.ChoiceField(choices=KYCDocumentType.choices)
    
    def validate(self, attrs):
        kyc_profile = self.context['kyc_profile']
        document_type = attrs['document_type']
        
        completeness = KYCDocument.get_document_completeness(
            kyc_profile, document_type
        )
        
        attrs['completeness'] = completeness
        return attrs


class KYCLevelRequirementsSerializer(serializers.Serializer):
    """Check requirements for KYC level upgrade"""
    
    target_level = serializers.ChoiceField(choices=KYCLevel.choices)
    
    def validate(self, attrs):
        kyc_profile = self.context['kyc_profile']
        target_level = attrs['target_level']
        
        requirements = KYCDocument.check_level_requirements(
            kyc_profile, target_level
        )
        
        attrs['requirements'] = requirements
        return attrs



# class DocumentCompletenessSerializer(serializers.Serializer):
#     """Check document upload completeness"""
    
#     document_type = serializers.ChoiceField(choices=KYCDocumentType.choices)
    
#     def validate(self, attrs):
#         kyc_profile = self.context['kyc_profile']
#         document_type = attrs['document_type']
        
#         completeness = KYCDocument.get_document_completeness(
#             kyc_profile, document_type
#         )
        
#         attrs['completeness'] = completeness
#         return attrs

