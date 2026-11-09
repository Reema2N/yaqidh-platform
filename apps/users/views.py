from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse
from apps.core.models import Users
import json
import re
import secrets
import string
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail

def generate_otp():
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def generate_temporary_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_user_data(full_name, email, phone, role, status):
    if not full_name or not email or not phone or not role or not status:
        return 'All fields are required'

    if len(full_name) < 3:
        return 'Full name must be at least 3 characters'

    if not re.match(r'^[A-Za-z\u0600-\u06FF\s]+$', full_name):
        return 'Full name must contain letters only'

    try:
        validate_email(email)
    except ValidationError:
        return 'Invalid email format'

    if not re.match(r'^05\d{8}$', phone):
        return 'Phone must be Saudi format like 05XXXXXXXX'

    if role not in ['admin', 'operator', 'viewer']:
        return 'Invalid role'

    if status not in ['active', 'inactive']:
        return 'Invalid status'

    return None


def index(request):
    if not request.session.get('user_id'):
        return redirect('core:login')

    if request.session.get('role') != 'admin':
        return redirect('dashboard:index')

    users = Users.objects.all()

    total_users = users.count()
    active_users = users.filter(status='active').count()
    admins = users.filter(role='admin').count()

    context = {
        'users': users,
        'total_users': total_users,
        'active_users': active_users,
        'admins': admins,
    }

    return render(request, 'users/users.html', context)


def add_user(request):

    if not request.session.get('user_id'):
        return redirect('core:login')

    if request.session.get('role') != 'admin':
        return redirect('dashboard:index')

    if request.method != 'POST':
        return redirect('users:index')

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)

            full_name = data.get('full_name', '').strip()
            email = data.get('email', '').strip()
            phone = data.get('phone', '').strip()
            role = data.get('role', '').strip().lower()
            status = data.get('status', '').strip().lower()

        else:
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            role = request.POST.get('role', '').strip().lower()
            status = request.POST.get('status', '').strip().lower()

        error = validate_user_data(full_name, email, phone, role, status)
        if error:
            return JsonResponse({'success': False, 'error': error})

        if Users.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email exists'})
        
        verification_code = generate_otp()
        temporary_password = generate_temporary_password()

        # If the email cannot be sent, the account is not created either.
        with transaction.atomic():
            user = Users.objects.create(
                full_name=full_name,
                email=email,
                password=make_password(temporary_password),
                phone=phone,
                role=role,
                status=status,
                must_change_password=True,
                phone_verified=False,
                verification_code=verification_code,
                created=timezone.now()
            )

            send_mail(
                subject='Yaqidh - Your account details',
                message=(
                    f'Hello {full_name},\n\n'
                    f'An account has been created for you on the Yaqidh platform.\n\n'
                    f'Email: {email}\n'
                    f'Temporary password: {temporary_password}\n'
                    f'Verification code: {verification_code}\n\n'
                    f'Sign in with the temporary password, enter the verification code, '
                    f'then choose a new password.'
                ),
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )

        return JsonResponse({
            'success': True,
            'user_id': user.user_id
        })

    except Exception as e:
        print("ADD USER ERROR:", e)
        return JsonResponse({'success': False, 'error': 'Failed to add user'})


def update_user(request, user_id):

    if not request.session.get('user_id'):
        return redirect('core:login')

    if request.session.get('role') != 'admin':
        return redirect('dashboard:index')

    if request.method != 'POST':
        return redirect('users:index')

    try:
        user = Users.objects.filter(user_id=user_id).first()

        if not user:
            return JsonResponse({'success': False, 'error': 'User not found'})

        if request.content_type == 'application/json':
            data = json.loads(request.body)

            full_name = data.get('full_name', '').strip()
            email = data.get('email', '').strip()
            phone = data.get('phone', '').strip()
            role = data.get('role', '').strip().lower()
            status = data.get('status', '').strip().lower()

        else:
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            role = request.POST.get('role', '').strip().lower()
            status = request.POST.get('status', '').strip().lower()

        error = validate_user_data(full_name, email, phone, role, status)
        if error:
            return JsonResponse({'success': False, 'error': error})

        if Users.objects.filter(email=email).exclude(user_id=user_id).exists():
            return JsonResponse({'success': False, 'error': 'Email exists'})

        user.full_name = full_name
        user.email = email
        user.phone = phone
        user.role = role
        user.status = status
        user.save(update_fields=['full_name', 'email', 'phone', 'role', 'status'])

        return JsonResponse({
            'success': True,
            'user_id': user.user_id
        })

    except Exception as e:
        print("UPDATE USER ERROR:", e)
        return JsonResponse({'success': False, 'error': 'Failed to update user'})
    
def delete_user(request):

    if not request.session.get('user_id'):
        return redirect('core:login')

    if request.session.get('role') != 'admin':
        return redirect('dashboard:index')

    if request.method != 'POST':
        return JsonResponse({'success': False})

    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')

        user = Users.objects.filter(user_id=user_id).first()

        if not user:
            return JsonResponse({'success': False, 'error': 'User not found'})

        if user.user_id == request.session.get('user_id'):
            return JsonResponse({'success': False, 'error': 'You cannot delete your own account'})

        user.delete()

        return JsonResponse({'success': True})

    except Exception as e:
        print("DELETE USER ERROR:", e)
        return JsonResponse({'success': False})