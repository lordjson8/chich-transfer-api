"""
Custom pagination classes
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    """Custom pagination with better response format"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


from rest_framework.pagination import LimitOffsetPagination


class StandardResultsSetPagination(LimitOffsetPagination):
    """
    Standard pagination with limit/offset.
    """
    default_limit = 20
    max_limit = 100
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'data': data,
            'pagination': {
                'count': self.count,
                'limit': self.limit,
                'offset': self.offset,
                'has_next': self.get_next_link() is not None,
                'has_previous': self.get_previous_link() is not None,
            }
        })
