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
    NOT_SUBMITTED = 'not_submitted', 'Not Submitted'
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
    nationality = models.CharField(max_length=100, blank=True)
    
    # Address Information
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Verification Status
    kyc_level = models.CharField(
        max_length=20,
        choices=KYCLevel.choices,
        default=KYCLevel.BASIC
    )
    verification_status = models.CharField(
        max_length=20,
        choices=KYCVerificationStatus.choices,
        default=KYCVerificationStatus.NOT_SUBMITTED
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
        """Check if document requires front and back - BACK IS OPTIONAL NOW"""
        # Return False since back is always optional
        return False
    
    @classmethod
    def requires_selfie(cls, document_type):
        """Check if document type requires a selfie for verification"""
        # All ID documents require selfie for face matching
        requires_selfie_docs = [
            KYCDocumentType.NATIONAL_ID,
            KYCDocumentType.PASSPORT,
            KYCDocumentType.DRIVERS_LICENSE,
        ]
        return document_type in requires_selfie_docs
    
    @classmethod
    def is_selfie(cls, document_type):
        """Check if document is a selfie"""
        return document_type == KYCDocumentType.SELFIE
    
    @classmethod
    def get_document_completeness(cls, kyc_profile, document_type):
        """
        Check if document upload is complete
        - Front is required
        - Back is optional
        - Selfie is required for ID documents
        """
        if cls.is_selfie(document_type):
            has_selfie = cls.objects.filter(
                kyc_profile=kyc_profile,
                document_type=KYCDocumentType.SELFIE
            ).exists()
            
            return {
                'complete': has_selfie,
                'has_front': has_selfie,
                'has_back': True,  # N/A for selfie
                'has_selfie': has_selfie,
            }
        
        # Check for front (required)
        has_front = cls.objects.filter(
            kyc_profile=kyc_profile,
            document_type=document_type,
            document_side=DocumentSide.FRONT
        ).exists()
        
        # Check for back (optional)
        has_back = cls.objects.filter(
            kyc_profile=kyc_profile,
            document_type=document_type,
            document_side=DocumentSide.BACK
        ).exists()
        
        # Check for selfie (required for ID documents)
        has_selfie = True  # Default for non-ID documents
        if cls.requires_selfie(document_type):
            has_selfie = cls.objects.filter(
                kyc_profile=kyc_profile,
                document_type=KYCDocumentType.SELFIE
            ).exists()
        
        # Document is complete if:
        # 1. Has front (required)
        # 2. Has selfie (required for ID documents)
        # Back is optional, so not checked for completeness
        complete = has_front and has_selfie
        
        return {
            'complete': complete,
            'has_front': has_front,
            'has_back': has_back,  # Optional
            'has_selfie': has_selfie,
            'requires_selfie': cls.requires_selfie(document_type),
        }
    
    @classmethod
    def get_required_documents_for_level(cls, kyc_level):
        """Get required documents for each KYC level"""
        requirements = {
            KYCLevel.BASIC: [],  # Just email + phone
            KYCLevel.INTERMEDIATE: [
                # User must provide ONE of these ID documents + selfie
                {
                    'type': 'id_document',
                    'options': [
                        KYCDocumentType.NATIONAL_ID,
                        KYCDocumentType.PASSPORT,
                        KYCDocumentType.DRIVERS_LICENSE,
                    ],
                    'selfie_required': True,  # Must also upload selfie
                },
                KYCDocumentType.PROOF_OF_ADDRESS,
            ],
            KYCLevel.ADVANCED: [
                {
                    'type': 'id_document',
                    'options': [
                        KYCDocumentType.NATIONAL_ID,
                        KYCDocumentType.PASSPORT,
                        KYCDocumentType.DRIVERS_LICENSE,
                    ],
                    'selfie_required': True,
                },
                KYCDocumentType.PROOF_OF_ADDRESS,
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
            'uploaded_documents': list,
            'selfie_status': dict
        }
        """
        requirements = cls.get_required_documents_for_level(target_level)
        uploaded = cls.objects.filter(
            kyc_profile=kyc_profile,
            status__in=[
                KYCVerificationStatus.PENDING,
                KYCVerificationStatus.UNDER_REVIEW,
                KYCVerificationStatus.APPROVED,
            ]
        )
        
        uploaded_types = list(uploaded.values_list('document_type', flat=True))
        
        # Check for ID document
        id_docs = [
            KYCDocumentType.NATIONAL_ID,
            KYCDocumentType.PASSPORT,
            KYCDocumentType.DRIVERS_LICENSE,
        ]
        
        has_id_doc = any(doc in uploaded_types for doc in id_docs)
        has_selfie = KYCDocumentType.SELFIE in uploaded_types
        
        missing = []
        selfie_status = {
            'required': False,
            'uploaded': has_selfie,
        }
        
        for requirement in requirements:
            if isinstance(requirement, dict) and requirement['type'] == 'id_document':
                if not has_id_doc:
                    missing.append('ID Document (National ID, Passport, or Driver\'s License) - Front side required')
                
                if requirement.get('selfie_required') and not has_selfie:
                    missing.append('Selfie (for face verification with your ID)')
                    selfie_status['required'] = True
            else:
                if requirement not in uploaded_types:
                    missing.append(dict(KYCDocumentType.choices)[requirement])
        
        return {
            'eligible': len(missing) == 0,
            'missing_documents': missing,
            'uploaded_documents': uploaded_types,
            'selfie_status': selfie_status,
        }
    
    @classmethod
    def get_required_documents_for_level(cls, kyc_level):
        """
        Get required documents for each KYC level
        Returns list of tuples: (document_type, requires_front, requires_selfie)
        """
        requirements = {
            KYCLevel.BASIC: [],  # Just email + phone
            
            KYCLevel.INTERMEDIATE: [
                # At least one ID document (front mandatory)
                {
                    'category': 'id_document',
                    'options': [
                        KYCDocumentType.NATIONAL_ID,
                        KYCDocumentType.PASSPORT,
                        KYCDocumentType.DRIVERS_LICENSE,
                    ],
                    'requires_front': True,
                    'requires_back': False,
                },
                 {
                    'category': 'selfie',
                    'document_type': KYCDocumentType.SELFIE,
                    'required': True,
                },
                # Proof of address
                # {
                #     'category': 'proof_of_address',
                #     'document_type': KYCDocumentType.PROOF_OF_ADDRESS,
                #     'required': True,
                # },
            ],
            
            KYCLevel.ADVANCED: [
                # ID document (front mandatory)
                {
                    'category': 'id_document',
                    'options': [
                        KYCDocumentType.NATIONAL_ID,
                        KYCDocumentType.PASSPORT,
                        KYCDocumentType.DRIVERS_LICENSE,
                    ],
                    'requires_front': True,
                    'requires_back': False,
                },
                # Proof of address
                {
                    'category': 'proof_of_address',
                    'document_type': KYCDocumentType.PROOF_OF_ADDRESS,
                    'required': True,
                },
                # Selfie (MANDATORY)
                {
                    'category': 'selfie',
                    'document_type': KYCDocumentType.SELFIE,
                    'required': True,
                },
                # Bank statement
                {
                    'category': 'bank_statement',
                    'document_type': KYCDocumentType.BANK_STATEMENT,
                    'required': True,
                },
            ],
        }
        return requirements.get(kyc_level, [])
    
    @classmethod
    def check_level_requirements(cls, kyc_profile, target_level):
        """
        Check if user has uploaded all required documents for target KYC level
        Front + Selfie are mandatory, back is optional
        """
        requirements = cls.get_required_documents_for_level(target_level)
        uploaded = cls.objects.filter(
            kyc_profile=kyc_profile,
            status__in=[
                KYCVerificationStatus.PENDING,
                KYCVerificationStatus.UNDER_REVIEW,
                KYCVerificationStatus.APPROVED,
            ]
        )
        
        missing = []
        uploaded_list = []
        
        for req in requirements:
            category = req.get('category')
            
            if category == 'id_document':
                # Check if user has at least one ID document with FRONT
                id_options = req.get('options', [])
                has_id_front = uploaded.filter(
                    document_type__in=id_options,
                    document_side=DocumentSide.FRONT
                ).exists()
                
                if not has_id_front:
                    missing.append('ID Document (Front side - National ID, Passport, or Driver\'s License)')
                else:
                    # Find which ID they uploaded
                    id_doc = uploaded.filter(
                        document_type__in=id_options,
                        document_side=DocumentSide.FRONT
                    ).first()
                    uploaded_list.append(f"{dict(KYCDocumentType.choices)[id_doc.document_type]} (Front)")
                    
                    # Check if back is also uploaded (optional, just for info)
                    has_back = uploaded.filter(
                        document_type=id_doc.document_type,
                        document_side=DocumentSide.BACK
                    ).exists()
                    if has_back:
                        uploaded_list.append(f"{dict(KYCDocumentType.choices)[id_doc.document_type]} (Back - optional)")
            
            elif category == 'selfie':
                # Selfie is MANDATORY for advanced
                has_selfie = uploaded.filter(
                    document_type=KYCDocumentType.SELFIE
                ).exists()
                
                if not has_selfie:
                    missing.append('Selfie (Mandatory)')
                else:
                    uploaded_list.append('Selfie')
            
            else:
                # Other documents (proof_of_address, bank_statement)
                doc_type = req.get('document_type')
                has_doc = uploaded.filter(document_type=doc_type).exists()
                
                if not has_doc:
                    missing.append(dict(KYCDocumentType.choices)[doc_type])
                else:
                    uploaded_list.append(dict(KYCDocumentType.choices)[doc_type])
        
        return {
            'eligible': len(missing) == 0,
            'missing_documents': missing,
            'uploaded_documents': uploaded_list,
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
