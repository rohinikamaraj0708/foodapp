from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------------

class User(AbstractUser):
    """Custom user model shared by every role in the system."""

    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        RESTAURANT = 'RESTAURANT', 'Restaurant Owner'
        DELIVERY = 'DELIVERY', 'Delivery Partner'
        ADMIN = 'ADMIN', 'Administrator'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_restaurant_owner(self):
        return self.role == self.Role.RESTAURANT

    @property
    def is_delivery_partner(self):
        return self.role == self.Role.DELIVERY

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser


# ---------------------------------------------------------------------------
# RESTAURANTS
# ---------------------------------------------------------------------------

class FoodCategory(models.Model):
    """Global food categories, e.g. Pizza, Chinese, Desserts (managed by Admin)."""

    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Food Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Restaurant(models.Model):
    """A restaurant owned/managed by a RESTAURANT role user."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='restaurants')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    logo = models.ImageField(upload_to='restaurants/', blank=True, null=True)
    opening_time = models.TimeField(default='09:00')
    closing_time = models.TimeField(default='23:00')
    is_open = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False, help_text='Approved by Admin before it goes live.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        agg = self.reviews.aggregate(avg=models.Avg('rating'))
        return round(agg['avg'], 1) if agg['avg'] else 0

    @property
    def total_reviews(self):
        return self.reviews.count()


class FoodItem(models.Model):
    """Menu item that belongs to a restaurant."""

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(FoodCategory, on_delete=models.SET_NULL, null=True, related_name='food_items')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='food_items/', blank=True, null=True)
    is_veg = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} - {self.restaurant.name}'


# ---------------------------------------------------------------------------
# CART
# ---------------------------------------------------------------------------

class Cart(models.Model):
    """One active cart per customer."""

    customer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, blank=True,
                                    help_text='All items in a cart must come from one restaurant.')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart of {self.customer.username}'

    @property
    def items(self):
        return self.cart_items.select_related('food_item')

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items), Decimal('0.00'))

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items)

    def clear(self):
        self.cart_items.all().delete()
        self.restaurant = None
        self.save()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'food_item')

    def __str__(self):
        return f'{self.quantity} x {self.food_item.name}'

    @property
    def line_total(self):
        return self.food_item.price * self.quantity


# ---------------------------------------------------------------------------
# COUPONS
# ---------------------------------------------------------------------------

class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2,
                                            validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    minimum_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    @property
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to

    def compute_discount(self, subtotal):
        if subtotal < self.minimum_order_amount:
            return Decimal('0.00')
        discount = (subtotal * self.discount_percent) / Decimal('100')
        return min(discount, self.max_discount_amount)


# ---------------------------------------------------------------------------
# DELIVERY PARTNERS
# ---------------------------------------------------------------------------

class DeliveryPartner(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_profile')
    vehicle_type = models.CharField(max_length=50, blank=True)
    vehicle_number = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    @property
    def total_earnings(self):
        agg = self.orders.filter(status=Order.Status.DELIVERED).aggregate(total=models.Sum('delivery_fee'))
        return agg['total'] or Decimal('0.00')


# ---------------------------------------------------------------------------
# ORDERS
# ---------------------------------------------------------------------------

class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = 'PLACED', 'Placed'
        ACCEPTED = 'ACCEPTED', 'Accepted by Restaurant'
        REJECTED = 'REJECTED', 'Rejected by Restaurant'
        PREPARING = 'PREPARING', 'Preparing'
        READY = 'READY', 'Ready for Pickup'
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', 'Out for Delivery'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    delivery_partner = models.ForeignKey(DeliveryPartner, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='orders')
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    delivery_address = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)

    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.id} - {self.customer.username}'

    def recompute_totals(self):
        self.subtotal = sum((i.line_total for i in self.items.all()), Decimal('0.00'))
        if self.coupon and self.coupon.is_valid:
            self.discount_amount = self.coupon.compute_discount(self.subtotal)
        else:
            self.discount_amount = Decimal('0.00')
        taxable = self.subtotal - self.discount_amount
        self.tax_amount = (taxable * Decimal(str(settings.GST_PERCENT))) / Decimal('100')
        self.total_amount = taxable + self.tax_amount + self.delivery_fee
        self.save()

    STATUS_FLOW = [Status.PLACED, Status.ACCEPTED, Status.PREPARING, Status.READY,
                   Status.OUT_FOR_DELIVERY, Status.DELIVERED]

    @property
    def progress_percent(self):
        if self.status in (self.Status.REJECTED, self.Status.CANCELLED):
            return 0
        try:
            idx = self.STATUS_FLOW.index(self.status)
        except ValueError:
            return 0
        return int((idx / (len(self.STATUS_FLOW) - 1)) * 100)

    @property
    def can_review(self):
        return self.status == self.Status.DELIVERED


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.SET_NULL, null=True)
    item_name = models.CharField(max_length=150)  # snapshot in case food item is deleted/renamed later
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.quantity} x {self.item_name}'

    @property
    def line_total(self):
        return self.price * self.quantity


# ---------------------------------------------------------------------------
# PAYMENTS
# ---------------------------------------------------------------------------

class Payment(models.Model):
    class Method(models.TextChoices):
        CARD = 'CARD', 'Credit / Debit Card'
        UPI = 'UPI', 'UPI'
        NETBANKING = 'NETBANKING', 'Net Banking'
        COD = 'COD', 'Cash on Delivery'
        WALLET = 'WALLET', 'Wallet'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CARD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Payment for Order #{self.order_id} ({self.status})'


# ---------------------------------------------------------------------------
# REVIEWS
# ---------------------------------------------------------------------------

class Review(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.rating}* review by {self.customer.username} for {self.restaurant.name}'
