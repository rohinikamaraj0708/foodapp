import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone

from .decorators import customer_required, restaurant_required, delivery_required, admin_required
from .forms import (CustomerSignUpForm, RestaurantSignUpForm, DeliverySignUpForm,
                     UserProfileForm, RestaurantProfileForm, FoodItemForm, ReviewForm,
                     CheckoutForm, CouponForm)
from .models import (User, Restaurant, FoodCategory, FoodItem, Cart, CartItem,
                      Coupon, DeliveryPartner, Order, OrderItem, Payment, Review)


# ---------------------------------------------------------------------------
# PUBLIC / SHARED
# ---------------------------------------------------------------------------

def home(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')

    restaurants = Restaurant.objects.filter(is_approved=True, is_open=True)
    if query:
        restaurants = restaurants.filter(
            Q(name__icontains=query) | Q(menu_items__name__icontains=query)
        ).distinct()
    if category_id:
        restaurants = restaurants.filter(menu_items__category_id=category_id).distinct()

    categories = FoodCategory.objects.filter(is_active=True)
    context = {
        'restaurants': restaurants,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
    }
    return render(request, 'core/home.html', context)


def restaurant_detail(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_approved=True)
    category_id = request.GET.get('category', '')
    items = restaurant.menu_items.filter(is_available=True)
    if category_id:
        items = items.filter(category_id=category_id)
    categories = FoodCategory.objects.filter(food_items__restaurant=restaurant).distinct()
    reviews = restaurant.reviews.select_related('customer')[:10]
    context = {
        'restaurant': restaurant,
        'items': items,
        'categories': categories,
        'reviews': reviews,
        'selected_category': category_id,
    }
    return render(request, 'core/restaurant_detail.html', context)


class RoleAwareLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


@login_required
def dashboard_redirect(request):
    user = request.user
    if user.is_superuser or user.is_admin_role:
        return redirect('admin_dashboard')
    if user.is_restaurant_owner:
        return redirect('restaurant_dashboard')
    if user.is_delivery_partner:
        return redirect('delivery_dashboard')
    return redirect('home')


def register_choice(request):
    return render(request, 'registration/register_choice.html')


def register_customer(request):
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            Cart.objects.get_or_create(customer=user)
            messages.success(request, 'Welcome to FoodExpress! Your account was created successfully.')
            return redirect('home')
    else:
        form = CustomerSignUpForm()
    return render(request, 'registration/register_customer.html', {'form': form})


def register_restaurant(request):
    if request.method == 'POST':
        form = RestaurantSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Restaurant account created! An admin will review and approve it shortly.')
            return redirect('restaurant_dashboard')
    else:
        form = RestaurantSignUpForm()
    return render(request, 'registration/register_restaurant.html', {'form': form})


def register_delivery(request):
    if request.method == 'POST':
        form = DeliverySignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Delivery partner account created! An admin will approve it shortly.')
            return redirect('delivery_dashboard')
    else:
        form = DeliverySignUpForm()
    return render(request, 'registration/register_delivery.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'core/profile.html', {'form': form})


# ---------------------------------------------------------------------------
# CART
# ---------------------------------------------------------------------------

@customer_required
def add_to_cart(request, food_item_id):
    food_item = get_object_or_404(FoodItem, id=food_item_id, is_available=True)
    cart, _ = Cart.objects.get_or_create(customer=request.user)

    if cart.restaurant_id and cart.restaurant_id != food_item.restaurant_id and cart.total_items > 0:
        messages.warning(
            request,
            f'Your cart already has items from another restaurant. '
            f'Clear the cart to order from {food_item.restaurant.name}.'
        )
        return redirect('cart_view')

    cart.restaurant = food_item.restaurant
    cart.save()
    item, created = CartItem.objects.get_or_create(cart=cart, food_item=food_item)
    if not created:
        item.quantity += 1
    item.save()
    messages.success(request, f'{food_item.name} added to cart.')
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@customer_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(customer=request.user)
    return render(request, 'core/cart.html', {'cart': cart})


@customer_required
def update_cart_item(request, item_id, action):
    item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user)
    if action == 'increase':
        item.quantity += 1
        item.save()
    elif action == 'decrease':
        item.quantity -= 1
        if item.quantity <= 0:
            item.delete()
        else:
            item.save()
    elif action == 'remove':
        item.delete()
    cart = item.cart if action != 'remove' else Cart.objects.get(customer=request.user)
    if not cart.cart_items.exists():
        cart.restaurant = None
        cart.save()
    return redirect('cart_view')


# ---------------------------------------------------------------------------
# CHECKOUT / ORDERS (CUSTOMER)
# ---------------------------------------------------------------------------

@customer_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(customer=request.user)
    if not cart.cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('home')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = Order.objects.create(
                    customer=request.user,
                    restaurant=cart.restaurant,
                    delivery_address=form.cleaned_data['delivery_address'] or request.user.address,
                    delivery_fee=Decimal(str(settings.DELIVERY_CHARGE)),
                )
                for cart_item in cart.cart_items.select_related('food_item'):
                    OrderItem.objects.create(
                        order=order,
                        food_item=cart_item.food_item,
                        item_name=cart_item.food_item.name,
                        price=cart_item.food_item.price,
                        quantity=cart_item.quantity,
                    )

                coupon_code = form.cleaned_data.get('coupon_code', '').strip().upper()
                if coupon_code:
                    coupon = Coupon.objects.filter(code=coupon_code).first()
                    if coupon and coupon.is_valid:
                        order.coupon = coupon
                    else:
                        messages.warning(request, 'Coupon code is invalid or expired and was not applied.')

                order.recompute_totals()

                payment = Payment.objects.create(
                    order=order,
                    method=form.cleaned_data['payment_method'],
                    amount=order.total_amount,
                    transaction_id=str(uuid.uuid4()).replace('-', '')[:20].upper(),
                )
                # Simulated payment gateway: everything except COD is marked paid immediately.
                if payment.method == Payment.Method.COD:
                    payment.status = Payment.Status.PENDING
                else:
                    payment.status = Payment.Status.SUCCESS
                    payment.paid_at = timezone.now()
                payment.save()

                cart.clear()

            _notify(order.customer.email, 'Order Placed - FoodExpress',
                    f'Your order #{order.id} from {order.restaurant.name} has been placed successfully. '
                    f'Total: Rs.{order.total_amount}')
            messages.success(request, f'Order #{order.id} placed successfully!')
            return redirect('order_success', order_id=order.id)
    else:
        form = CheckoutForm(initial={'delivery_address': request.user.address})

    return render(request, 'core/checkout.html', {'form': form, 'cart': cart})


@customer_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'core/order_success.html', {'order': order})


@customer_required
def my_orders(request):
    orders = Order.objects.filter(customer=request.user).select_related('restaurant')
    return render(request, 'core/my_orders.html', {'orders': orders})


@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    user = request.user
    allowed = (
        user == order.customer or
        (user.is_restaurant_owner and order.restaurant.owner_id == user.id) or
        (user.is_delivery_partner and order.delivery_partner and order.delivery_partner.user_id == user.id) or
        user.is_superuser or user.is_admin_role
    )
    if not allowed:
        messages.error(request, "You don't have permission to view this order.")
        return redirect('home')
    return render(request, 'core/track_order.html', {'order': order})


@customer_required
def submit_review(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    if not order.can_review:
        messages.error(request, 'You can only review delivered orders.')
        return redirect('my_orders')
    if hasattr(order, 'review'):
        messages.info(request, 'You already reviewed this order.')
        return redirect('my_orders')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.customer = request.user
            review.restaurant = order.restaurant
            review.order = order
            review.save()
            messages.success(request, 'Thanks for your feedback!')
            return redirect('my_orders')
    else:
        form = ReviewForm()
    return render(request, 'core/submit_review.html', {'form': form, 'order': order})


# ---------------------------------------------------------------------------
# RESTAURANT DASHBOARD
# ---------------------------------------------------------------------------

def _get_owned_restaurant(request):
    return Restaurant.objects.filter(owner=request.user).first()


@restaurant_required
def restaurant_dashboard(request):
    restaurant = _get_owned_restaurant(request)
    orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')[:10] if restaurant else []
    stats = {}
    if restaurant:
        stats = {
            'total_orders': Order.objects.filter(restaurant=restaurant).count(),
            'pending_orders': Order.objects.filter(restaurant=restaurant, status=Order.Status.PLACED).count(),
            'menu_items': restaurant.menu_items.count(),
            'total_sales': Order.objects.filter(
                restaurant=restaurant, status=Order.Status.DELIVERED
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
        }
    return render(request, 'core/restaurant/dashboard.html', {
        'restaurant': restaurant, 'orders': orders, 'stats': stats,
    })


@restaurant_required
def restaurant_profile(request):
    restaurant = _get_owned_restaurant(request)
    if not restaurant:
        messages.error(request, 'No restaurant profile found.')
        return redirect('restaurant_dashboard')
    if request.method == 'POST':
        form = RestaurantProfileForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Restaurant profile updated.')
            return redirect('restaurant_profile')
    else:
        form = RestaurantProfileForm(instance=restaurant)
    return render(request, 'core/restaurant/profile.html', {'form': form, 'restaurant': restaurant})


@restaurant_required
def restaurant_menu(request):
    restaurant = _get_owned_restaurant(request)
    items = restaurant.menu_items.all() if restaurant else []
    return render(request, 'core/restaurant/menu.html', {'restaurant': restaurant, 'items': items})


@restaurant_required
def restaurant_menu_add(request):
    restaurant = _get_owned_restaurant(request)
    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.restaurant = restaurant
            item.save()
            messages.success(request, f'{item.name} added to your menu.')
            return redirect('restaurant_menu')
    else:
        form = FoodItemForm()
    return render(request, 'core/restaurant/menu_form.html', {'form': form, 'title': 'Add Food Item'})


@restaurant_required
def restaurant_menu_edit(request, item_id):
    restaurant = _get_owned_restaurant(request)
    item = get_object_or_404(FoodItem, id=item_id, restaurant=restaurant)
    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'{item.name} updated.')
            return redirect('restaurant_menu')
    else:
        form = FoodItemForm(instance=item)
    return render(request, 'core/restaurant/menu_form.html', {'form': form, 'title': 'Edit Food Item'})


@restaurant_required
def restaurant_menu_delete(request, item_id):
    restaurant = _get_owned_restaurant(request)
    item = get_object_or_404(FoodItem, id=item_id, restaurant=restaurant)
    item.delete()
    messages.success(request, 'Food item deleted.')
    return redirect('restaurant_menu')


@restaurant_required
def restaurant_orders(request):
    restaurant = _get_owned_restaurant(request)
    status_filter = request.GET.get('status', '')
    orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at') if restaurant else []
    if status_filter:
        orders = orders.filter(status=status_filter)
    return render(request, 'core/restaurant/orders.html', {
        'restaurant': restaurant, 'orders': orders, 'statuses': Order.Status.choices, 'status_filter': status_filter,
    })


@restaurant_required
def restaurant_order_action(request, order_id, action):
    restaurant = _get_owned_restaurant(request)
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)

    transitions = {
        'accept': Order.Status.ACCEPTED,
        'reject': Order.Status.REJECTED,
        'preparing': Order.Status.PREPARING,
        'ready': Order.Status.READY,
    }
    new_status = transitions.get(action)
    if new_status:
        order.status = new_status
        order.save()
        _notify(order.customer.email, f'Order #{order.id} update',
                f'Your order status changed to: {order.get_status_display()}')
        messages.success(request, f'Order #{order.id} marked as {order.get_status_display()}.')

        if new_status == Order.Status.READY:
            partner = DeliveryPartner.objects.filter(is_available=True, is_approved=True).first()
            if partner:
                order.delivery_partner = partner
                order.save()
    return redirect('restaurant_orders')


@restaurant_required
def restaurant_sales(request):
    restaurant = _get_owned_restaurant(request)
    orders = Order.objects.filter(restaurant=restaurant, status=Order.Status.DELIVERED) if restaurant else Order.objects.none()
    summary = orders.aggregate(total_sales=Sum('total_amount'), total_orders=Count('id'))
    top_items = OrderItem.objects.filter(order__in=orders).values('item_name').annotate(
        total_qty=Sum('quantity')
    ).order_by('-total_qty')[:5]
    return render(request, 'core/restaurant/sales.html', {
        'restaurant': restaurant, 'summary': summary, 'top_items': top_items, 'orders': orders[:20],
    })


# ---------------------------------------------------------------------------
# DELIVERY PARTNER DASHBOARD
# ---------------------------------------------------------------------------

def _get_delivery_profile(request):
    return DeliveryPartner.objects.filter(user=request.user).first()


@delivery_required
def delivery_dashboard(request):
    partner = _get_delivery_profile(request)
    available_orders = Order.objects.filter(
        status=Order.Status.READY, delivery_partner__isnull=True
    ).select_related('restaurant')
    my_orders_qs = Order.objects.filter(delivery_partner=partner).exclude(
        status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED, Order.Status.REJECTED]
    ).select_related('restaurant') if partner else []
    return render(request, 'core/delivery/dashboard.html', {
        'partner': partner, 'available_orders': available_orders, 'my_orders': my_orders_qs,
    })


@delivery_required
def delivery_accept_order(request, order_id):
    partner = _get_delivery_profile(request)
    order = get_object_or_404(Order, id=order_id, status=Order.Status.READY, delivery_partner__isnull=True)
    order.delivery_partner = partner
    order.save()
    messages.success(request, f'You accepted order #{order.id}.')
    return redirect('delivery_dashboard')


@delivery_required
def delivery_update_status(request, order_id, action):
    partner = _get_delivery_profile(request)
    order = get_object_or_404(Order, id=order_id, delivery_partner=partner)
    if action == 'out_for_delivery':
        order.status = Order.Status.OUT_FOR_DELIVERY
    elif action == 'delivered':
        order.status = Order.Status.DELIVERED
    order.save()
    _notify(order.customer.email, f'Order #{order.id} update',
            f'Your order status changed to: {order.get_status_display()}')
    messages.success(request, f'Order #{order.id} updated to {order.get_status_display()}.')
    return redirect('delivery_dashboard')


@delivery_required
def delivery_earnings(request):
    partner = _get_delivery_profile(request)
    delivered_orders = Order.objects.filter(delivery_partner=partner, status=Order.Status.DELIVERED) if partner else Order.objects.none()
    return render(request, 'core/delivery/earnings.html', {
        'partner': partner, 'orders': delivered_orders,
    })


# ---------------------------------------------------------------------------
# ADMIN DASHBOARD (custom, in addition to Django's built-in /admin/)
# ---------------------------------------------------------------------------

@admin_required
def admin_dashboard(request):
    stats = {
        'total_customers': User.objects.filter(role=User.Role.CUSTOMER).count(),
        'total_restaurants': Restaurant.objects.count(),
        'pending_restaurant_approvals': Restaurant.objects.filter(is_approved=False).count(),
        'total_delivery_partners': DeliveryPartner.objects.count(),
        'pending_delivery_approvals': DeliveryPartner.objects.filter(is_approved=False).count(),
        'total_orders': Order.objects.count(),
        'total_revenue': Order.objects.filter(status=Order.Status.DELIVERED).aggregate(
            total=Sum('total_amount'))['total'] or 0,
    }
    recent_orders = Order.objects.select_related('customer', 'restaurant').order_by('-created_at')[:10]
    return render(request, 'core/admin/dashboard.html', {'stats': stats, 'recent_orders': recent_orders})


@admin_required
def admin_users(request):
    role_filter = request.GET.get('role', '')
    users = User.objects.exclude(is_superuser=True).order_by('-created_at')
    if role_filter:
        users = users.filter(role=role_filter)
    return render(request, 'core/admin/users.html', {'users': users, 'roles': User.Role.choices, 'role_filter': role_filter})


@admin_required
def admin_toggle_block(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_blocked = not user.is_blocked
    user.is_active = not user.is_blocked
    user.save()
    messages.success(request, f'{user.username} is now {"blocked" if user.is_blocked else "active"}.')
    return redirect('admin_users')


@admin_required
def admin_restaurants(request):
    restaurants = Restaurant.objects.select_related('owner').order_by('-created_at')
    return render(request, 'core/admin/restaurants.html', {'restaurants': restaurants})


@admin_required
def admin_toggle_restaurant_approval(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    restaurant.is_approved = not restaurant.is_approved
    restaurant.save()
    messages.success(request, f'{restaurant.name} is now {"approved" if restaurant.is_approved else "unapproved"}.')
    return redirect('admin_restaurants')


@admin_required
def admin_delivery_partners(request):
    partners = DeliveryPartner.objects.select_related('user').order_by('-id')
    return render(request, 'core/admin/delivery_partners.html', {'partners': partners})


@admin_required
def admin_toggle_delivery_approval(request, partner_id):
    partner = get_object_or_404(DeliveryPartner, id=partner_id)
    partner.is_approved = not partner.is_approved
    partner.save()
    messages.success(request, f'{partner.user.username} is now {"approved" if partner.is_approved else "unapproved"}.')
    return redirect('admin_delivery_partners')


@admin_required
def admin_orders(request):
    status_filter = request.GET.get('status', '')
    orders = Order.objects.select_related('customer', 'restaurant').order_by('-created_at')
    if status_filter:
        orders = orders.filter(status=status_filter)
    return render(request, 'core/admin/orders.html', {'orders': orders, 'statuses': Order.Status.choices, 'status_filter': status_filter})


@admin_required
def admin_categories(request):
    categories = FoodCategory.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            FoodCategory.objects.get_or_create(name=name)
            messages.success(request, f'Category "{name}" added.')
        return redirect('admin_categories')
    return render(request, 'core/admin/categories.html', {'categories': categories})


@admin_required
def admin_category_toggle(request, category_id):
    category = get_object_or_404(FoodCategory, id=category_id)
    category.is_active = not category.is_active
    category.save()
    return redirect('admin_categories')


@admin_required
def admin_coupons(request):
    coupons = Coupon.objects.order_by('-id')
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Coupon created.')
            return redirect('admin_coupons')
    else:
        form = CouponForm()
    return render(request, 'core/admin/coupons.html', {'coupons': coupons, 'form': form})


@admin_required
def admin_reports(request):
    orders = Order.objects.filter(status=Order.Status.DELIVERED)
    top_restaurants = orders.values('restaurant__name').annotate(
        revenue=Sum('total_amount'), order_count=Count('id')
    ).order_by('-revenue')[:10]
    monthly = orders.values('created_at__year', 'created_at__month').annotate(
        revenue=Sum('total_amount'), order_count=Count('id')
    ).order_by('-created_at__year', '-created_at__month')[:12]
    context = {
        'top_restaurants': top_restaurants,
        'monthly': monthly,
        'total_revenue': orders.aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_orders': orders.count(),
        'average_order_value': orders.aggregate(avg=Avg('total_amount'))['avg'] or 0,
    }
    return render(request, 'core/admin/reports.html', context)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _notify(to_email, subject, message):
    """Send an email notification; fails silently so it never blocks the request flow."""
    if not to_email:
        return
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=True)
    except Exception:
        pass
