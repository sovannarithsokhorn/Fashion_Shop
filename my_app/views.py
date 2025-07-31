from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

# --- Existing imports for dashboard and other views ---
from django.db.models import Sum, Q, F, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, InvalidOperation

# Ensure these models are correctly defined in your my_app/models.py
from my_app.models import (
    Product, ProductVariant, Order, OrderItem, Customer, Category, Brand, Promotion, Review,
    GENDER_CHOICES, DISCOUNT_TYPE_CHOICES, ORDER_STATUS_CHOICES, PAYMENT_STATUS_CHOICES
)


# --- End Existing imports ---


# Home view
@login_required
def home(request):
    return render(request, "index.html")


# Dashboard view
@login_required
def dashboard(request):
    """
    Renders the admin dashboard with various key performance indicators (KPIs).
    Calculates sales summaries, order statistics, stock alerts, and total counts.
    """
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to access the dashboard.")
        return redirect('login')

    today = timezone.localdate()
    now = timezone.now()

    end_date_30_days = now
    start_date_30_days = now - timedelta(days=30)

    total_sales_last_30_days = Order.objects.filter(
        order_date__range=(start_date_30_days, end_date_30_days),
        payment_status='PAID'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    start_date_prev_30_days = start_date_30_days - timedelta(days=30)
    total_sales_prev_30_days = Order.objects.filter(
        order_date__range=(start_date_prev_30_days, start_date_30_days),
        payment_status='PAID'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    sales_percentage_change = Decimal('0.00')
    if total_sales_prev_30_days > 0:
        sales_percentage_change = ((
                                               total_sales_last_30_days - total_sales_prev_30_days) / total_sales_prev_30_days) * 100
    elif total_sales_last_30_days > 0:
        sales_percentage_change = Decimal('100.00')

    new_orders_today = Order.objects.filter(order_date__date=today).count()
    pending_orders = Order.objects.filter(order_status='PENDING').count()
    shipped_orders = Order.objects.filter(order_status='SHIPPED').count()

    LOW_STOCK_THRESHOLD = 10

    low_stock_products_count = Product.objects.filter(
        variants__quantity_in_stock__lte=LOW_STOCK_THRESHOLD,
        is_active=True
    ).distinct().count()

    total_products_count = Product.objects.count()
    total_categories_count = Category.objects.count()

    recent_orders = Order.objects.all().order_by('-order_date')[:5]
    recent_reviews = Review.objects.all().order_by('-review_date')[:5]

    recent_activities = []
    for order in recent_orders:
        recent_activities.append({
            'description': f"New order #{order.order_id} by {order.customer.first_name if order.customer else 'Guest'}",
            'date': order.order_date
        })
    for review in recent_reviews:
        recent_activities.append({
            'description': f"New review for {review.product.product_name} ({review.rating} stars)",
            'date': review.review_date
        })
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:5]

    context = {
        'total_sales_last_30_days': total_sales_last_30_days,
        'sales_percentage_change': sales_percentage_change,
        'new_orders_today': new_orders_today,
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'low_stock_products_count': low_stock_products_count,
        'total_products_count': total_products_count,
        'total_categories_count': total_categories_count,
        'recent_activities': recent_activities,
    }

    # Retrieve SweetAlert flags from session and remove them ONLY here
    login_success = request.session.pop('login_success', False)
    logged_in_username = request.session.pop('logged_in_username', '')

    context['login_success'] = login_success
    context['logged_in_username'] = logged_in_username

    return render(request, "pages/dashboard.html", context)


# --- Authentication Views ---

def login_view(request):
    """
    Handles user login.
    If POST, attempts to authenticate with either username or email.
    If successful, sets session flags for SweetAlert and redirects to dashboard.
    If GET or authentication fails, renders the login form.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        identifier = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        user = authenticate(request, username=identifier, password=password)

        if user is None:
            try:
                user_by_email = User.objects.get(email=identifier)
                user = authenticate(request, username=user_by_email.username, password=password)
            except User.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            if remember_me:
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

                # Set session variables for SweetAlert (do NOT pop here)
            request.session['login_success'] = True
            request.session['logged_in_username'] = user.username

            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials. Please try again.")
            return render(request, 'pages/auth/login_register.html',
                          {'form_type': 'login', 'request_post': request.POST})

    # For GET request to login page, just render the form.
    # SweetAlert flags are handled by the dashboard view after redirect.
    context = {
        'form_type': 'login',
        # Do NOT pop session variables here for GET requests to login page
        # 'login_success': request.session.pop('login_success', False),
        # 'logged_in_username': request.session.pop('logged_in_username', ''),
    }
    return render(request, 'pages/auth/login_register.html', context)


def register_view(request):
    """
    Handles user registration.
    If POST, attempts to create a new user with username, email, and password.
    If successful, logs them in and redirects.
    If GET or registration fails, re-renders the registration form.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        agree_terms = request.POST.get('agree_terms') == 'on'

        errors = {}

        if not username:
            errors['username'] = "Username is required."
        elif User.objects.filter(username=username).exists():
            errors['username'] = "This username is already taken."

        if not email:
            errors['email'] = "Email is required."
        elif User.objects.filter(email=email).exists():
            errors['email'] = "A user with that email already exists."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 8:
            errors['password'] = "Password must be at least 8 characters long."

        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not agree_terms:
            errors['agree_terms'] = "You must agree to the Terms of Service and Privacy Policy."

        if errors:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form_type': 'register',
                'errors': errors,
                'request_post': request.POST
            }
            return render(request, 'pages/auth/login_register.html', context)

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            user.save()

            login(request, user)
            messages.success(request, "Account created successfully! Welcome to Fashion Admin.")
            return redirect('dashboard')
        except IntegrityError:
            messages.error(request, "A user with that username or email already exists.")
            context = {
                'form_type': 'register',
                'request_post': request.POST
            }
            return render(request, 'pages/auth/login_register.html', context)
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}")
            context = {
                'form_type': 'register',
                'request_post': request.POST
            }
            return render(request, 'pages/auth/login_register.html', context)

    return render(request, 'pages/auth/login_register.html', {'form_type': 'register'})


def logout_view(request):
    """
    Logs out the current user and redirects to the login page.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
def user_detail_view(request):
    """
    Renders the user detail page for the currently logged-in user.
    Handles POST requests to update user information.
    """
    user = request.user
    errors = {}
    general_error = None

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()

        if not email:
            errors['email'] = 'Email is required.'
        elif User.objects.filter(email=email).exclude(pk=user.pk).exists():
            errors['email'] = 'This email is already in use by another account.'

        if not errors:
            try:
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.full_clean()
                user.save()
                messages.success(request, "Your profile has been updated successfully!")
                return redirect('user_detail')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error updating profile. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'username' in str(e).lower():
                    errors['email'] = 'The email you entered is already linked to another account.'
                else:
                    general_error = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error updating profile. Please check the form.')
            except Exception as e:
                general_error = f"An unexpected error occurred: {str(e)}"
                messages.error(request, 'An unexpected error occurred while updating your profile.')

        context = {
            'user_obj': user,
            'errors': errors,
            'general_error': general_error,
        }
        return render(request, 'pages/auth/user_detail.html', context)

    context = {
        'user_obj': user,
        'errors': errors,
        'general_error': general_error,
    }
    return render(request, 'pages/auth/user_detail.html', context)
