from .models import Cart


def cart_count(request):
    """Makes the number of items in the logged-in customer's cart available in every template."""
    count = 0
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'CUSTOMER':
        cart = Cart.objects.filter(customer=request.user).first()
        if cart:
            count = cart.total_items
    return {'nav_cart_count': count}
