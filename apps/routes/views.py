# apps/routes/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Prefetch

from .models import Country, Corridor, CorridorFundingMethod, CorridorPayoutMethod
from .serializers import (
    CountrySerializer,
    CorridorSerializer,
    CorridorListSerializer,
    FundingMethodSerializer,
    PayoutMethodSerializer,
)


class CountryListView(APIView):
    """List all supported countries"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Get all supported countries
        
        GET /api/routes/countries/
        """
        countries = Country.objects.all().order_by('name')
        serializer = CountrySerializer(countries, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': countries.count(),
        }, status=status.HTTP_200_OK)


class CorridorListView(APIView):
    """List available corridors for a user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get available corridors from user's country
        
        GET /api/routes/corridors/
        GET /api/routes/corridors/?source_country=CM
        GET /api/routes/corridors/?destination_country=CI
        """
        # Get source country from query param or user's country
        source_country_code = request.query_params.get('source_country')
        destination_country_code = request.query_params.get('destination_country')
        
        # If no source specified, try to get from user's country
        if not source_country_code:
            try:
                source_country_code = request.user.country.iso_code
            except AttributeError:
                return Response({
                    'success': False,
                    'error': 'Please specify source_country or update your profile with your country.',
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter corridors
        corridors = Corridor.objects.filter(
            source_country__iso_code=source_country_code,
            is_active=True
        ).select_related(
            'source_country',
            'destination_country'
        )
        
        # Further filter by destination if specified
        if destination_country_code:
            corridors = corridors.filter(
                destination_country__iso_code=destination_country_code
            )
        
        serializer = CorridorListSerializer(corridors, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': corridors.count(),
        }, status=status.HTTP_200_OK)


class CorridorDetailView(APIView):
    """Get detailed corridor info with payment methods"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, corridor_id):
        """
        Get corridor details with payment methods
        
        GET /api/routes/corridors/{id}/
        """
        try:
            corridor = Corridor.objects.prefetch_related(
                Prefetch(
                    'funding_methods',
                    queryset=CorridorFundingMethod.objects.filter(is_active=True)
                ),
                Prefetch(
                    'payout_methods',
                    queryset=CorridorPayoutMethod.objects.filter(is_active=True)
                )
            ).select_related(
                'source_country',
                'destination_country'
            ).get(id=corridor_id, is_active=True)
        except Corridor.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Corridor not found or inactive.',
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CorridorSerializer(corridor)
        
        return Response({
            'success': True,
            'data': serializer.data,
        }, status=status.HTTP_200_OK)


class CorridorPaymentMethodsView(APIView):
    """Get payment methods for a specific corridor"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get payment methods for source→destination corridor
        
        GET /api/routes/payment-methods/?source=CM&destination=CI
        """
        source_code = request.query_params.get('source')
        destination_code = request.query_params.get('destination')
        
        if not source_code or not destination_code:
            return Response({
                'success': False,
                'error': 'Both source and destination country codes are required.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            corridor = Corridor.objects.prefetch_related(
                Prefetch(
                    'funding_methods',
                    queryset=CorridorFundingMethod.objects.filter(is_active=True)
                ),
                Prefetch(
                    'payout_methods',
                    queryset=CorridorPayoutMethod.objects.filter(is_active=True)
                )
            ).get(
                source_country__iso_code=source_code,
                destination_country__iso_code=destination_code,
                is_active=True
            )
        except Corridor.DoesNotExist:
            return Response({
                'success': False,
                'error': f'No active corridor found from {source_code} to {destination_code}.',
            }, status=status.HTTP_404_NOT_FOUND)
        
        funding_serializer = FundingMethodSerializer(corridor.funding_methods.all(), many=True)
        payout_serializer = PayoutMethodSerializer(corridor.payout_methods.all(), many=True)
        
        return Response({
            'success': True,
            'data': {
                'corridor_id': corridor.id,
                'source_country': corridor.source_country.iso_code,
                'destination_country': corridor.destination_country.iso_code,
                'funding_methods': funding_serializer.data,
                'payout_methods': payout_serializer.data,
            }
        }, status=status.HTTP_200_OK)


class ValidateCorridorView(APIView):
    """Validate if a corridor and payment methods are valid"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Validate corridor and payment methods before transfer
        
        POST /api/routes/validate/
        {
            "source_country": "CM",
            "destination_country": "CI",
            "funding_method_type": "mobile_money",
            "funding_mobile_provider": "mtn_cm",
            "payout_method_type": "mobile_money",
            "payout_mobile_provider": "mtn_ci"
        }
        """
        source_code = request.data.get('source_country')
        destination_code = request.data.get('destination_country')
        funding_type = request.data.get('funding_method_type')
        funding_provider = request.data.get('funding_mobile_provider')
        payout_type = request.data.get('payout_method_type')
        payout_provider = request.data.get('payout_mobile_provider')
        
        # Validate corridor exists
        try:
            corridor = Corridor.objects.get(
                source_country__iso_code=source_code,
                destination_country__iso_code=destination_code,
                is_active=True
            )
        except Corridor.DoesNotExist:
            return Response({
                'success': False,
                'valid': False,
                'error': f'No active corridor from {source_code} to {destination_code}.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate funding method
        funding_valid = CorridorFundingMethod.objects.filter(
            corridor=corridor,
            method_type=funding_type,
            is_active=True
        )
        
        if funding_type == 'mobile_money' and funding_provider:
            funding_valid = funding_valid.filter(mobile_provider=funding_provider)
        
        if not funding_valid.exists():
            return Response({
                'success': False,
                'valid': False,
                'error': 'Selected funding method is not available for this corridor.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate payout method
        payout_valid = CorridorPayoutMethod.objects.filter(
            corridor=corridor,
            method_type=payout_type,
            is_active=True
        )
        
        if payout_type == 'mobile_money' and payout_provider:
            payout_valid = payout_valid.filter(mobile_provider=payout_provider)
        
        if not payout_valid.exists():
            return Response({
                'success': False,
                'valid': False,
                'error': 'Selected payout method is not available for this corridor.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'valid': True,
            'message': 'Corridor and payment methods are valid.',
            'data': {
                'corridor_id': corridor.id,
            }
        }, status=status.HTTP_200_OK)
