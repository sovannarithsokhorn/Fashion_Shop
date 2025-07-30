from django.shortcuts import render
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta, date

# --- MODELS IMPORTS ---
from my_app.models import Order, ProductVariant, Product, Category # Assuming these models exist
# --- END MODELS IMPORTS ---


def dashboard(request):
    """
    Renders the admin dashboard with dynamic data fetched from the database.
    Includes sales summary, order overview, stock alerts, and recent activities.
    Also includes total product and category counts.
    """
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    sixty_days_ago = today - timedelta(days=60)

    # --- Sales Summary ---
    total_sales_last_30_days = Order.objects.filter(
        order_date__date__gte=thirty_days_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    total_sales_prev_30_days = Order.objects.filter(
        order_date__date__gte=sixty_days_ago,
        order_date__date__lt=thirty_days_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    sales_percentage_change = 0
    if total_sales_prev_30_days > 0:
        sales_percentage_change = ((total_sales_last_30_days - total_sales_prev_30_days) / total_sales_prev_30_days) * 100

    # --- Orders Overview ---
    new_orders_today = Order.objects.filter(order_date__date=today).count()
    pending_orders = Order.objects.filter(order_status='PENDING').count()
    shipped_orders = Order.objects.filter(order_status='SHIPPED').count()

    # --- Product Stock Alerts ---
    # Assuming "low stock" is defined as quantity_in_stock less than 10
    low_stock_products_count = ProductVariant.objects.filter(quantity_in_stock__lt=10).count()

    # --- Total Counts ---
    total_products_count = Product.objects.count()
    total_categories_count = Category.objects.count()

    # --- Recent Activity (Simplified for common actions) ---
    # Fetching recent orders and products
    # Limit to a reasonable number to avoid heavy queries for recent activity
    recent_orders = Order.objects.all().order_by('-order_date')[:10].values(
        'order_id', 'order_date', 'customer__first_name', 'customer__last_name'
    )
    recent_products = Product.objects.all().order_by('-created_at')[:10].values(
        'product_name', 'created_at'
    )
    # For categories, assuming no 'created_at'/'updated_at' field in the Category model.
    # We'll use the current time as a placeholder for display purposes, ordered by category_id as a proxy for recency.
    recent_categories = Category.objects.all().order_by('-category_id')[:10].values(
        'category_name'
    )

    # Format recent activities for display and consistent sorting
    recent_activities = []

    for order in recent_orders:
        customer_name = f"{order['customer__first_name']} {order['customer__last_name']}" if order['customer__first_name'] else 'Guest'
        recent_activities.append({
            'type': 'Order',
            'description': f"Order #{order['order_id']} placed by {customer_name}",
            'date': order['order_date'] # This is a datetime object
        })

    for product in recent_products:
        recent_activities.append({
            'type': 'Product',
            'description': f"New product \"{product['product_name']}\" added",
            'date': product['created_at'] # This is a datetime object
        })

    for category in recent_categories:
        # Placeholder for category activity date if no specific timestamp field exists in Category model.
        # To get actual creation/update times for categories, you would need to add
        # `created_at = models.DateTimeField(auto_now_add=True)` and/or
        # `updated_at = models.DateTimeField(auto_now=True)` to your Category model.
        recent_activities.append({
            'type': 'Category',
            'description': f"Category \"{category['category_name']}\" added/updated",
            'date': timezone.now() # Using current time as a proxy for recent activity
        })

    # Sort all activities by date in descending order and limit to top 5
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:5] # Limit to top 5 after combining and sorting

    context = {
        'total_sales_last_30_days': total_sales_last_30_days,
        'sales_percentage_change': sales_percentage_change,
        'new_orders_today': new_orders_today,
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'low_stock_products_count': low_stock_products_count,
        'total_products_count': total_products_count, # Added total products count
        'total_categories_count': total_categories_count, # Added total categories count
        'recent_activities': recent_activities,
    }
    return render(request, "pages/dashboard.html", context)
