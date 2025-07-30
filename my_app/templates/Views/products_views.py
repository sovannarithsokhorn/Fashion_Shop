import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Sum, Prefetch, Q  # Import Q for complex queries
from decimal import Decimal, InvalidOperation
from datetime import date

# --- MODELS IMPORTS ---
from my_app.models import Product, Category, Brand, GENDER_CHOICES, ProductImage, Review  # Added Review


# --- END MODELS IMPORTS ---


# --- CRUCIAL: Ensure total_stock property is in your Product model in my_app/models.py ---
# (Same reminder as before, ensure this property and Sum import are in your models.py)


# This view is for listing all products
def index(request):
    """
    Renders the product list page, displaying all products.
    Pre-fetches the thumbnail image for each product to simplify template logic.
    Applies filters based on GET parameters.
    """
    products_queryset = Product.objects.all().select_related('brand', 'category').prefetch_related(
        Prefetch(
            'images',
            queryset=ProductImage.objects.filter(is_thumbnail=True).order_by('display_order')[:1],
            to_attr='thumbnail_image_object_list'
        )
    )

    # --- Filtering Logic ---
    search_query = request.GET.get('q')
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    status = request.GET.get('status')

    if search_query:
        products_queryset = products_queryset.filter(
            Q(product_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(variants__sku__icontains=search_query)  # Corrected: Search SKU through variants
        ).distinct()  # Use distinct to avoid duplicate products if multiple variants match

    if category_id:
        products_queryset = products_queryset.filter(category_id=category_id)

    if brand_id:
        products_queryset = products_queryset.filter(brand_id=brand_id)

    if status:
        if status == 'active':
            products_queryset = products_queryset.filter(is_active=True)
        elif status == 'inactive':
            products_queryset = products_queryset.filter(is_active=False)
    # --- End Filtering Logic ---

    products = products_queryset.order_by('product_name')

    for product in products:
        product.thumbnail_image = product.thumbnail_image_object_list[
            0] if product.thumbnail_image_object_list else None

    categories = Category.objects.all().order_by('category_name')
    brands = Brand.objects.all().order_by('brand_name')

    context = {
        'products': products,
        'categories': categories,
        'brands': brands,
        # Pass the current filter values back to the template for pre-selection
        'current_q': search_query,
        'current_category': category_id,
        'current_brand': brand_id,
        'current_status': status,
    }
    return render(request, "pages/products/index.html", context)


# This view is for rendering the product creation form
def show(request):
    """
    Renders the product creation form.
    Passes all available Category and Brand objects to the template for dropdowns.
    """
    categories = Category.objects.all().order_by('category_name')
    brands = Brand.objects.all().order_by('brand_name')
    context = {
        'categories': categories,
        'brands': brands,
        'gender_choices': GENDER_CHOICES,
        'product_data': {},
        'errors': {},
        'general_error': None,
    }
    return render(request, "pages/products/create.html", context)


# This view handles the POST request for creating a new product
def create(request):
    """
    Handles POST requests to create a new product manually without Django Forms.
    Includes logic to handle product image upload.
    """
    if request.method == 'POST':
        product_data = {
            'product_name': request.POST.get('product_name', '').strip(),
            'description': request.POST.get('description', '').strip(),
            'brand_id': request.POST.get('brand'),
            'category_id': request.POST.get('category'),
            'gender': request.POST.get('gender', '').strip(),
            'price': request.POST.get('price', '').strip(),
            'material': request.POST.get('material', '').strip(),
            'care_instructions': request.POST.get('care_instructions', '').strip(),
            'is_active': request.POST.get('is_active') == 'on',
        }

        errors = {}
        general_error = None

        # --- Manual Validation ---
        if not product_data['product_name']:
            errors['product_name'] = 'Product name is required.'

        if not product_data['price']:
            errors['price'] = 'Price is required.'
        else:
            try:
                product_data['price'] = Decimal(product_data['price'])
                if product_data['price'] <= 0:
                    errors['price'] = 'Price must be positive.'
            except InvalidOperation:
                errors['price'] = 'Invalid price format.'

        brand_obj = None
        if product_data['brand_id']:
            try:
                brand_obj = Brand.objects.get(pk=product_data['brand_id'])
            except Brand.DoesNotExist:
                errors['brand'] = 'Invalid brand selected.'

        category_obj = None
        if product_data['category_id']:
            try:
                category_obj = Category.objects.get(pk=product_data['category_id'])
            except Category.DoesNotExist:
                errors['category'] = 'Invalid category selected.'

        if product_data['gender'] and product_data['gender'] not in [c[0] for c in GENDER_CHOICES]:
            errors['gender'] = 'Invalid gender selected.'
        # --- End Manual Validation ---

        if not errors:
            try:
                product = Product.objects.create(
                    product_name=product_data['product_name'],
                    description=product_data['description'],
                    brand=brand_obj,
                    category=category_obj,
                    gender=product_data['gender'],
                    price=product_data['price'],
                    material=product_data['material'],
                    care_instructions=product_data['care_instructions'],
                    is_active=product_data['is_active']
                )

                # --- Image Upload Handling for Create ---
                uploaded_image = request.FILES.get('product_image')
                if uploaded_image:
                    try:
                        ProductImage.objects.create(
                            product=product,
                            image=uploaded_image,
                            is_thumbnail=True,  # Set as thumbnail for the first image
                            alt_text=f"Image for {product.product_name}"
                        )
                    except Exception as img_e:
                        messages.warning(request, f"Product created, but image upload failed: {str(img_e)}")
                        # Log the image error but don't prevent product creation
                        print(f"Image upload error for product {product.product_id}: {img_e}")
                else:
                    messages.info(request, "No image uploaded for the product.")

                messages.success(request,
                                 f'Product "{product.product_name}" added successfully! You can now add more variants and images.')
                return redirect('product_edit', pk=product.product_id)
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {e}')
                general_error = f'An unexpected error occurred during save: {str(e)}'

        # If there are errors, re-render the form with existing data and errors
        categories = Category.objects.all().order_by('category_name')
        brands = Brand.objects.all().order_by('brand_name')
        context = {
            'categories': categories,
            'brands': brands,
            'gender_choices': GENDER_CHOICES,
            'product_data': product_data,
            'errors': errors,
            'general_error': general_error,
        }
        return render(request, 'pages/products/create.html', context)
    else:
        # For GET request, redirect to show form
        return redirect('product_show')


@csrf_exempt
def delete_product(request, pk):
    """
    Handles POST requests to delete a product.
    """
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        product_name = product.product_name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('product_index')
    else:
        return HttpResponseNotAllowed(['POST'])


def edit(request, pk):
    """
    Renders the product edit form, pre-filling it with existing data.
    """
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all().order_by('category_name')
    brands = Brand.objects.all().order_by('brand_name')

    product_data = {
        'product_name': product.product_name,
        'description': product.description,
        'brand_id': product.brand.pk if product.brand else '',
        'category_id': product.category.pk if product.category else '',
        'gender': product.gender,
        'price': product.price,
        'material': product.material,
        'care_instructions': product.care_instructions,
        'is_active': product.is_active,
    }

    variants = product.variants.all()
    images = product.images.all()

    context = {
        'product': product,
        'product_data': product_data,
        'categories': categories,
        'brands': brands,
        'gender_choices': GENDER_CHOICES,
        'errors': {},
        'general_error': None,
        'variants': variants,
        'images': images,
    }
    return render(request, "pages/products/edit.html", context)


@csrf_exempt
def update_product(request, pk):
    """
    Handles POST requests to update an existing product manually without Django Forms.
    Includes logic to handle product image upload.
    """
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        product_data = {
            'product_name': request.POST.get('product_name', '').strip(),
            'description': request.POST.get('description', '').strip(),
            'brand_id': request.POST.get('brand'),
            'category_id': request.POST.get('category'),
            'gender': request.POST.get('gender', '').strip(),
            'price': request.POST.get('price', '').strip(),
            'material': request.POST.get('material', '').strip(),
            'care_instructions': request.POST.get('care_instructions', '').strip(),
            'is_active': request.POST.get('is_active') == 'on',
        }

        errors = {}
        general_error = None

        if not product_data['product_name']:
            errors['product_name'] = 'Product name is required.'

        if not product_data['price']:
            errors['price'] = 'Price is required.'
        else:
            try:
                product_data['price'] = Decimal(product_data['price'])
                if product_data['price'] <= 0:
                    errors['price'] = 'Price must be positive.'
            except InvalidOperation:
                errors['price'] = 'Invalid price format.'

        brand_obj = None
        if product_data['brand_id']:
            try:
                brand_obj = Brand.objects.get(pk=product_data['brand_id'])
            except Brand.DoesNotExist:
                errors['brand'] = 'Invalid brand selected.'

        category_obj = None
        if product_data['category_id']:
            try:
                category_obj = Category.objects.get(pk=product_data['category_id'])
            except Category.DoesNotExist:
                errors['category'] = 'Invalid category selected.'

        if product_data['gender'] and product_data['gender'] not in [c[0] for c in GENDER_CHOICES]:
            errors['gender'] = 'Invalid gender selected.'

        if not errors:
            try:
                product.product_name = product_data['product_name']
                product.description = product_data['description']
                product.brand = brand_obj
                product.category = category_obj
                product.gender = product_data['gender']
                product.price = product_data['price']
                product.material = product_data['material']
                product.care_instructions = product_data['care_instructions']
                product.is_active = product_data['is_active']
                product.save()

                # --- Image Upload Handling for Update ---
                uploaded_image = request.FILES.get('product_image')
                if uploaded_image:
                    try:
                        # Option: Delete existing thumbnail and create new one
                        # This assumes you only want one thumbnail at a time
                        old_thumbnail = product.images.filter(is_thumbnail=True).first()
                        if old_thumbnail:
                            old_thumbnail.delete()  # This will delete the image file too

                        ProductImage.objects.create(
                            product=product,
                            image=uploaded_image,
                            is_thumbnail=True,  # Set the new image as thumbnail
                            alt_text=f"Updated image for {product.product_name}"
                        )
                        messages.info(request, "Product image updated.")
                    except Exception as img_e:
                        messages.warning(request, f"Product updated, but image upload failed: {str(img_e)}")
                        print(f"Image upload error for product {product.product_id}: {img_e}")

                messages.success(request, f'Product "{product.product_name}" updated successfully!')
                return redirect('product_index')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {e}')
                general_error = f'An unexpected error occurred during save: {str(e)}'
    else:
        return HttpResponse("Method Not Allowed", status=405)

    categories = Category.objects.all().order_by('category_name')
    brands = Brand.objects.all().order_by('brand_name')
    variants = product.variants.all()
    images = product.images.all()

    context = {
        'product': product,
        'product_data': product_data,
        'categories': categories,
        'brands': brands,
        'gender_choices': GENDER_CHOICES,
        'errors': errors,
        'general_error': general_error,
        'variants': variants,
        'images': images,
    }
    return render(request, 'pages/products/edit.html', context)


def view_product(request, pk):
    """
    Renders the product detail page, displaying a single product's information.
    Ensures all related images and reviews are fetched.
    """
    product = get_object_or_404(Product, pk=pk)
    variants = product.variants.all()
    images = product.images.all()  # Fetch all images related to the product
    reviews = product.reviews.all().order_by('-review_date')  # NEW: Fetch all reviews for the product

    context = {
        'product': product,
        'variants': variants,
        'images': images,
        'reviews': reviews,  # NEW: Add reviews to the context
    }
    return render(request, "pages/products/detail.html", context)
