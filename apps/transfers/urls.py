from django.urls import path
from .views import (
    CreateTransferView,
    TransferHistoryView,
    TransferDetailView,
    TransferLimitsView,
)

urlpatterns = [
    path('transfer/', CreateTransferView.as_view(), name='transfer-create'),
    path('history/', TransferHistoryView.as_view(), name='transfer-history'),
    path('<uuid:pk>/', TransferDetailView.as_view(), name='transfer-detail'),
    path('limits/', TransferLimitsView.as_view(), name='transfer-limits'),
]
