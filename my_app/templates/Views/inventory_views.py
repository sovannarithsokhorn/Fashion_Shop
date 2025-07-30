from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction  # Import transaction
from django.views.decorators.http import require_POST  # Import for delete view

# --- MODELS IMPORTS ---
from my_app.models import ProductVariant, Product, Category, Brand  # Assuming these models exist


# --- END MODELS IMPORTS ---


def index(request):
    """
    Renders the inventory listing page, displaying all product variants
    with their stock levels and related product information.
    """
    # Fetch all ProductVariants and prefetch related Product, Category, and Brand
    # This reduces the number of database queries for related data
    variants = ProductVariant.objects.select_related('product', 'product__category', 'product__brand').order_by(
        'product__product_name', 'color', 'size')

    context = {
        'variants': variants,
        'low_stock_threshold': 10,  # Define a threshold for highlighting low stock
    }
    return render(request, "pages/inventory/index.html", context)


def create_variant(request):
    """
    Handles POST requests to create new product variants based on multiple size selections.
    Manually validates data and saves variants.
    If successful, redirects to the inventory index. If not, re-renders the create page with errors.
    """
    products = Product.objects.all().order_by('product_name')  # Fetch all products for dropdown

    # Define size and color options here to pass to the template
    size_options = ['S', 'M', 'L', 'XL', 'XXL']
    color_options = ['Red', 'Blue', 'Green', 'Black', 'White', 'Gray']

    if request.method == "POST":
        product_id = request.POST.get("product")
        color = request.POST.get("color", "").strip()  # Now from a dropdown
        sizes = request.POST.getlist("size")  # Get list of selected sizes
        quantity_in_stock = request.POST.get("quantity_in_stock", "").strip()

        errors = {}
        selected_product = None
        variants_to_create = []  # List to hold variant data before saving

        # Manual Validation for Product and Color (needed for SKU generation)
        if not product_id:
            errors['product'] = 'Product is required.'
        else:
            try:
                selected_product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                errors['product'] = 'Selected product does not exist.'

        if not color:
            errors['color'] = 'Color cannot be empty.'
        elif color not in color_options:  # Validate selected color against predefined options
            errors['color'] = 'Invalid color selected.'

        if not sizes:  # Validate that at least one size is selected
            errors['size'] = 'At least one size must be selected.'
        else:
            # Validate each selected size against predefined options
            for s in sizes:
                if s not in size_options:
                    errors['size'] = 'Invalid size(s) selected.'
                    break  # Stop checking if one invalid size is found

        if not quantity_in_stock:
            errors['quantity_in_stock'] = 'Quantity cannot be empty.'
        else:
            try:
                quantity_in_stock = int(quantity_in_stock)
                if quantity_in_stock < 0:
                    errors['quantity_in_stock'] = 'Quantity must be a non-negative number.'
            except ValueError:
                errors['quantity_in_stock'] = 'Quantity must be a valid number.'

        # If initial validations pass, prepare variants and check SKUs
        if not errors and selected_product and color:
            for size_item in sizes:
                # Format product ID to be zero-padded, e.g., 001, 010
                formatted_product_id = str(selected_product.product_id).zfill(3)
                # Sanitize color and size for SKU
                sanitized_color = ''.join(filter(str.isalnum, color)).replace(' ', '')  # Remove spaces too
                sanitized_size = ''.join(filter(str.isalnum, size_item)).replace(' ', '')  # Remove spaces too

                generated_sku = f"PROD{formatted_product_id}-{sanitized_color}-{sanitized_size}"

                # Check if this specific generated SKU already exists
                if ProductVariant.objects.filter(sku=generated_sku).exists():
                    errors[
                        'sku'] = f'SKU "{generated_sku}" for size {size_item} already exists. Please choose a different color/size combination for this product.'
                    break  # Stop processing if a duplicate SKU is found

                variants_to_create.append({
                    'product': selected_product,
                    'color': color,
                    'size': size_item,
                    'sku': generated_sku,
                    'quantity_in_stock': quantity_in_stock
                })
        elif not errors:  # If no errors but product/color are missing, add SKU generation error
            if not selected_product:
                errors['sku'] = 'Cannot generate SKU: A valid product must be selected.'
            if not color:
                errors['sku'] = (errors.get('sku', '') + ' ' if errors.get(
                    'sku') else '') + 'Cannot generate SKU: Color cannot be empty.'

        if not errors:  # Proceed only if no validation errors so far
            try:
                with transaction.atomic():  # Ensure all variants are created or none are
                    for variant_data in variants_to_create:
                        variant = ProductVariant(
                            product=variant_data['product'],
                            color=variant_data['color'],
                            size=variant_data['size'],
                            sku=variant_data['sku'],
                            quantity_in_stock=variant_data['quantity_in_stock']
                        )
                        variant.full_clean()  # Run model's clean method for field validation
                        variant.save()
                messages.success(request, f'Successfully added {len(variants_to_create)} product variant(s)!')
                return redirect('inventory_index')
            except ValidationError as e:
                # Map Django's ValidationError messages back to the form fields
                for field, field_errors in e.message_dict.items():
                    if field == 'sku' and 'sku' not in errors:  # Don't overwrite existing SKU errors
                        errors['sku'] = field_errors[0]
                    elif field != 'sku':  # For other fields, just add the error
                        errors[field] = field_errors[0]
                messages.error(request, 'Error creating product variant. Please check the form.')
            except IntegrityError as e:
                # Catch database integrity errors (e.g., unique constraints)
                if 'unique constraint' in str(e).lower() and 'sku' in str(e).lower():
                    errors[
                        'sku'] = 'One or more generated SKUs already exist. Please choose a different color/size combination for the product.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error creating product variant. Please check the form.')
            except Exception as e:
                # Catch any other unexpected errors
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f"An unexpected error occurred: {str(e)}"

        # If there are errors, re-render the form with entered data and errors
        context = {
            'products': products,
            'size_options': size_options,  # Pass size options to template
            'color_options': color_options,  # Pass color options to template
            'variant_data': {
                'product_id': product_id,
                'color': color,
                'size': sizes,  # Pass the list of selected sizes back
                'sku': errors.get('sku', ''),  # Only pass SKU error if it exists, as it's generated
                'quantity_in_stock': request.POST.get("quantity_in_stock", "")
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/inventory/create_variant.html", context)
    else:
        # For GET request, render the empty create form
        context = {
            'products': products,
            'size_options': size_options,  # Pass size options to template
            'color_options': color_options,  # Pass color options to template
            'variant_data': {'size': []},  # Initialize size as an empty list for GET requests
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/inventory/create_variant.html", context)


def edit_variant(request, pk):
    """
    Handles GET and POST requests for editing an existing product variant.
    """
    variant = get_object_or_404(ProductVariant, pk=pk)
    products = Product.objects.all().order_by('product_name')
    size_options = ['S', 'M', 'L', 'XL', 'XXL']
    color_options = ['Red', 'Blue', 'Green', 'Black', 'White', 'Gray']

    if request.method == "POST":
        product_id = request.POST.get("product")
        color = request.POST.get("color", "").strip()
        size = request.POST.get("size", "").strip()  # Single size from dropdown for edit
        quantity_in_stock = request.POST.get("quantity_in_stock", "").strip()

        errors = {}
        selected_product = None

        # Manual Validation
        if not product_id:
            errors['product'] = 'Product is required.'
        else:
            try:
                selected_product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                errors['product'] = 'Selected product does not exist.'

        if not color:
            errors['color'] = 'Color cannot be empty.'
        elif color not in color_options:
            errors['color'] = 'Invalid color selected.'

        if not size:
            errors['size'] = 'Size cannot be empty.'
        elif size not in size_options:
            errors['size'] = 'Invalid size selected.'

        if not quantity_in_stock:
            errors['quantity_in_stock'] = 'Quantity cannot be empty.'
        else:
            try:
                quantity_in_stock = int(quantity_in_stock)
                if quantity_in_stock < 0:
                    errors['quantity_in_stock'] = 'Quantity must be a non-negative number.'
            except ValueError:
                errors['quantity_in_stock'] = 'Quantity must be a valid number.'

        # SKU auto-generation and uniqueness check for update
        generated_sku = ""
        if selected_product and color and size and not errors.get('product') and not errors.get(
                'color') and not errors.get('size'):
            formatted_product_id = str(selected_product.product_id).zfill(3)
            sanitized_color = ''.join(filter(str.isalnum, color)).replace(' ', '')
            sanitized_size = ''.join(filter(str.isalnum, size)).replace(' ', '')
            generated_sku = f"PROD{formatted_product_id}-{sanitized_color}-{sanitized_size}"

            # Check if the generated SKU already exists for *other* variants
            if ProductVariant.objects.filter(sku=generated_sku).exclude(pk=variant.pk).exists():
                errors[
                    'sku'] = f'SKU "{generated_sku}" already exists for another variant. Please choose a different color/size combination.'
        elif not errors:  # If no errors but product/color/size are missing, add SKU generation error
            if not selected_product:
                errors['sku'] = 'Cannot generate SKU: A valid product must be selected.'
            if not color:
                errors['sku'] = (errors.get('sku', '') + ' ' if errors.get(
                    'sku') else '') + 'Cannot generate SKU: Color cannot be empty.'
            if not size:
                errors['sku'] = (errors.get('sku', '') + ' ' if errors.get(
                    'sku') else '') + 'Cannot generate SKU: Size cannot be empty.'

        if not errors:
            try:
                variant.product = selected_product
                variant.color = color
                variant.size = size
                variant.sku = generated_sku  # Update with generated SKU
                variant.quantity_in_stock = quantity_in_stock
                variant.full_clean()
                variant.save()
                messages.success(request, f'Product variant "{variant.sku}" updated successfully!')
                return redirect('inventory_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    if field == 'sku' and 'sku' not in errors:
                        errors['sku'] = field_errors[0]
                    elif field != 'sku':
                        errors[field] = field_errors[0]
                messages.error(request, 'Error updating product variant. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'sku' in str(e).lower():
                    errors['sku'] = 'This SKU already exists. Please choose a different color/size for the product.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error updating product variant. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f"An unexpected error occurred: {str(e)}"

        context = {
            'variant': variant,  # Pass the original variant object for context
            'products': products,
            'size_options': size_options,
            'color_options': color_options,
            'variant_data': {  # Data for pre-filling form fields
                'product_id': product_id,
                'color': color,
                'size': size,
                'sku': generated_sku,  # Pass generated SKU back
                'quantity_in_stock': request.POST.get("quantity_in_stock", "")
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/inventory/edit_variant.html", context)
    else:
        # GET request: Pre-fill form with existing variant data
        context = {
            'variant': variant,
            'products': products,
            'size_options': size_options,
            'color_options': color_options,
            'variant_data': {
                'product_id': variant.product.pk,
                'color': variant.color,
                'size': variant.size,
                'sku': variant.sku,
                'quantity_in_stock': variant.quantity_in_stock
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/inventory/edit_variant.html", context)


@require_POST  # Ensures this view only accepts POST requests
def delete_variant(request, pk):
    """
    Handles POST requests to delete a specific product variant.
    """
    try:
        variant = get_object_or_404(ProductVariant, pk=pk)
        sku = variant.sku  # Get SKU before deleting for message
        variant.delete()
        messages.success(request, f'Product variant "{sku}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting product variant: {str(e)}')
    return redirect('inventory_index')

