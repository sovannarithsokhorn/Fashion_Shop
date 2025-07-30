from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone  # For last_login
from django.db.models import Sum, Avg, Max  # For calculating order statistics
from decimal import Decimal  # NEW: Import Decimal for financial calculations

# --- MODELS IMPORTS ---
from my_app.models import Customer, Address, Order  # Assuming these models exist


# --- END MODELS IMPORTS ---


def index(request):
    """
    Renders the customer listing page, displaying all customers.
    """
    customers = Customer.objects.all().order_by('-registration_date')
    context = {
        'customers': customers
    }
    return render(request, "pages/customers/index.html", context)


def create_customer(request):
    """
    Handles GET and POST requests for creating a new customer.
    """
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        password_hash = request.POST.get("password_hash", "").strip()  # In a real app, hash this!
        phone_number = request.POST.get("phone_number", "").strip()
        profile_picture = request.FILES.get('profile_picture')  # Get the uploaded file
        notes = request.POST.get("notes", "").strip()  # Get notes

        errors = {}

        if not first_name:
            errors['first_name'] = 'First name is required.'
        if not last_name:
            errors['last_name'] = 'Last name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif Customer.objects.filter(email__iexact=email).exists():
            errors['email'] = f'Customer with email "{email}" already exists.'
        if not password_hash:
            errors['password_hash'] = 'Password hash is required.'  # Reminder: Hash passwords securely!

        if not errors:
            try:
                customer = Customer(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password_hash=password_hash,  # Again, hash this in production!
                    phone_number=phone_number if phone_number else None,
                    registration_date=timezone.now(),
                    last_login=None,  # Set to None initially
                    profile_picture=profile_picture,  # Assign the uploaded picture
                    notes=notes if notes else None  # Assign notes
                )
                customer.full_clean()  # Run model's clean method for field validation
                customer.save()
                messages.success(request, f'Customer "{customer.email}" added successfully!')
                return redirect('customer_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error creating customer. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'email' in str(e).lower():
                    errors['email'] = 'A customer with this email already exists.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error creating customer. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'customer_data': {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'password_hash': password_hash,
                'phone_number': phone_number,
                'notes': notes,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/customers/create.html", context)
    else:
        context = {
            'customer_data': {},
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/customers/create.html", context)


def edit_customer(request, pk):
    """
    Handles GET and POST requests for editing an existing customer.
    """
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        profile_picture = request.FILES.get('profile_picture')  # Get the uploaded file
        notes = request.POST.get("notes", "").strip()  # Get notes

        errors = {}

        if not first_name:
            errors['first_name'] = 'First name is required.'
        if not last_name:
            errors['last_name'] = 'Last name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif Customer.objects.filter(email__iexact=email).exclude(pk=customer.pk).exists():
            errors['email'] = f'Customer with email "{email}" already exists.'

        if not errors:
            try:
                customer.first_name = first_name
                customer.last_name = last_name
                customer.email = email
                customer.phone_number = phone_number if phone_number else None
                if profile_picture:  # Update picture only if a new one is provided
                    customer.profile_picture = profile_picture
                customer.notes = notes if notes else None  # Update notes
                customer.full_clean()
                customer.save()
                messages.success(request, f'Customer "{customer.email}" updated successfully!')
                return redirect('customer_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error updating customer. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'email' in str(e).lower():
                    errors['email'] = 'A customer with this email already exists.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error updating customer. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'customer': customer,
            'customer_data': {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone_number': phone_number,
                'notes': notes,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/customers/edit.html", context)
    else:
        context = {
            'customer': customer,
            'customer_data': {
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'email': customer.email,
                'phone_number': customer.phone_number,
                'notes': customer.notes,
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/customers/edit.html", context)


@require_POST
def delete_customer(request, pk):
    """
    Handles POST requests to delete a customer.
    """
    try:
        customer = get_object_or_404(Customer, pk=pk)
        customer_email = customer.email
        customer.delete()
        messages.success(request, f'Customer "{customer_email}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting customer: {str(e)}')
    return redirect('customer_index')


def view_customer(request, pk):
    """
    Renders the customer detail page, displaying a single customer's information
    and their associated addresses, along with order history and statistics.
    """
    customer = get_object_or_404(Customer, pk=pk)
    addresses = customer.addresses.all()  # Fetch all addresses related to the customer

    # Fetch orders and calculate statistics
    orders = customer.orders.all().order_by('-order_date')
    total_orders = orders.count()
    total_spent = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    average_order = orders.aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0.00')
    last_order = orders.aggregate(Max('order_date'))['order_date__max']

    context = {
        'customer': customer,
        'addresses': addresses,
        'orders': orders,  # Pass orders for the history table
        'total_orders': total_orders,
        'total_spent': total_spent,
        'average_order': average_order,
        'last_order': last_order,
        'is_premium_customer': total_spent >= 1000,  # Example logic for premium customer
        'shopping_preferences': "Dresses, Casual Wear, Size M",  # Placeholder for now
    }
    return render(request, "pages/customers/detail.html", context)
