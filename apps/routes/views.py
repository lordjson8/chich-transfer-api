# apps/routes/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Country, PaymentMethod, Corridor
from .serializers import (
    CountrySerializer,
    PaymentMethodSerializer,
    CountryWithPaymentMethodsSerializer,
    CorridorSerializer,
    CorridorListSerializer,
    TransferFlowSerializer,
)


class CountryListView(APIView):
    """
    GET /api/routes/countries/
    
    List all supported countries with their payment methods
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Optionally include payment methods
        include_methods = request.query_params.get('include_methods', 'true').lower() == 'true'
        
        countries = Country.objects.filter(is_active=True).order_by('name')
        
        if include_methods:
            countries = countries.prefetch_related('payment_methods')
            serializer = CountryWithPaymentMethodsSerializer(countries, many=True)
        else:
            serializer = CountrySerializer(countries, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': countries.count(),
        })


class CountryPaymentMethodsView(APIView):
    """
    GET /api/routes/countries/{iso_code}/payment-methods/
    
    Get all payment methods available in a specific country
    """
    permission_classes = [AllowAny]
    
    def get(self, request, iso_code):
        country = get_object_or_404(Country, iso_code=iso_code.upper(), is_active=True)
        
        # Filter by usage type if specified
        method_type = request.query_params.get('type')  # 'funding' or 'payout'
        
        methods = country.payment_methods.filter(is_active=True)
        
        if method_type in ['funding', 'payout']:
            methods = methods.filter(
                Q(type_category=method_type) | Q(type_category='both')
            )
        
        methods = methods.order_by('-priority', 'method_type')
        serializer = PaymentMethodSerializer(methods, many=True)
        
        return Response({
            'success': True,
            'country': CountrySerializer(country).data,
            'payment_methods': serializer.data,
            'count': methods.count(),
        })


class FundingMethodsView(APIView):
    """
    GET /api/routes/funding-methods/
    
    Get all available funding methods for a country
    (How the sender can pay)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        source_code = request.query_params.get('country')
        
        if not source_code:
            # Get from user's country if available
            try:
                if hasattr(request.user, 'country') and request.user.country:
                    source_code = request.user.country.iso_code
                else:
                    return Response({
                        'success': False,
                        'error': 'Please provide ?country=ISO_CODE parameter',
                    }, status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response({
                    'success': False,
                    'error': 'Please provide ?country=ISO_CODE parameter',
                }, status=status.HTTP_400_BAD_REQUEST)
        
        source_country = get_object_or_404(
            Country,
            iso_code=source_code.upper(),
            is_active=True
        )
        
        # Get payment methods suitable for funding
        funding_methods = source_country.payment_methods.filter(
            is_active=True
        ).filter(
            Q(type_category='funding') | Q(type_category='both')
        ).order_by('-priority', 'method_type')
        
        serializer = PaymentMethodSerializer(funding_methods, many=True)
        
        return Response({
            'success': True,
            'country': CountrySerializer(source_country).data,
            'funding_methods': serializer.data,
            'count': funding_methods.count(),
        })


class PayoutMethodsView(APIView):
    """
    GET /api/routes/payout-methods/
    
    Get all available payout methods for a country
    (How the receiver gets money)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        destination_code = request.query_params.get('country')
        
        if not destination_code:
            return Response({
                'success': False,
                'error': 'Please provide ?country=ISO_CODE parameter',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        destination_country = get_object_or_404(
            Country,
            iso_code=destination_code.upper(),
            is_active=True
        )
        
        # Get payment methods suitable for payout
        payout_methods = destination_country.payment_methods.filter(
            is_active=True
        ).filter(
            Q(type_category='payout') | Q(type_category='both')
        ).order_by('-priority', 'method_type')
        
        serializer = PaymentMethodSerializer(payout_methods, many=True)
        
        return Response({
            'success': True,
            'country': CountrySerializer(destination_country).data,
            'payout_methods': serializer.data,
            'count': payout_methods.count(),
        })


class TransferFlowView(APIView):
    """
    ✨ NEW: Complete transfer flow endpoint
    
    GET /api/routes/transfer-flow/?source=CM&destination=CI&funding_method=mtn_cm&payout_method=mtn_ci
    
    Returns:
    - Source country funding methods
    - Destination country payout methods
    - Corridor info (fees, limits)
    - Whether transfer is possible
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        source_code = request.query_params.get('source')
        destination_code = request.query_params.get('destination')
        funding_method_id = request.query_params.get('funding_method')
        payout_method_id = request.query_params.get('payout_method')
        
        # Validate required params
        if not source_code or not destination_code:
            return Response({
                'success': False,
                'error': 'Both source and destination country codes required (?source=CM&destination=CI)',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get countries
        source_country = get_object_or_404(Country, iso_code=source_code.upper())
        destination_country = get_object_or_404(Country, iso_code=destination_code.upper())
        
        # Check if corridor exists
        corridor = Corridor.objects.filter(
            source_country=source_country,
            destination_country=destination_country,
            is_active=True
        ).first()
        
        # Get payment methods
        funding_methods = source_country.payment_methods.filter(
            is_active=True
        ).filter(
            Q(type_category='funding') | Q(type_category='both')
        ).order_by('-priority')
        
        payout_methods = destination_country.payment_methods.filter(
            is_active=True
        ).filter(
            Q(type_category='payout') | Q(type_category='both')
        ).order_by('-priority')
        
        # If specific methods requested, validate them
        if funding_method_id or payout_method_id:
            if funding_method_id:
                try:
                    funding_method = funding_methods.get(id=funding_method_id)
                except PaymentMethod.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'Funding method {funding_method_id} not available in {source_code}',
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            if payout_method_id:
                try:
                    payout_method = payout_methods.get(id=payout_method_id)
                except PaymentMethod.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'Payout method {payout_method_id} not available in {destination_code}',
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        # Build response
        response_data = {
            'success': True,
            'source_country': CountrySerializer(source_country).data,
            'destination_country': CountrySerializer(destination_country).data,
            'funding_methods': PaymentMethodSerializer(funding_methods, many=True).data,
            'payout_methods': PaymentMethodSerializer(payout_methods, many=True).data,
            'corridor': CorridorSerializer(corridor).data if corridor else None,
            'available': bool(corridor),
            'message': 'Transfer route available' if corridor else f'No active corridor from {source_code} to {destination_code}',
        }
        
        return Response(response_data)


class AvailableDestinationsView(APIView):
    """
    ✨ NEW: Get all destinations from a source country
    
    GET /api/routes/available-destinations/?source=CM
    
    Returns all countries you can send to from source, with their payout methods
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        source_code = request.query_params.get('source')
        
        if not source_code:
            try:
                if hasattr(request.user, 'country') and request.user.country:
                    source_code = request.user.country.iso_code
                else:
                    return Response({
                        'success': False,
                        'error': 'Please provide ?source=ISO_CODE parameter',
                    }, status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response({
                    'success': False,
                    'error': 'Please provide ?source=ISO_CODE parameter',
                }, status=status.HTTP_400_BAD_REQUEST)
        
        source_country = get_object_or_404(Country, iso_code=source_code.upper())
        
        # Get all active corridors from source
        corridors = Corridor.objects.filter(
            source_country=source_country,
            is_active=True
        ).select_related('destination_country')
        
        destinations = []
        flag_map = {
            'CM': '🇨🇲', 'CI': '🇨🇮', 'SN': '🇸🇳', 'ML': '🇲🇱',
            'BF': '🇧🇫', 'TG': '🇹🇬', 'BJ': '🇧🇯', 'NE': '🇳🇪',
            'GH': '🇬🇭', 'NG': '🇳🇬', 'KE': '🇰🇪', 'UG': '🇺🇬',
        }
        
        for corridor in corridors:
            dest = corridor.destination_country
            
            # Get payout methods for destination
            payout_methods = dest.payment_methods.filter(
                is_active=True
            ).filter(
                Q(type_category='payout') | Q(type_category='both')
            ).order_by('-priority')
            
            destinations.append({
                'country_code': dest.iso_code,
                'country_name': dest.name,
                'country_flag': flag_map.get(dest.iso_code, '🌍'),
                'corridor_id': corridor.id,
                'fees': {
                    'fixed': str(corridor.fixed_fee),
                    'percentage': str(corridor.percentage_fee),
                },
                'limits': {
                    'min': str(corridor.min_amount),
                    'max': str(corridor.max_amount),
                },
                'payout_methods': PaymentMethodSerializer(payout_methods, many=True).data,
            })
        
        return Response({
            'success': True,
            'source_country': CountrySerializer(source_country).data,
            'destinations': sorted(destinations, key=lambda x: x['country_name']),
            'total_destinations': len(destinations),
        })
