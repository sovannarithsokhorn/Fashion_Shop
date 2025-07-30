from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from decimal import Decimal

# --- MODELS IMPORTS ---
from my_app.models import Promotion, DISCOUNT_TYPE_CHOICES


# --- END MODELS IMPORTS ---


def index(request):
    """
    Renders the promotion listing page, displaying all promotions.
    """
    promotions = Promotion.objects.all().order_by('-start_date')
    context = {
        'promotions': promotions
    }
    return render(request, "pages/promotions/index.html", context)


def create_promotion(request):
    """
    Handles GET and POST requests for creating a new promotion.
    """
    if request.method == "POST":
        promo_code = request.POST.get("promo_code", "").strip()
        description = request.POST.get("description", "").strip()
        discount_type = request.POST.get("discount_type", "").strip()
        discount_value = request.POST.get("discount_value", "").strip()
        start_date_str = request.POST.get("start_date", "").strip()
        end_date_str = request.POST.get("end_date", "").strip()
        min_order_amount = request.POST.get("min_order_amount", "").strip()
        usage_limit = request.POST.get("usage_limit", "").strip()
        per_customer_limit = request.POST.get("per_customer_limit", "").strip()
        is_active = request.POST.get("is_active") == 'on'

        errors = {}

        if not promo_code:
            errors['promo_code'] = 'Promo code is required.'
        elif Promotion.objects.filter(promo_code__iexact=promo_code).exists():
            errors['promo_code'] = f'Promotion with code "{promo_code}" already exists.'

        if not discount_type:
            errors['discount_type'] = 'Discount type is required.'
        elif discount_type not in [c[0] for c in DISCOUNT_TYPE_CHOICES]:
            errors['discount_type'] = 'Invalid discount type.'

        if not discount_value:
            errors['discount_value'] = 'Discount value is required.'
        else:
            try:
                discount_value = Decimal(discount_value)
                if discount_value <= 0:
                    errors['discount_value'] = 'Discount value must be positive.'
            except InvalidOperation:
                errors['discount_value'] = 'Invalid discount value format.'

        if not start_date_str:
            errors['start_date'] = 'Start date is required.'
        if not end_date_str:
            errors['end_date'] = 'End date is required.'

        start_date = None
        end_date = None
        try:
            if start_date_str:
                start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            errors['start_date'] = 'Invalid start date format.'

        try:
            if end_date_str:
                end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            errors['end_date'] = 'Invalid end date format.'

        if start_date and end_date and start_date >= end_date:
            errors['end_date'] = 'End date must be after start date.'

        if min_order_amount:
            try:
                min_order_amount = Decimal(min_order_amount)
                if min_order_amount < 0:
                    errors['min_order_amount'] = 'Min order amount cannot be negative.'
            except InvalidOperation:
                errors['min_order_amount'] = 'Invalid min order amount format.'
        else:
            min_order_amount = None

        if usage_limit:
            try:
                usage_limit = int(usage_limit)
                if usage_limit < 0:
                    errors['usage_limit'] = 'Usage limit cannot be negative.'
            except ValueError:
                errors['usage_limit'] = 'Invalid usage limit format.'
        else:
            usage_limit = None

        if per_customer_limit:
            try:
                per_customer_limit = int(per_customer_limit)
                if per_customer_limit < 0:
                    errors['per_customer_limit'] = 'Per customer limit cannot be negative.'
            except ValueError:
                errors['per_customer_limit'] = 'Invalid per customer limit format.'
        else:
            per_customer_limit = None

        if not errors:
            try:
                promotion = Promotion(
                    promo_code=promo_code,
                    description=description if description else None,
                    discount_type=discount_type,
                    discount_value=discount_value,
                    start_date=start_date,
                    end_date=end_date,
                    min_order_amount=min_order_amount,
                    usage_limit=usage_limit,
                    per_customer_limit=per_customer_limit,
                    is_active=is_active
                )
                promotion.full_clean()
                promotion.save()
                messages.success(request, f'Promotion "{promotion.promo_code}" created successfully!')
                return redirect('promotion_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error creating promotion. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'promo_code' in str(e).lower():
                    errors['promo_code'] = 'A promotion with this code already exists.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error creating promotion. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'discount_type_choices': DISCOUNT_TYPE_CHOICES,
            'promotion_data': {
                'promo_code': promo_code,
                'description': description,
                'discount_type': discount_type,
                'discount_value': str(discount_value) if isinstance(discount_value, Decimal) else discount_value,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'min_order_amount': str(min_order_amount) if isinstance(min_order_amount,
                                                                        Decimal) else min_order_amount,
                'usage_limit': usage_limit,
                'per_customer_limit': per_customer_limit,
                'is_active': is_active,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/promotions/create.html", context)
    else:
        context = {
            'discount_type_choices': DISCOUNT_TYPE_CHOICES,
            'promotion_data': {
                'is_active': True  # Default to active for new promotions
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/promotions/create.html", context)


def edit_promotion(request, pk):
    """
    Handles GET and POST requests for editing an existing promotion.
    """
    promotion = get_object_or_404(Promotion, pk=pk)

    if request.method == "POST":
        promo_code = request.POST.get("promo_code", "").strip()
        description = request.POST.get("description", "").strip()
        discount_type = request.POST.get("discount_type", "").strip()
        discount_value = request.POST.get("discount_value", "").strip()
        start_date_str = request.POST.get("start_date", "").strip()
        end_date_str = request.POST.get("end_date", "").strip()
        min_order_amount = request.POST.get("min_order_amount", "").strip()
        usage_limit = request.POST.get("usage_limit", "").strip()
        per_customer_limit = request.POST.get("per_customer_limit", "").strip()
        is_active = request.POST.get("is_active") == 'on'

        errors = {}

        if not promo_code:
            errors['promo_code'] = 'Promo code is required.'
        elif Promotion.objects.filter(promo_code__iexact=promo_code).exclude(pk=promotion.pk).exists():
            errors['promo_code'] = f'Promotion with code "{promo_code}" already exists.'

        if not discount_type:
            errors['discount_type'] = 'Discount type is required.'
        elif discount_type not in [c[0] for c in DISCOUNT_TYPE_CHOICES]:
            errors['discount_type'] = 'Invalid discount type.'

        if not discount_value:
            errors['discount_value'] = 'Discount value is required.'
        else:
            try:
                discount_value = Decimal(discount_value)
                if discount_value <= 0:
                    errors['discount_value'] = 'Discount value must be positive.'
            except InvalidOperation:
                errors['discount_value'] = 'Invalid discount value format.'

        if not start_date_str:
            errors['start_date'] = 'Start date is required.'
        if not end_date_str:
            errors['end_date'] = 'End date is required.'

        start_date = None
        end_date = None
        try:
            if start_date_str:
                start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            errors['start_date'] = 'Invalid start date format.'

        try:
            if end_date_str:
                end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            errors['end_date'] = 'Invalid end date format.'

        if start_date and end_date and start_date >= end_date:
            errors['end_date'] = 'End date must be after start date.'

        if min_order_amount:
            try:
                min_order_amount = Decimal(min_order_amount)
                if min_order_amount < 0:
                    errors['min_order_amount'] = 'Min order amount cannot be negative.'
            except InvalidOperation:
                errors['min_order_amount'] = 'Invalid min order amount format.'
        else:
            min_order_amount = None

        if usage_limit:
            try:
                usage_limit = int(usage_limit)
                if usage_limit < 0:
                    errors['usage_limit'] = 'Usage limit cannot be negative.'
            except ValueError:
                errors['usage_limit'] = 'Invalid usage limit format.'
        else:
            usage_limit = None

        if per_customer_limit:
            try:
                per_customer_limit = int(per_customer_limit)
                if per_customer_limit < 0:
                    errors['per_customer_limit'] = 'Per customer limit cannot be negative.'
            except ValueError:
                errors['per_customer_limit'] = 'Invalid per customer limit format.'
        else:
            per_customer_limit = None

        if not errors:
            try:
                promotion.promo_code = promo_code
                promotion.description = description if description else None
                promotion.discount_type = discount_type
                promotion.discount_value = discount_value
                promotion.start_date = start_date
                promotion.end_date = end_date
                promotion.min_order_amount = min_order_amount
                promotion.usage_limit = usage_limit
                promotion.per_customer_limit = per_customer_limit
                promotion.is_active = is_active
                promotion.full_clean()
                promotion.save()
                messages.success(request, f'Promotion "{promotion.promo_code}" updated successfully!')
                return redirect('promotion_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error updating promotion. Please check the form.')
            except IntegrityError as e:
                if 'unique constraint' in str(e).lower() and 'promo_code' in str(e).lower():
                    errors['promo_code'] = 'A promotion with this code already exists.'
                else:
                    errors['__all__'] = f"An unexpected database error occurred: {str(e)}"
                messages.error(request, 'Error updating promotion. Please check the form.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

        context = {
            'promotion': promotion,
            'discount_type_choices': DISCOUNT_TYPE_CHOICES,
            'promotion_data': {
                'promo_code': promo_code,
                'description': description,
                'discount_type': discount_type,
                'discount_value': str(discount_value) if isinstance(discount_value, Decimal) else discount_value,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'min_order_amount': str(min_order_amount) if isinstance(min_order_amount,
                                                                        Decimal) else min_order_amount,
                'usage_limit': usage_limit,
                'per_customer_limit': per_customer_limit,
                'is_active': is_active,
            },
            'errors': errors,
            'general_error': errors.get('__all__'),
        }
        return render(request, "pages/promotions/edit.html", context)
    else:
        context = {
            'promotion': promotion,
            'discount_type_choices': DISCOUNT_TYPE_CHOICES,
            'promotion_data': {
                'promo_code': promotion.promo_code,
                'description': promotion.description,
                'discount_type': promotion.discount_type,
                'discount_value': promotion.discount_value,
                'start_date': promotion.start_date.strftime('%Y-%m-%dT%H:%M') if promotion.start_date else '',
                'end_date': promotion.end_date.strftime('%Y-%m-%dT%H:%M') if promotion.end_date else '',
                'min_order_amount': promotion.min_order_amount,
                'usage_limit': promotion.usage_limit,
                'per_customer_limit': promotion.per_customer_limit,
                'is_active': promotion.is_active,
            },
            'errors': {},
            'general_error': None,
        }
        return render(request, "pages/promotions/edit.html", context)


@require_POST
def delete_promotion(request, pk):
    """
    Handles POST requests to delete a promotion.
    """
    try:
        promotion = get_object_or_404(Promotion, pk=pk)
        promo_code = promotion.promo_code
        promotion.delete()
        messages.success(request, f'Promotion "{promo_code}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting promotion: {str(e)}')
    return redirect('promotion_index')


def view_promotion(request, pk):
    """
    Renders the promotion detail page, displaying a single promotion's information.
    """
    promotion = get_object_or_404(Promotion, pk=pk)
    context = {
        'promotion': promotion,
    }
    return render(request, "pages/promotions/detail.html", context)

