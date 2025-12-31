# apps/kyc/urls.py

from django.urls import path
from .views import (
    KYCLevelRequirementsView,
    KYCProfileView,
    KYCDocumentUploadView,
    KYCDocumentsListView,
    KYCVerificationStatusView,
    KYCDocumentCompletenessView
)


urlpatterns = [
    path('profile/', KYCProfileView.as_view(), name='kyc-profile'),
    path('documents/', KYCDocumentsListView.as_view(), name='kyc-documents-list'),
    path('documents/upload/', KYCDocumentUploadView.as_view(), name='kyc-document-upload'),
    path('documents/completeness/', KYCDocumentCompletenessView.as_view(), name='kyc-document-completeness'),
    path('level-requirements/', KYCLevelRequirementsView.as_view(), name='kyc-level-requirements'),  # NEW
    path('status/', KYCVerificationStatusView.as_view(), name='kyc-status'),
]
