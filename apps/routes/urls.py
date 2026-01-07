# apps/routes/urls.py

from django.urls import path
from .views import (
    CountryListView,
    CountryPaymentMethodsView,
    FundingMethodsView,
    PayoutMethodsView,
    TransferFlowView,
    AvailableDestinationsView,
)

urlpatterns = [
    # Countries
    path('countries/', CountryListView.as_view(), name='country-list'),
    path('countries/<str:iso_code>/payment-methods/', CountryPaymentMethodsView.as_view(), name='country-payment-methods'),
    
    # Payment methods (independent of corridors)
    path('funding-methods/', FundingMethodsView.as_view(), name='funding-methods'),
    path('payout-methods/', PayoutMethodsView.as_view(), name='payout-methods'),
    
    # Transfer flow (combines both)
    path('transfer-flow/', TransferFlowView.as_view(), name='transfer-flow'),
    path('available-destinations/', AvailableDestinationsView.as_view(), name='available-destinations'),
]
