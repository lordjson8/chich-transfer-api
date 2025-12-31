# apps/kyc/models.py

from django.db import models
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.utils import timezone
import uuid
from apps.authentication.models import User


class KYCLevel(models.TextChoices):
    """KYC verification levels"""
    BASIC = 'basic', 'Basic'
    INTERMEDIATE = 'intermediate', 'Intermediate'
    ADVANCED = 'advanced', 'Advanced'


class KYCDocumentType(models.TextChoices):
    """Type of documents accepted"""
    NATIONAL_ID = 'national_id', 'National ID'
    PASSPORT = 'passport', 'Passport'
    DRIVERS_LICENSE = 'drivers_license', "Driver's License"
    PROOF_OF_ADDRESS = 'proof_of_address', 'Proof of Address'
    BANK_STATEMENT = 'bank_statement', 'Bank Statement'
    SELFIE = 'selfie', 'Selfie'  # NEW



class KYCVerificationStatus(models.TextChoices):
    """KYC verification status"""
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    UNDER_REVIEW = 'under_review', 'Under Review'

class DocumentSide(models.TextChoices):
    """Document side for front/back uploads"""
    FRONT = 'front', 'Front'
    BACK = 'back', 'Back'
    SINGLE = 'single', 'Single (No back required)'

class KYCProfile(models.Model):
    """User KYC profile - tracks verification status"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='kyc_profile')
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            # ('other', 'Other'),
        ]
    )
    nationality = models.CharField(max_length=100)
    
    # Address Information
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    # Verification Status
    kyc_level = models.CharField(
        max_length=20,
        choices=KYCLevel.choices,
        default=KYCLevel.BASIC
    )
    verification_status = models.CharField(
        max_length=20,
        choices=KYCVerificationStatus.choices,
        default=KYCVerificationStatus.PENDING
    )
    
    # Verification Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    
    # Rejection Details
    rejection_reason = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "KYC Profile"
        verbose_name_plural = "KYC Profiles"
        indexes = [
            models.Index(fields=['user', 'verification_status']),
            models.Index(fields=['kyc_level']),
        ]
    
    def is_verified(self):
        """Check if user is KYC verified"""
        return self.verification_status == KYCVerificationStatus.APPROVED
    
    def get_transaction_limit(self):
        """Get monthly transaction limit based on KYC level"""
        limits = {
            KYCLevel.BASIC: {
                'monthly_limit': 500_000,      # 500k XAF
                'daily_limit': 100_000,        # 100k XAF
                'transaction_limit': 50_000,   # 50k per transaction
            },
            KYCLevel.INTERMEDIATE: {
                'monthly_limit': 2_000_000,    # 2M XAF
                'daily_limit': 500_000,        # 500k XAF
                'transaction_limit': 200_000,  # 200k per transaction
            },
            KYCLevel.ADVANCED: {
                'monthly_limit': 10_000_000,   # 10M XAF
                'daily_limit': 2_000_000,      # 2M XAF
                'transaction_limit': 1_000_000,# 1M per transaction
            },
        }
        return limits.get(self.kyc_level, limits[KYCLevel.BASIC])
    
    def __str__(self):
        return f"KYC Profile - {self.user.email} ({self.kyc_level})"


class KYCDocument(models.Model):
    """Documents submitted for KYC verification"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    document_type = models.CharField(
        max_length=50,
        choices=KYCDocumentType.choices
    )
    
    # NEW: Document side (front/back)
    document_side = models.CharField(
        max_length=10,
        choices=DocumentSide.choices,
        default=DocumentSide.SINGLE
    )
    
    document_file = models.FileField(
        upload_to='kyc_documents/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']
            )
        ]
    )
    
    # Document Details
    document_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Verification
    status = models.CharField(
        max_length=20,
        choices=KYCVerificationStatus.choices,
        default=KYCVerificationStatus.PENDING
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Metadata
    file_size = models.BigIntegerField(help_text="Size in bytes")
    file_hash = models.CharField(max_length=64, db_index=True)  # Remove unique=True
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "KYC Document"
        verbose_name_plural = "KYC Documents"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['kyc_profile', 'document_type', 'document_side']),
            models.Index(fields=['status']),
        ]
        # NEW: Ensure only one front and one back per document type
        unique_together = [['kyc_profile', 'document_type', 'document_side']]
    
    @classmethod
    def requires_both_sides(cls, document_type):
        """Check if document requires front and back"""
        two_sided_documents = [
            KYCDocumentType.NATIONAL_ID,
            KYCDocumentType.DRIVERS_LICENSE,
        ]
        return document_type in two_sided_documents
    
    @classmethod
    def requires_both_sides(cls, document_type):
        """Check if document requires front and back"""
        two_sided_documents = [
            KYCDocumentType.NATIONAL_ID,
            KYCDocumentType.DRIVERS_LICENSE,
        ]
        return document_type in two_sided_documents
    
    @classmethod
    def is_selfie(cls, document_type):
        """Check if document is a selfie"""
        return document_type == KYCDocumentType.SELFIE
    
    @classmethod
    def get_required_documents_for_level(cls, kyc_level):
        """Get required documents for each KYC level"""
        requirements = {
            KYCLevel.BASIC: [],  # Just email + phone
            KYCLevel.INTERMEDIATE: [
                KYCDocumentType.NATIONAL_ID,  # or PASSPORT or DRIVERS_LICENSE
                KYCDocumentType.PROOF_OF_ADDRESS,
            ],
            KYCLevel.ADVANCED: [
                KYCDocumentType.NATIONAL_ID,  # or PASSPORT or DRIVERS_LICENSE
                KYCDocumentType.PROOF_OF_ADDRESS,
                KYCDocumentType.SELFIE,  # NEW: Required for advanced
                KYCDocumentType.BANK_STATEMENT,
            ],
        }
        return requirements.get(kyc_level, [])
    
    @classmethod
    def check_level_requirements(cls, kyc_profile, target_level):
        """
        Check if user has uploaded all required documents for target KYC level
        Returns: {
            'eligible': bool,
            'missing_documents': list,
            'uploaded_documents': list
        }
        """
        required = cls.get_required_documents_for_level(target_level)
        uploaded = cls.objects.filter(
            kyc_profile=kyc_profile,
            status__in=[
                KYCVerificationStatus.PENDING,
                KYCVerificationStatus.UNDER_REVIEW,
                KYCVerificationStatus.APPROVED,
            ]
        ).values_list('document_type', flat=True)
        
        # For ID documents, user needs at least one of: national_id, passport, drivers_license
        id_docs = [
            KYCDocumentType.NATIONAL_ID,
            KYCDocumentType.PASSPORT,
            KYCDocumentType.DRIVERS_LICENSE,
        ]
        
        has_id_doc = any(doc in uploaded for doc in id_docs)
        required_without_id = [doc for doc in required if doc not in id_docs]
        
        missing = []
        if id_docs[0] in required and not has_id_doc:
            missing.append('ID Document (National ID, Passport, or Driver\'s License)')
        
        for doc in required_without_id:
            if doc not in uploaded:
                missing.append(dict(KYCDocumentType.choices)[doc])
        
        return {
            'eligible': len(missing) == 0,
            'missing_documents': missing,
            'uploaded_documents': list(uploaded),
        }
    
    @classmethod
    def get_document_completeness(cls, kyc_profile, document_type):
        """Check if both sides are uploaded for two-sided documents"""
        if not cls.requires_both_sides(document_type):
            return {
                'complete': cls.objects.filter(
                    kyc_profile=kyc_profile,
                    document_type=document_type
                ).exists(),
                'has_front': True,
                'has_back': True,
            }
        
        has_front = cls.objects.filter(
            kyc_profile=kyc_profile,
            document_type=document_type,
            document_side=DocumentSide.FRONT
        ).exists()
        
        has_back = cls.objects.filter(
            kyc_profile=kyc_profile,
            document_type=document_type,
            document_side=DocumentSide.BACK
        ).exists()
        
        return {
            'complete': has_front and has_back,
            'has_front': has_front,
            'has_back': has_back,
        }
    
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
    def __str__(self):
        side_display = f" ({self.get_document_side_display()})" if self.document_side != DocumentSide.SINGLE else ""
        return f"{self.get_document_type_display()}{side_display} - {self.kyc_profile.user.email}"


class KYCVerificationLog(models.Model):
    """Audit log for KYC verification"""
    
    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='verification_logs'
    )
    
    action = models.CharField(
        max_length=50,
        choices=[
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('resubmitted', 'Resubmitted'),
            ('document_added', 'Document Added'),
            ('document_verified', 'Document Verified'),
        ]
    )
    
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kyc_verifications'
    )
    
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "KYC Verification Log"
        verbose_name_plural = "KYC Verification Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.kyc_profile.user.email}"
# apps/core/models.py

from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model with created_at and updated_at timestamps."""
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract base model with soft delete functionality."""
    
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Soft delete this instance."""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
    
    def restore(self):
        """Restore a soft-deleted instance."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
    
    @property
    def is_deleted(self):
        """Check if instance is soft-deleted."""
        return self.deleted_at is not None
