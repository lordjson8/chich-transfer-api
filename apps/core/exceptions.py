from rest_framework.exceptions import APIException
from rest_framework import status


# apps/core/exceptions.py (add this function)

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import Throttled


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error format.
    """
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'success': False,
            'error': None,
            'error_code': None,
            'data': None,
        }
        
        # Handle throttling specifically
        if isinstance(exc, Throttled):
            custom_response_data['error'] = 'Too many requests. Please try again later.'
            custom_response_data['error_code'] = 'RATE_LIMIT_EXCEEDED'
            custom_response_data['retry_after'] = exc.wait
        else:
            # Get error message
            if hasattr(response.data, 'get'):
                detail = response.data.get('detail')
                if detail:
                    custom_response_data['error'] = str(detail)
                else:
                    custom_response_data['error'] = response.data
            else:
                custom_response_data['error'] = str(response.data)
            
            # Get error code
            if hasattr(exc, 'default_code'):
                custom_response_data['error_code'] = exc.default_code.upper()
        
        response.data = custom_response_data
    
    return response



class InsufficientFundsException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Insufficient funds to complete this transaction.'
    default_code = 'insufficient_funds'


class KYCNotCompletedException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Complete your KYC verification to perform this action.'
    default_code = 'kyc_not_completed'


class TransactionLimitExceededException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Transaction limit exceeded.'
    default_code = 'limit_exceeded'


class CorridorNotSupportedException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Transfer corridor not supported.'
    default_code = 'corridor_not_supported'


class PaymentMethodNotAllowedException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Payment method not allowed for this transaction.'
    default_code = 'payment_method_not_allowed'


class ProviderException(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Payment provider is temporarily unavailable.'
    default_code = 'provider_unavailable'
