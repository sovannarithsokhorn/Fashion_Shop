from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

# --- MODELS IMPORTS ---
from my_app.models import Review, Product, Customer


# --- END MODELS IMPORTS ---


def index(request):
    """
    Renders the review listing page, displaying all reviews.
    """
    reviews = Review.objects.all().order_by('-review_date')
    context = {
        'reviews': reviews
    }
    return render(request, "pages/reviews/index.html", context)


def create_review(request):
    """
    Handles GET and POST requests for creating a new review.
    """
    products = Product.objects.all().order_by('product_name')
    customers = Customer.objects.all().order_by('email')  # Or by name

    if request.method == "POST":
        product_id = request.POST.get("product")
        customer_id = request.POST.get("customer")
        rating = request.POST.get("rating")
        review_text = request.POST.get("review_text", "").strip()
        is_approved = request.POST.get("is_approved") == 'on'

        errors = {}

        product_obj = None
        if not product_id:
            errors['product'] = 'Product is required.'
        else:
            try:
                product_obj = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                errors['product'] = 'Invalid product selected.'

        customer_obj = None
        if customer_id:  # Customer can be optional (anonymous review)
            try:
                customer_obj = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                errors['customer'] = 'Invalid customer selected.'

        if not rating:
            errors['rating'] = 'Rating is required.'
        else:
            try:
                rating = int(rating)
                if not (1 <= rating <= 5):
                    errors['rating'] = 'Rating must be between 1 and 5.'
            except ValueError:
                errors['rating'] = 'Invalid rating format.'

        # Check for unique_together constraint: one review per customer per product
        if product_obj and customer_obj and Review.objects.filter(product=product_obj, customer=customer_obj).exists():
            errors['__all__'] = 'This customer has already reviewed this product.'

        if not errors:
            try:
                review = Review(
                    product=product_obj,
                    customer=customer_obj,
                    rating=rating,
                    review_text=review_text if review_text else None,
                    is_approved=is_approved
                )
                review.full_clean()
                review.save()
                messages.success(request, f'Review for "{product_obj.product_name}" created successfully!')
                return redirect('review_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error creating review. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'product' in str(e).lower() and 'customer' in str(
                        e).lower():
                    errors['__all__'] = 'This customer has already reviewed this product.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error creating review. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'products': products,
            'customers': customers,
            'review_data': {
                'product_id': product_id,
                'customer_id': customer_id,
                'rating': rating,
                'review_text': review_text,
                'is_approved': is_approved,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/reviews/create.html", context)
    else:
        context = {
            'products': products,
            'customers': customers,
            'review_data': {
                'is_approved': False  # Default to not approved for new reviews
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/reviews/create.html", context)


def edit_review(request, pk):
    """
    Handles GET and POST requests for editing an existing review.
    """
    review = get_object_or_404(Review, pk=pk)
    products = Product.objects.all().order_by('product_name')
    customers = Customer.objects.all().order_by('email')

    if request.method == "POST":
        product_id = request.POST.get("product")
        customer_id = request.POST.get("customer")
        rating = request.POST.get("rating")
        review_text = request.POST.get("review_text", "").strip()
        is_approved = request.POST.get("is_approved") == 'on'

        errors = {}

        product_obj = None
        if not product_id:
            errors['product'] = 'Product is required.'
        else:
            try:
                product_obj = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                errors['product'] = 'Invalid product selected.'

        customer_obj = None
        if customer_id:
            try:
                customer_obj = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                errors['customer'] = 'Invalid customer selected.'

        if not rating:
            errors['rating'] = 'Rating is required.'
        else:
            try:
                rating = int(rating)
                if not (1 <= rating <= 5):
                    errors['rating'] = 'Rating must be between 1 and 5.'
            except ValueError:
                errors['rating'] = 'Invalid rating format.'

        # Check for unique_together constraint, excluding the current review
        if product_obj and customer_obj and Review.objects.filter(product=product_obj, customer=customer_obj).exclude(
                pk=review.pk).exists():
            errors['__all__'] = 'This customer has already reviewed this product.'

        if not errors:
            try:
                review.product = product_obj
                review.customer = customer_obj
                review.rating = rating
                review.review_text = review_text if review_text else None
                review.is_approved = is_approved
                review.full_clean()
                review.save()
                messages.success(request, f'Review for "{review.product.product_name}" updated successfully!')
                return redirect('review_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error updating review. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'product' in str(e).lower() and 'customer' in str(
                        e).lower():
                    errors['__all__'] = 'This customer has already reviewed this product.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error updating review. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'review': review,
            'products': products,
            'customers': customers,
            'review_data': {
                'product_id': product_id,
                'customer_id': customer_id,
                'rating': rating,
                'review_text': review_text,
                'is_approved': is_approved,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/reviews/edit.html", context)
    else:
        context = {
            'review': review,
            'products': products,
            'customers': customers,
            'review_data': {
                'product_id': review.product.pk if review.product else '',
                'customer_id': review.customer.pk if review.customer else '',
                'rating': review.rating,
                'review_text': review.review_text,
                'is_approved': review.is_approved,
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/reviews/edit.html", context)


@require_POST
def delete_review(request, pk):
    """
    Handles POST requests to delete a review.
    """
    try:
        review = get_object_or_404(Review, pk=pk)
        product_name = review.product.product_name if review.product else 'N/A'
        customer_email = review.customer.email if review.customer else 'Anonymous'
        review.delete()
        messages.success(request, f'Review for "{product_name}" by "{customer_email}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting review: {str(e)}')
    return redirect('review_index')


def view_review(request, pk):
    """
    Renders the review detail page, displaying a single review's information.
    """
    review = get_object_or_404(Review, pk=pk)
    context = {
        'review': review,
    }
    return render(request, "pages/reviews/detail.html", context)

