from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
import datetime # Import datetime for date parsing

# IMPORTANT: Adjust this import path based on your actual project structure.
# If your models.py is in the parent directory of this views file (e.g., my_app/models.py),
# then 'from ..models import Member' is likely correct.
# If models.py is in the same directory as this views file (less common for app views),
# then 'from .models import Member' would be used.
from my_app.models import Member


# --- LIST VIEW ---
@login_required
def index(request):
    """
    Renders the member listing page, displaying all members.
    The 'members' queryset is ordered by their creation date.
    """
    # Fetch all Member objects from the database
    members = Member.objects.all().order_by('created_at')
    context = {
        'members': members
    }
    return render(request, "pages/members/index.html", context)


# --- CREATE VIEW ---
@login_required
def create_member(request):
    """
    Handles GET and POST requests for creating a new member.
    This view manually handles form data and performs validation for the standalone Member model.
    """
    errors = {}
    member_data = {}

    if request.method == "POST":
        # Capture all form data from the POST request
        member_data['first_name'] = request.POST.get("first_name", "").strip()
        member_data['last_name'] = request.POST.get("last_name", "").strip()
        member_data['email'] = request.POST.get("email", "").strip()
        member_data['phone_number'] = request.POST.get("phone_number", "").strip()
        member_data['bio'] = request.POST.get("bio", "").strip()
        date_of_birth_str = request.POST.get("date_of_birth", "").strip()

        # Handle profile picture upload for creation
        profile_picture_file = request.FILES.get('profile_picture')

        # --- Manual Validation Checks ---
        if not member_data['first_name']:
            errors['first_name'] = 'First name is required.'
        if not member_data['last_name']:
            errors['last_name'] = 'Last name is required.'

        if not member_data['email']:
            errors['email'] = 'Email is required.'
        elif Member.objects.filter(email__iexact=member_data['email']).exists():
            errors['email'] = f'Member with email "{member_data["email"]}" already exists.'

        # Validate and parse date_of_birth
        member_data['date_of_birth'] = None
        if date_of_birth_str:
            try:
                member_data['date_of_birth'] = datetime.datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            except ValueError:
                errors['date_of_birth'] = 'Invalid date format. Please use YYYY-MM-DD.'
        # else:
            # If date of birth is required, uncomment the following line:
            # errors['date_of_birth'] = 'Date of birth is required.'


        if not errors:
            try:
                # Create the new Member object directly within a transaction for atomicity
                with transaction.atomic():
                    member = Member(
                        first_name=member_data['first_name'],
                        last_name=member_data['last_name'],
                        email=member_data['email'],
                        phone_number=member_data['phone_number'] if member_data['phone_number'] else None,
                        bio=member_data['bio'] if member_data['bio'] else None,
                        date_of_birth=member_data['date_of_birth'],
                        profile_picture=profile_picture_file, # Assign the uploaded file
                        created_at=timezone.now(), # Set creation time explicitly
                    )
                    member.full_clean()  # Perform full model validation (e.g., email format, max length)
                    member.save()

                messages.success(request, f'Member "{member.first_name} {member.last_name}" added successfully!')
                return redirect('member_index')
            except ValidationError as e:
                # Handle model validation errors (e.g., from full_clean())
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error creating member. Please check the form.')
            except IntegrityError as e:
                # Handle database integrity errors (e.g., unique constraints)
                messages.error(request, 'Error creating member. A database integrity error occurred (e.g., duplicate email).')
                errors['__all__'] = f"A database error occurred: {str(e)}"
            except Exception as e:
                # Catch any other unexpected errors during the process
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

    context = {
        'member_data': member_data, # Pass back data to repopulate form fields on error
        'errors': errors,
        'general_error': errors.get('__all__'),
    }
    return render(request, "pages/members/create.html", context)


# --- EDIT VIEW ---
@login_required
def edit_member(request, pk):
    """
    Handles GET and POST requests for editing an existing member.
    This is the "update" view for the standalone Member model.
    """
    # Fetch the Member object by its primary key (pk) or return a 404 error
    member = get_object_or_404(Member, pk=pk)

    errors = {}
    member_data = {}

    if request.method == "POST":
        # Capture updated form data from the POST request
        member_data['first_name'] = request.POST.get("first_name", "").strip()
        member_data['last_name'] = request.POST.get("last_name", "").strip()
        member_data['email'] = request.POST.get("email", "").strip()
        member_data['phone_number'] = request.POST.get("phone_number", "").strip()
        member_data['bio'] = request.POST.get("bio", "").strip()
        date_of_birth_str = request.POST.get("date_of_birth", "").strip()

        # Handle profile picture upload for editing
        profile_picture_file = request.FILES.get('profile_picture')
        # Check if the 'clear_profile_picture' checkbox was ticked
        clear_profile_picture = 'clear_profile_picture' in request.POST

        # --- Manual Validation Checks ---
        if not member_data['first_name']:
            errors['first_name'] = 'First name is required.'
        if not member_data['last_name']:
            errors['last_name'] = 'Last name is required.'

        if not member_data['email']:
            errors['email'] = 'Email is required.'
        # Check for email uniqueness, excluding the current member's own email
        elif Member.objects.filter(email__iexact=member_data['email']).exclude(pk=member.pk).exists():
            errors['email'] = f'Member with email "{member_data["email"]}" already exists.'

        # Validate and parse date_of_birth
        member_data['date_of_birth'] = None
        if date_of_birth_str:
            try:
                member_data['date_of_birth'] = datetime.datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            except ValueError:
                errors['date_of_birth'] = 'Invalid date format. Please use YYYY-MM-DD.'
        # else:
            # If date of birth is required, uncomment the following line:
            # errors['date_of_birth'] = 'Date of birth is required.'


        if not errors:
            try:
                # Update the Member object fields directly within a transaction
                with transaction.atomic():
                    member.first_name = member_data['first_name']
                    member.last_name = member_data['last_name']
                    member.email = member_data['email']
                    member.phone_number = member_data['phone_number'] if member_data['phone_number'] else None
                    member.bio = member_data['bio'] if member_data['bio'] else None
                    member.date_of_birth = member_data['date_of_birth'] # Assign parsed date

                    # Handle profile picture: new upload, clear, or keep existing
                    if profile_picture_file:
                        member.profile_picture = profile_picture_file
                    elif clear_profile_picture:
                        member.profile_picture = None # Set to None to clear the existing picture
                    # If neither, the existing member.profile_picture remains unchanged

                    member.updated_at = timezone.now() # Update the 'updated_at' timestamp
                    member.full_clean() # Perform full model validation
                    member.save()

                messages.success(request, f'Member "{member.first_name} {member.last_name}" updated successfully!')
                return redirect('member_index')
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    errors[field] = field_errors[0]
                messages.error(request, 'Error updating member. Please check the form.')
            except IntegrityError as e:
                messages.error(request, 'Error updating member. A database integrity error occurred (e.g., duplicate email).')
                errors['__all__'] = f"A database error occurred: {str(e)}"
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                errors['__all__'] = f'An unexpected error occurred: {str(e)}'

    else:
        # Initial GET request, populate form with existing data from the Member object
        member_data = {
            'first_name': member.first_name,
            'last_name': member.last_name,
            'email': member.email,
            'phone_number': member.phone_number,
            'bio': member.bio,
            'date_of_birth': member.date_of_birth.isoformat() if member.date_of_birth else '', # Format date for HTML input
        }

    context = {
        'member': member, # Pass the member object itself for display (e.g., current profile pic)
        'member_data': member_data, # Pass back data to repopulate form fields
        'errors': errors,
        'general_error': errors.get('__all__'),
    }
    return render(request, "pages/members/edit.html", context)


# --- DELETE VIEW ---
@login_required
@require_POST # Ensures this view only accepts POST requests for security
def delete_member(request, pk):
    """
    Handles POST requests to delete a member.
    """
    try:
        # Fetch the Member object by its primary key (pk) or return a 404 error
        member = get_object_or_404(Member, pk=pk)
        member_name = f"{member.first_name} {member.last_name}"
        member.delete() # Delete the member from the database
        messages.success(request, f'Member "{member_name}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting member: {str(e)}')
    return redirect('member_index') # Redirect back to the member list


# --- DETAIL VIEW ---
@login_required
def view_member(request, pk):
    """
    Renders the member detail page, displaying a single member's information
    from the standalone Member model.
    """
    # Fetch the Member object by its primary key (pk) or return a 404 error
    member = get_object_or_404(Member, pk=pk)

    context = {
        'member': member, # Pass the Member object directly to the template
    }
    return render(request, "pages/members/detail.html", context)
