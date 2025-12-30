# apps/kyc/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import KYCProfile, KYCDocument, KYCLevel
import hashlib


class KYCDocumentSerializer(serializers.ModelSerializer):
    """Serialize KYC documents"""
    
    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = KYCDocument
        fields = [
            'id',
            'document_type',
            'document_type_display',
            'document_number',
            'issue_date',
            'expiry_date',
            'is_expired',
            'status',
            'status_display',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()


class KYCProfileSerializer(serializers.ModelSerializer):
    """Serialize KYC profile"""
    
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
    """Upload KYC document"""
    
    class Meta:
        model = KYCDocument
        fields = [
            'document_type',
            'document_file',
            'document_number',
            'issue_date',
            'expiry_date',
        ]
    
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
        
        return value
    
    def create(self, validated_data):
        """Create document with file hash"""
        document_file = validated_data['document_file']
        
        # Calculate file hash
        file_hash = hashlib.sha256()
        for chunk in document_file.chunks():
            file_hash.update(chunk)
        
        validated_data['file_hash'] = file_hash.hexdigest()
        validated_data['file_size'] = document_file.size
        
        return super().create(validated_data)
