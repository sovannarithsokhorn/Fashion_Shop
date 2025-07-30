from django.urls import path, include
# Removed: from django.conf.urls.static import static
# Removed: from FASHION_SHOP import settings
from . import views  # Assuming this contains your home and dashboard views
from .templates.Views import categories_views, products_views, dashboard_views, inventory_views, \
    brands_views, orders_views, customers_views, promotions_views, reviews_views  # Corrected import path

urlpatterns = [
    path("", views.home, name='home'),
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),

    # Category URLs
    path("category/index", categories_views.index, name='category_index'),
    path("category/add/", categories_views.create, name='category_create'),
    path("category/<int:category_id>/delete/", categories_views.delete, name='category_delete'),
    path("category/<int:category_id>/edit/", categories_views.edit, name='category_edit'),
    path("category/<int:category_id>/update/", categories_views.update_category, name='category_update'),

    # Product URLs
    path("product/index", products_views.index, name='product_index'),
    path("product/add/", products_views.show, name='product_show'),
    path("product/create/", products_views.create, name='product_create'),
    path("product/<int:pk>/delete/", products_views.delete_product, name='product_delete'),
    path("product/<int:pk>/edit/", products_views.edit, name='product_edit'),
    path("product/<int:pk>/update/", products_views.update_product, name='product_update'),
    path("product/<int:pk>/view/", products_views.view_product, name='product_view'),

    path('inventory/', inventory_views.index, name='inventory_index'),
    path('inventory/create/', inventory_views.create_variant, name='inventory_create_variant'),
    path('inventory/<int:pk>/edit/', inventory_views.edit_variant, name='inventory_edit_variant'),  # NEW
    path('inventory/<int:pk>/delete/', inventory_views.delete_variant, name='inventory_delete_variant'),
    # New Inventory URL

    # Brand URLs
    path('brands/', brands_views.index, name='brand_index'),
    path('brands/add/', brands_views.create_brand, name='brand_create'),  # NEW
    path('brands/<int:pk>/edit/', brands_views.edit_brand, name='brand_edit'),  # NEW
    path('brands/<int:pk>/delete/', brands_views.delete_brand, name='brand_delete'),  # NEW

    # Order URLs (NEW)
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

    # Promotion URLs (NEW)
    path('promotions/', promotions_views.index, name='promotion_index'),
    path('promotions/add/', promotions_views.create_promotion, name='promotion_create'),
    path('promotions/<int:pk>/edit/', promotions_views.edit_promotion, name='promotion_edit'),
    path('promotions/<int:pk>/delete/', promotions_views.delete_promotion, name='promotion_delete'),
    path('promotions/<int:pk>/view/', promotions_views.view_promotion, name='promotion_detail'),
    # Review URLs (NEW)
    path('reviews/', reviews_views.index, name='review_index'),
    path('reviews/add/', reviews_views.create_review, name='review_create'),
    path('reviews/<int:pk>/edit/', reviews_views.edit_review, name='review_edit'),
    path('reviews/<int:pk>/delete/', reviews_views.delete_review, name='review_delete'),
    path('reviews/<int:pk>/view/', reviews_views.view_review, name='review_detail'),
]

# Removed this block: Serving static/media files should typically be in your project's main urls.py (FASHION_SHOP/urls.py)
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
