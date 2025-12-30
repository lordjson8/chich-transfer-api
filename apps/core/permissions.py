# apps/core/permissions.py

from rest_framework import permissions


class IsKYCVerified(permissions.BasePermission):
    """
    Permission to check if user has completed KYC verification.
    """
    message = 'Complete your KYC verification to access this resource.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            kyc_profile = request.user.kyc_profile
            return kyc_profile.is_verified()
        except:
            return False


class IsKYCBasic(permissions.BasePermission):
    """
    Permission for basic KYC level or higher.
    """
    message = 'Complete basic KYC verification to access this resource.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            kyc_profile = request.user.kyc_profile
            return kyc_profile.kyc_level in ['basic', 'intermediate', 'advanced']
        except:
            return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.user == request.user
