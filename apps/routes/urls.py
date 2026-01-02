# apps/routes/urls.py

from django.urls import path
from .views import (
    CountryListView,
    CorridorListView,
    CorridorDetailView,
    CorridorPaymentMethodsView,
    ValidateCorridorView,
)

urlpatterns = [
    # Countries
    path('countries/', CountryListView.as_view(), name='country-list'),
    
    # Corridors
    path('corridors/', CorridorListView.as_view(), name='corridor-list'),
    path('corridors/<int:corridor_id>/', CorridorDetailView.as_view(), name='corridor-detail'),
    
    # Payment Methods
    path('payment-methods/', CorridorPaymentMethodsView.as_view(), name='corridor-payment-methods'),
    
    # Validation
    path('validate/', ValidateCorridorView.as_view(), name='validate-corridor'),
]
