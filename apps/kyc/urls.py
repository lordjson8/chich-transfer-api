# apps/kyc/urls.py

from django.urls import path
from .views import (
    KYCProfileView,
    KYCDocumentUploadView,
    KYCDocumentsListView,
    KYCVerificationStatusView,
)

urlpatterns = [
    path('profile/', KYCProfileView.as_view(), name='kyc-profile'),
    path('documents/', KYCDocumentsListView.as_view(), name='kyc-documents-list'),
    path('documents/upload/', KYCDocumentUploadView.as_view(), name='kyc-document-upload'),
    path('status/', KYCVerificationStatusView.as_view(), name='kyc-status'),
]
