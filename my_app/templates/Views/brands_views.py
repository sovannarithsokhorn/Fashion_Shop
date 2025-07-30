from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from my_app.models import Brand  # Import your Brand model


def index(request):
    """
    Renders the brand listing page, displaying all brands.
    """
    brands = Brand.objects.all().order_by('brand_name')
    context = {
        'brands': brands
    }
    return render(request, "pages/brands/index.html", context)


def create_brand(request):
    """
    Handles GET and POST requests for creating a new brand.
    """
    if request.method == "POST":
        brand_name = request.POST.get("brand_name", "").strip()
        description = request.POST.get("description", "").strip()
        website_url = request.POST.get("website_url", "").strip()

        errors = {}

        if not brand_name:
            errors['brand_name'] = 'Brand name is required.'
        elif Brand.objects.filter(brand_name__iexact=brand_name).exists():  # Case-insensitive check
            errors['brand_name'] = f'Brand "{brand_name}" already exists.'

        # Basic URL validation (Django's URLField does more robust validation on save)
        if website_url and not (website_url.startswith('http://') or website_url.startswith('https://')):
            errors['website_url'] = 'Website URL must start with http:// or https://'

        if not errors:
            try:
                brand = Brand(
                    brand_name=brand_name,
                    description=description if description else None,
                    website_url=website_url if website_url else None
                )
                brand.full_clean()  # Run model's clean method for field validation
                brand.save()
                messages.success(request, f'Brand "{brand.brand_name}" added successfully!')
                return redirect('brand_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error creating brand. Please check the form.')
            except IntegrityError as e:
                # Catch database integrity errors (e.g., unique constraints not caught by full_clean)
                if 'unique constraint' in str(e).lower() and 'brand_name' in str(e).lower():
                    errors['brand_name'] = 'This brand name already exists.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error creating brand. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f"An unexpected error occurred: {str(e)}"

        context = {
            'brand_data': {
                'brand_name': brand_name,
                'description': description,
                'website_url': website_url,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/brands/create.html", context)
    else:
        context = {
            'brand_data': {},
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/brands/create.html", context)


def edit_brand(request, pk):
    """
    Handles GET and POST requests for editing an existing brand.
    """
    brand = get_object_or_404(Brand, pk=pk)

    if request.method == "POST":
        brand_name = request.POST.get("brand_name", "").strip()
        description = request.POST.get("description", "").strip()
        website_url = request.POST.get("website_url", "").strip()

        errors = {}

        if not brand_name:
            errors['brand_name'] = 'Brand name is required.'
        elif Brand.objects.filter(brand_name__iexact=brand_name).exclude(pk=brand.pk).exists():
            errors['brand_name'] = f'Brand "{brand_name}" already exists.'

        if website_url and not (website_url.startswith('http://') or website_url.startswith('https://')):
            errors['website_url'] = 'Website URL must start with http:// or https://'

        if not errors:
            try:
                brand.brand_name = brand_name
                brand.description = description if description else None
                brand.website_url = website_url if website_url else None
                brand.full_clean()
                brand.save()
                messages.success(request, f'Brand "{brand.brand_name}" updated successfully!')
                return redirect('brand_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error updating brand. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'brand_name' in str(e).lower():
                    errors['brand_name'] = 'This brand name already exists.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error updating brand. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f"An unexpected error occurred: {str(e)}"

        context = {
            'brand': brand,  # Pass the original brand object
            'brand_data': {
                'brand_name': brand_name,
                'description': description,
                'website_url': website_url,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/brands/edit.html", context)
    else:
        context = {
            'brand': brand,
            'brand_data': {
                'brand_name': brand.brand_name,
                'description': brand.description,
                'website_url': brand.website_url,
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/brands/edit.html", context)


@require_POST
def delete_brand(request, pk):
    """
    Handles POST requests to delete a brand.
    """
    try:
        brand = get_object_or_404(Brand, pk=pk)
        brand_name = brand.brand_name
        brand.delete()
        messages.success(request, f'Brand "{brand_name}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting brand: {str(e)}')
    return redirect('brand_index')
