"""
Custom validators for authentication
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class CustomPasswordValidator:
    """
    Validate password strength:
    - At least 8 characters
    - Contains uppercase letter
    - Contains lowercase letter
    - Contains number
    """
    
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(
                _("Password must be at least 8 characters long."),
                code='password_too_short',
            )
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            )
        
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code='password_no_lower',
            )
        
        if not re.search(r'\d', password):
            raise ValidationError(
                _("Password must contain at least one number."),
                code='password_no_number',
            )
    
    def get_help_text(self):
        return _(
            "Your password must contain at least 8 characters, "
            "including uppercase, lowercase, and numbers."
        )
