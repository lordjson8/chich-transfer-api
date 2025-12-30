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
