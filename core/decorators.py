from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    """Restrict a view to users whose .role is in `roles` (superusers always pass)."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You don't have permission to access that page.")
            return redirect('home')
        return _wrapped
    return decorator


customer_required = role_required('CUSTOMER')
restaurant_required = role_required('RESTAURANT')
delivery_required = role_required('DELIVERY')
admin_required = role_required('ADMIN')
