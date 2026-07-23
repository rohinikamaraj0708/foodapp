from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('restaurant/<int:restaurant_id>/', views.restaurant_detail, name='restaurant_detail'),

    # Auth
    path('accounts/login/', views.RoleAwareLoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register_choice, name='register_choice'),
    path('accounts/register/customer/', views.register_customer, name='register_customer'),
    path('accounts/register/restaurant/', views.register_restaurant, name='register_restaurant'),
    path('accounts/register/delivery/', views.register_delivery, name='register_delivery'),
    path('accounts/password-change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html', success_url='/accounts/password-change/done/'
    ), name='password_change'),
    path('accounts/password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('profile/', views.profile, name='profile'),

    # Cart
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:food_item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/item/<int:item_id>/<str:action>/', views.update_cart_item, name='update_cart_item'),

    # Checkout / Orders (customer)
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/success/', views.order_success, name='order_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/track/', views.track_order, name='track_order'),
    path('order/<int:order_id>/review/', views.submit_review, name='submit_review'),

    # Restaurant dashboard
    path('restaurant-panel/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('restaurant-panel/profile/', views.restaurant_profile, name='restaurant_profile'),
    path('restaurant-panel/menu/', views.restaurant_menu, name='restaurant_menu'),
    path('restaurant-panel/menu/add/', views.restaurant_menu_add, name='restaurant_menu_add'),
    path('restaurant-panel/menu/<int:item_id>/edit/', views.restaurant_menu_edit, name='restaurant_menu_edit'),
    path('restaurant-panel/menu/<int:item_id>/delete/', views.restaurant_menu_delete, name='restaurant_menu_delete'),
    path('restaurant-panel/orders/', views.restaurant_orders, name='restaurant_orders'),
    path('restaurant-panel/orders/<int:order_id>/<str:action>/', views.restaurant_order_action, name='restaurant_order_action'),
    path('restaurant-panel/sales/', views.restaurant_sales, name='restaurant_sales'),

    # Delivery dashboard
    path('delivery-panel/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery-panel/accept/<int:order_id>/', views.delivery_accept_order, name='delivery_accept_order'),
    path('delivery-panel/update/<int:order_id>/<str:action>/', views.delivery_update_status, name='delivery_update_status'),
    path('delivery-panel/earnings/', views.delivery_earnings, name='delivery_earnings'),

    # Admin dashboard (custom)
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/<int:user_id>/toggle-block/', views.admin_toggle_block, name='admin_toggle_block'),
    path('admin-panel/restaurants/', views.admin_restaurants, name='admin_restaurants'),
    path('admin-panel/restaurants/<int:restaurant_id>/toggle-approval/', views.admin_toggle_restaurant_approval, name='admin_toggle_restaurant_approval'),
    path('admin-panel/delivery-partners/', views.admin_delivery_partners, name='admin_delivery_partners'),
    path('admin-panel/delivery-partners/<int:partner_id>/toggle-approval/', views.admin_toggle_delivery_approval, name='admin_toggle_delivery_approval'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('admin-panel/categories/', views.admin_categories, name='admin_categories'),
    path('admin-panel/categories/<int:category_id>/toggle/', views.admin_category_toggle, name='admin_category_toggle'),
    path('admin-panel/coupons/', views.admin_coupons, name='admin_coupons'),
    path('admin-panel/reports/', views.admin_reports, name='admin_reports'),
]
