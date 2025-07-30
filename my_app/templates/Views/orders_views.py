from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from decimal import Decimal, InvalidOperation

# --- MODELS IMPORTS ---
from my_app.models import Order, Customer, Address, ProductVariant, OrderItem, ORDER_STATUS_CHOICES, \
    PAYMENT_STATUS_CHOICES


# --- END MODELS IMPORTS ---


def index(request):
    """
    Renders the order listing page, displaying all orders.
    """
    orders = Order.objects.select_related('customer', 'shipping_address', 'billing_address').order_by('-order_date')
    context = {
        'orders': orders
    }
    return render(request, "pages/orders/index.html", context)


def create_order(request):
    """
    Handles GET and POST requests for creating a new order.
    Focuses on main order details. Redirects to edit page after creation to add items.
    """
    customers = Customer.objects.all().order_by('first_name', 'last_name')
    # For addresses, we'll need to filter by customer later, or provide a generic list
    # For simplicity, initially show all addresses, or handle dynamically with JS
    addresses = Address.objects.all().order_by('address_line1')

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        shipping_address_id = request.POST.get("shipping_address")
        billing_address_id = request.POST.get("billing_address")
        order_status = request.POST.get("order_status", "PENDING").strip()
        payment_status = request.POST.get("payment_status", "PENDING").strip()
        shipping_method = request.POST.get("shipping_method", "").strip()
        tracking_number = request.POST.get("tracking_number", "").strip()

        errors = {}
        selected_customer = None
        selected_shipping_address = None
        selected_billing_address = None

        if not customer_id:
            errors['customer'] = 'Customer is required.'
        else:
            try:
                selected_customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                errors['customer'] = 'Selected customer does not exist.'

        if shipping_address_id:
            try:
                selected_shipping_address = Address.objects.get(pk=shipping_address_id)
            except Address.DoesNotExist:
                errors['shipping_address'] = 'Selected shipping address does not exist.'

        if billing_address_id:
            try:
                selected_billing_address = Address.objects.get(pk=billing_address_id)
            except Address.DoesNotExist:
                errors['billing_address'] = 'Selected billing address does not exist.'

        if order_status not in [c[0] for c in ORDER_STATUS_CHOICES]:
            errors['order_status'] = 'Invalid order status selected.'
        if payment_status not in [c[0] for c in PAYMENT_STATUS_CHOICES]:
            errors['payment_status'] = 'Invalid payment status selected.'

        if not errors:
            try:
                order = Order(
                    customer=selected_customer,
                    shipping_address=selected_shipping_address,
                    billing_address=selected_billing_address,
                    order_status=order_status,
                    payment_status=payment_status,
                    shipping_method=shipping_method if shipping_method else None,
                    tracking_number=tracking_number if tracking_number else None,
                    total_amount=Decimal('0.00')  # Initialize total_amount to 0, will be updated by order items
                )
                order.full_clean()
                order.save()
                messages.success(request, f'Order #{order.order_id} created successfully! Now add items to it.')
                return redirect('order_edit', pk=order.pk)
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error creating order. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'customers': customers,
            'addresses': addresses,  # Pass all addresses for now
            'order_status_choices': ORDER_STATUS_CHOICES,
            'payment_status_choices': PAYMENT_STATUS_CHOICES,
            'order_data': {
                'customer_id': customer_id,
                'shipping_address_id': shipping_address_id,
                'billing_address_id': billing_address_id,
                'order_status': order_status,
                'payment_status': payment_status,
                'shipping_method': shipping_method,
                'tracking_number': tracking_number,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/orders/create.html", context)
    else:
        context = {
            'customers': customers,
            'addresses': addresses,
            'order_status_choices': ORDER_STATUS_CHOICES,
            'payment_status_choices': PAYMENT_STATUS_CHOICES,
            'order_data': {},
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/orders/create.html", context)


def edit_order(request, pk):
    """
    Handles GET and POST requests for editing an existing order.
    Allows updating main order details and managing order items.
    """
    order = get_object_or_404(Order.objects.select_related('customer', 'shipping_address', 'billing_address'), pk=pk)
    customers = Customer.objects.all().order_by('first_name', 'last_name')
    addresses = Address.objects.all().order_by('address_line1')  # All addresses for selection
    order_items = order.items.select_related('variant__product').all()  # Fetch existing items

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        shipping_address_id = request.POST.get("shipping_address")
        billing_address_id = request.POST.get("billing_address")
        order_status = request.POST.get("order_status", "").strip()
        payment_status = request.POST.get("payment_status", "").strip()
        shipping_method = request.POST.get("shipping_method", "").strip()
        tracking_number = request.POST.get("tracking_number", "").strip()

        errors = {}
        selected_customer = None
        selected_shipping_address = None
        selected_billing_address = None

        if not customer_id:
            errors['customer'] = 'Customer is required.'
        else:
            try:
                selected_customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                errors['customer'] = 'Selected customer does not exist.'

        if shipping_address_id:
            try:
                selected_shipping_address = Address.objects.get(pk=shipping_address_id)
            except Address.DoesNotExist:
                errors['shipping_address'] = 'Selected shipping address does not exist.'

        if billing_address_id:
            try:
                selected_billing_address = Address.objects.get(pk=billing_address_id)
            except Address.DoesNotExist:
                errors['billing_address'] = 'Selected billing address does not exist.'

        if order_status not in [c[0] for c in ORDER_STATUS_CHOICES]:
            errors['order_status'] = 'Invalid order status selected.'
        if payment_status not in [c[0] for c in PAYMENT_STATUS_CHOICES]:
            errors['payment_status'] = 'Invalid payment status selected.'

        if not errors:
            try:
                order.customer = selected_customer
                order.shipping_address = selected_shipping_address
                order.billing_address = selected_billing_address
                order.order_status = order_status
                order.payment_status = payment_status
                order.shipping_method = shipping_method if shipping_method else None
                order.tracking_number = tracking_number if tracking_number else None
                order.full_clean()
                order.save()

                # Recalculate total_amount after potential item changes (or just save if no items changed here)
                order.total_amount = sum(item.quantity * item.price_at_purchase for item in order.items.all())
                order.save()

                messages.success(request, f'Order #{order.order_id} updated successfully!')
                return redirect('order_edit', pk=order.pk)  # Stay on edit page
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error updating order. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'order': order,
            'customers': customers,
            'addresses': addresses,
            'order_items': order_items,
            'order_status_choices': ORDER_STATUS_CHOICES,
            'payment_status_choices': PAYMENT_STATUS_CHOICES,
            'order_data': {
                'customer_id': customer_id,
                'shipping_address_id': shipping_address_id,
                'billing_address_id': billing_address_id,
                'order_status': order_status,
                'payment_status': payment_status,
                'shipping_method': shipping_method,
                'tracking_number': tracking_number,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/orders/edit.html", context)
    else:
        context = {
            'order': order,
            'customers': customers,
            'addresses': addresses,
            'order_items': order_items,
            'order_status_choices': ORDER_STATUS_CHOICES,
            'payment_status_choices': PAYMENT_STATUS_CHOICES,
            'order_data': {
                'customer_id': order.customer.pk if order.customer else '',
                'shipping_address_id': order.shipping_address.pk if order.shipping_address else '',
                'billing_address_id': order.billing_address.pk if order.billing_address else '',
                'order_status': order.order_status,
                'payment_status': order.payment_status,
                'shipping_method': order.shipping_method,
                'tracking_number': order.tracking_number,
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/orders/edit.html", context)


@require_POST
def delete_order(request, pk):
    """
    Handles POST requests to delete an order.
    """
    try:
        order = get_object_or_404(Order, pk=pk)
        order_id = order.order_id
        order.delete()
        messages.success(request, f'Order #{order_id} deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting order: {str(e)}')
    return redirect('order_index')


def add_order_item(request, order_pk):
    """
    Handles GET and POST requests for adding an item to an existing order.
    """
    order = get_object_or_404(Order, pk=order_pk)
    product_variants = ProductVariant.objects.select_related('product').order_by('product__product_name', 'color',
                                                                                 'size')

    if request.method == "POST":
        variant_id = request.POST.get("variant")
        quantity = request.POST.get("quantity", "").strip()

        errors = {}
        selected_variant = None

        if not variant_id:
            errors['variant'] = 'Product variant is required.'
        else:
            try:
                selected_variant = ProductVariant.objects.get(pk=variant_id)
            except ProductVariant.DoesNotExist:
                errors['variant'] = 'Selected product variant does not exist.'

        if not quantity:
            errors['quantity'] = 'Quantity is required.'
        else:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    errors['quantity'] = 'Quantity must be a positive number.'
                elif selected_variant and quantity > selected_variant.quantity_in_stock:
                    errors['quantity'] = f'Not enough stock. Only {selected_variant.quantity_in_stock} available.'
            except ValueError:
                errors['quantity'] = 'Quantity must be a valid number.'

        if not errors:
            try:
                with transaction.atomic():
                    # Check if item already exists in order, update quantity if so
                    order_item, created = OrderItem.objects.get_or_create(
                        order=order,
                        variant=selected_variant,
                        defaults={
                            'quantity': quantity,
                            'price_at_purchase': selected_variant.product.price  # Use product price for now
                        }
                    )
                    if not created:
                        order_item.quantity += quantity
                        order_item.save()

                    # Update order total amount
                    order.total_amount = sum(item.quantity * item.price_at_purchase for item in order.items.all())
                    order.save()

                    messages.success(request,
                                     f'Item "{selected_variant.sku}" added/updated in Order #{order.order_id}!')
                    return redirect('order_edit', pk=order.pk)
            except IntegrityError as e:
                messages.error(request,
                               f'An item with this variant already exists in the order. Please edit the existing item instead. Error: {str(e)}')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'order': order,
            'product_variants': product_variants,
            'item_data': {
                'variant_id': variant_id,
                'quantity': request.POST.get("quantity", "")
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/orders/add_item.html", context)
    else:
        context = {
            'order': order,
            'product_variants': product_variants,
            'item_data': {},
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/orders/add_item.html", context)


def edit_order_item(request, order_pk, item_pk):
    """
    Handles GET and POST requests for editing an existing order item.
    """
    order = get_object_or_404(Order, pk=order_pk)
    order_item = get_object_or_404(OrderItem.objects.select_related('variant__product'), pk=item_pk, order=order)
    product_variants = ProductVariant.objects.select_related('product').order_by('product__product_name', 'color',
                                                                                 'size')

    if request.method == "POST":
        variant_id = request.POST.get("variant")
        quantity = request.POST.get("quantity", "").strip()
        price_at_purchase = request.POST.get("price_at_purchase", "").strip()

        errors = {}
        selected_variant = None

        if not variant_id:
            errors['variant'] = 'Product variant is required.'
        else:
            try:
                selected_variant = ProductVariant.objects.get(pk=variant_id)
            except ProductVariant.DoesNotExist:
                errors['variant'] = 'Selected product variant does not exist.'

        if not quantity:
            errors['quantity'] = 'Quantity is required.'
        else:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    errors['quantity'] = 'Quantity must be a positive number.'
                # Check stock only if variant changed or quantity increased
                if selected_variant and (
                        selected_variant.pk != order_item.variant.pk or quantity > order_item.quantity):
                    available_stock = selected_variant.quantity_in_stock
                    if selected_variant.pk == order_item.variant.pk:  # Same variant, check against current stock + original item quantity
                        available_stock += order_item.quantity
                    if quantity > available_stock:
                        errors[
                            'quantity'] = f'Not enough stock. Only {available_stock} available for {selected_variant.sku}.'
            except ValueError:
                errors['quantity'] = 'Quantity must be a valid number.'

        if not price_at_purchase:
            errors['price_at_purchase'] = 'Price at purchase is required.'
        else:
            try:
                price_at_purchase = Decimal(price_at_purchase)
                if price_at_purchase <= 0:
                    errors['price_at_purchase'] = 'Price at purchase must be positive.'
            except InvalidOperation:
                errors['price_at_purchase'] = 'Invalid price format.'

        if not errors:
            try:
                with transaction.atomic():
                    order_item.variant = selected_variant
                    order_item.quantity = quantity
                    order_item.price_at_purchase = price_at_purchase
                    order_item.full_clean()
                    order_item.save()

                    # Update order total amount
                    order.total_amount = sum(item.quantity * item.price_at_purchase for item in order.items.all())
                    order.save()

                    messages.success(request,
                                     f'Item "{order_item.variant.sku}" in Order #{order.order_id} updated successfully!')
                    return redirect('order_edit', pk=order.pk)
            except IntegrityError as e:
                messages.error(request, f'An item with this variant already exists in the order. Error: {str(e)}')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'order': order,
            'order_item': order_item,
            'product_variants': product_variants,
            'item_data': {
                'variant_id': variant_id,
                'quantity': request.POST.get("quantity", ""),
                'price_at_purchase': request.POST.get("price_at_purchase", "")
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/orders/edit_item.html", context)
    else:
        context = {
            'order': order,
            'order_item': order_item,
            'product_variants': product_variants,
            'item_data': {
                'variant_id': order_item.variant.pk,
                'quantity': order_item.quantity,
                'price_at_purchase': order_item.price_at_purchase
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/orders/edit_item.html", context)


@require_POST
def delete_order_item(request, order_pk, item_pk):
    """
    Handles POST requests to delete an item from an order.
    """
    try:
        order = get_object_or_404(Order, pk=order_pk)
        order_item = get_object_or_404(OrderItem, pk=item_pk, order=order)
        item_sku = order_item.variant.sku  # Get SKU before deleting for message
        order_item.delete()

        # Update order total amount after item deletion
        order.total_amount = sum(item.quantity * item.price_at_purchase for item in order.items.all())
        order.save()

        messages.success(request, f'Item "{item_sku}" deleted from Order #{order.order_id} successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting order item: {str(e)}')
    return redirect('order_edit', pk=order.pk)

