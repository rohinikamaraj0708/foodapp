from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (User, Restaurant, FoodCategory, FoodItem, Cart, CartItem,
                      Coupon, DeliveryPartner, Order, OrderItem, Payment, Review)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone', 'is_blocked', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_blocked', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Food Delivery Profile', {'fields': ('role', 'phone', 'address', 'profile_image', 'is_blocked')}),
    )


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'city', 'is_open', 'is_approved', 'average_rating', 'created_at')
    list_filter = ('is_approved', 'is_open', 'city')
    search_fields = ('name', 'owner__username')
    actions = ['approve_restaurants']

    def approve_restaurants(self, request, queryset):
        queryset.update(is_approved=True)
    approve_restaurants.short_description = 'Approve selected restaurants'


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'is_veg', 'is_available')
    list_filter = ('is_veg', 'is_available', 'category')
    search_fields = ('name', 'restaurant__name')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'restaurant', 'total_items', 'updated_at')
    inlines = [CartItemInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'minimum_order_amount', 'valid_from', 'valid_to', 'is_active')
    list_filter = ('is_active',)


@admin.register(DeliveryPartner)
class DeliveryPartnerAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle_type', 'vehicle_number', 'is_available', 'is_approved', 'total_earnings')
    list_filter = ('is_available', 'is_approved')
    actions = ['approve_partners']

    def approve_partners(self, request, queryset):
        queryset.update(is_approved=True)
    approve_partners.short_description = 'Approve selected delivery partners'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'restaurant', 'delivery_partner', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'restaurant')
    search_fields = ('id', 'customer__username')
    inlines = [OrderItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'method', 'status', 'amount', 'transaction_id', 'paid_at')
    list_filter = ('method', 'status')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'customer', 'rating', 'created_at')
    list_filter = ('rating',)
