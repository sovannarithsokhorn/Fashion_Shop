from django.urls import path, include
from . import views # For login, register, logout, home, user_detail, dashboard (if dashboard is in main views.py)

# Corrected imports for specific view modules
# Assuming these view modules are located in a 'views' subdirectory within 'admin_dashboard'
# For example: admin_dashboard/views/categories_views.py
from my_app.templates.Views import (
    categories_views,
    products_views,
    dashboard_views, # If dashboard_views is a separate module
    inventory_views,
    brands_views,
    orders_views,
    customers_views,
    promotions_views,
    reviews_views,
    members_views,  # Import the members_views module
)

urlpatterns = [
    # Auth URLs
    path("login/", views.login_view, name='login'),
    path("register/", views.register_view, name='register'),
    path("logout/", views.logout_view, name='logout'),
    path("password_reset/", views.login_view, name='password_reset'), # Note: This points to login_view, might need a dedicated reset view
    path("profile/", views.user_detail_view, name='user_detail'),

    path("", views.home, name='home'),
    # Use dashboard_views if it's a separate module, otherwise use views.dashboard
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),

    # Category URLs
    path("category/index", categories_views.index, name='category_index'),
    path("category/add/", categories_views.create, name='category_create'),
    path("category/<int:category_id>/delete/", categories_views.delete, name='category_delete'),
    path("category/<int:category_id>/edit/", categories_views.edit, name='category_edit'),
    path("category/<int:category_id>/update/", categories_views.update_category, name='category_update'),

    # Product URLs
    path("product/index", products_views.index, name='product_index'),
    path("product/add/", products_views.show, name='product_show'), # 'show' typically implies detail, 'add' usually maps to 'create'
    path("product/create/", products_views.create, name='product_create'),
    path("product/<int:pk>/delete/", products_views.delete_product, name='product_delete'),
    path("product/<int:pk>/edit/", products_views.edit, name='product_edit'),
    path("product/<int:pk>/update/", products_views.update_product, name='product_update'),
    path("product/<int:pk>/view/", products_views.view_product, name='product_view'),

    # Inventory URLs
    path('inventory/', inventory_views.index, name='inventory_index'),
    path('inventory/create/', inventory_views.create_variant, name='inventory_create_variant'),
    path('inventory/<int:pk>/edit/', inventory_views.edit_variant, name='inventory_edit_variant'),
    path('inventory/<int:pk>/delete/', inventory_views.delete_variant, name='inventory_delete_variant'),

    # Brand URLs
    path('brands/', brands_views.index, name='brand_index'),
    path('brands/add/', brands_views.create_brand, name='brand_create'),
    path('brands/<int:pk>/edit/', brands_views.edit_brand, name='brand_edit'),
    path('brands/<int:pk>/delete/', brands_views.delete_brand, name='brand_delete'),

    # Order URLs
    path('orders/', orders_views.index, name='order_index'),
    path('orders/create/', orders_views.create_order, name='order_create'),
    path('orders/<int:pk>/edit/', orders_views.edit_order, name='order_edit'),
    path('orders/<int:pk>/delete/', orders_views.delete_order, name='order_delete'),
    path('orders/<int:order_pk>/items/add/', orders_views.add_order_item, name='order_add_item'),
    path('orders/<int:order_pk>/items/<int:item_pk>/edit/', orders_views.edit_order_item, name='order_edit_item'),
    path('orders/<int:order_pk>/items/<int:item_pk>/delete/', orders_views.delete_order_item, name='order_delete_item'),

    # Customer URLs
    path('customers/', customers_views.index, name='customer_index'),
    path('customers/add/', customers_views.create_customer, name='customer_create'),
    path('customers/<int:pk>/edit/', customers_views.edit_customer, name='customer_edit'),
    path('customers/<int:pk>/delete/', customers_views.delete_customer, name='customer_delete'),
    path('customers/<int:pk>/view/', customers_views.view_customer, name='customer_detail'),

    # Promotion URLs
    path('promotions/', promotions_views.index, name='promotion_index'),
    path('promotions/add/', promotions_views.create_promotion, name='promotion_create'),
    path('promotions/<int:pk>/edit/', promotions_views.edit_promotion, name='promotion_edit'),
    path('promotions/<int:pk>/delete/', promotions_views.delete_promotion, name='promotion_delete'),
    path('promotions/<int:pk>/view/', promotions_views.view_promotion, name='promotion_detail'),

    # Review URLs
    path('reviews/', reviews_views.index, name='review_index'),
    path('reviews/add/', reviews_views.create_review, name='review_create'),
    path('reviews/<int:pk>/edit/', reviews_views.edit_review, name='review_edit'),
    path('reviews/<int:pk>/delete/', reviews_views.delete_review, name='review_delete'),
    path('reviews/<int:pk>/view/', reviews_views.view_review, name='review_detail'),

    # Member URLs (Updated for Function-Based Views)
    path('members/', members_views.index, name='member_index'),
    path('members/add/', members_views.create_member, name='member_create'),
    path('members/<int:pk>/edit/', members_views.edit_member, name='member_edit'),
    path('members/<int:pk>/delete/', members_views.delete_member, name='member_delete'),
    path('members/<int:pk>/view/', members_views.view_member, name='member_detail'),
]
