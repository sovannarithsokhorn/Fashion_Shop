import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import \
    csrf_exempt  # IMPORTANT: Use this carefully. For production, ensure X-CSRFToken header is sent with DELETE requests.
from django.contrib import messages

# --- MODELS IMPORTS ---
# Explicitly import Category from my_app.models
from my_app.models import Category


# --- END MODELS IMPORTS ---


def index(request):
    """
    Renders the categories listing page, displaying all categories.
    """
    categories = Category.objects.all().order_by('category_name')
    context = {
        'categories': categories
    }
    return render(request, "pages/categories/index.html", context)


def create(request):
    """
    Handles POST requests to create a new category.
    Manually validates data and saves the category.
    If successful, redirects to the category index. If not, re-renders the create page with errors.
    """
    if request.method == "POST":
        category_name = request.POST.get("category_name", "").strip()

        errors = {}

        # Manual Validation
        if not category_name:
            errors['category_name'] = 'Category name cannot be empty.'
        elif Category.objects.filter(category_name=category_name).exists():
            errors['category_name'] = f'Category "{category_name}" already exists.'

        if not errors:
            try:
                category = Category()
                category.category_name = category_name
                # Assuming no parent_category or description are handled by this simple create view
                category.save()
                messages.success(request, f'Category "{category.category_name}" added successfully!')
                return redirect('category_index')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        # If there are errors, or if not a POST request, re-render the form
        context = {
            'category_data': {'category_name': category_name},  # Pass back entered data
            'errors': errors,
        }
        return render(request, "pages/categories/create.html", context)
    else:
        # For GET request, render the empty create form
        context = {
            'category_data': {},
            'errors': {},
        }
        return render(request, "pages/categories/create.html", context)


@csrf_exempt  # IMPORTANT: For production, ensure your frontend sends the X-CSRFToken header with DELETE requests
def delete(request, category_id):
    """
    Handles DELETE requests to delete a specific category.
    Returns JSON response for success or failure.
    """
    if request.method == 'DELETE':
        try:
            category = get_object_or_404(Category, category_id=category_id)
            category_name = category.category_name  # Get name before deleting for message
            category.delete()
            return JsonResponse({"message": f"Category '{category_name}' deleted successfully!"}, status=200)
        except Exception as e:
            return JsonResponse({"message": f"Error deleting category: {str(e)}"}, status=500)
    return HttpResponseNotAllowed(['DELETE'])


def edit(request, category_id):
    """
    Renders the category edit form, pre-filling it with existing data.
    """
    category = get_object_or_404(Category, category_id=category_id)
    context = {
        "category": category,  # The actual category object
        "category_data": {'category_name': category.category_name},  # Data for pre-filling the form field
        "errors": {},  # No errors on initial GET request
    }
    return render(request, "pages/categories/edit.html", context)


@csrf_exempt  # Use @csrf_protect if consistent CSRF token is sent with all POSTs.
def update_category(request, category_id):
    """
    Handles POST requests to update a specific category.
    Manually validates data and updates the category.
    Returns JSON response for success or failure (if used via AJAX) or redirects.
    """
    if request.method == 'POST':
        try:
            category = get_object_or_404(Category, category_id=category_id)
            new_category_name = request.POST.get('category_name', '').strip()

            errors = {}

            # Manual Validation
            if not new_category_name:
                errors['category_name'] = 'Category name cannot be empty.'
            # Check for uniqueness, excluding the current category being updated
            elif Category.objects.filter(category_name=new_category_name).exclude(
                    category_id=category.category_id).exists():
                errors['category_name'] = f'Category name "{new_category_name}" already exists.'

            if not errors:
                category.category_name = new_category_name
                # Assuming no other fields like description or parent_category are updated here
                category.save()
                messages.success(request, f'Category "{category.category_name}" updated successfully!')
                return redirect('category_index')  # Redirect after successful update
            else:
                # If there are errors, re-render the edit form with errors
                context = {
                    "category": category,
                    "category_data": {'category_name': new_category_name},
                    "errors": errors,
                }
                messages.error(request, 'Error updating category. Please check the form.')
                return render(request, "pages/categories/edit.html", context)

        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            # If an unexpected error, try to re-render the form with a general error
            category = get_object_or_404(Category, category_id=category_id)
            context = {
                "category": category,
                "category_data": {'category_name': request.POST.get('category_name', '').strip()},
                "errors": {'__all__': f"An unexpected error occurred: {str(e)}"},
            }
            return render(request, "pages/categories/edit.html", context)
    else:
        # Only allow POST requests for this view
        return HttpResponse("Method Not Allowed", status=405)

