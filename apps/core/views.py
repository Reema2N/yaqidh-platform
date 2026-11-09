from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Users

GENERIC_LOGIN_ERROR = 'Invalid email or password'


def _is_hashed(stored_password):
    try:
        identify_hasher(stored_password)
        return True
    except (ValueError, TypeError):
        return False


def _verify_password(user, raw_password):
    """Check a password and upgrade any legacy plain-text value to a hash."""
    if not user.password or not raw_password:
        return False

    if _is_hashed(user.password):
        return check_password(raw_password, user.password)

    # Legacy rows created before hashing was added: compare once, then hash.
    if user.password == raw_password:
        user.password = make_password(raw_password)
        user.save(update_fields=['password'])
        return True

    return False


def _start_session(request, user):
    # New session key on login prevents session fixation.
    request.session.cycle_key()
    request.session['user_id'] = user.user_id
    request.session['full_name'] = user.full_name
    request.session['email'] = user.email
    request.session['role'] = user.role
    request.session['status'] = user.status


def _otp_expired(user):
    if not user.created or settings.OTP_EXPIRY_MINUTES <= 0:
        return False
    expiry = user.created + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    return timezone.now() > expiry


def login_view(request):

    if request.session.get('user_id'):
        return redirect('dashboard:index')

    if request.method == 'POST':
        email = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        user = Users.objects.filter(email=email).first()

        # Same message for unknown email and wrong password (no account enumeration).
        if not user or not _verify_password(user, password):
            return render(request, 'core/login.html', {
                'error': GENERIC_LOGIN_ERROR
            })

        if not user.status or user.status.lower() != 'active':
            return render(request, 'core/login.html', {
                'error': 'This account is inactive'
            })

        if user.must_change_password:
            request.session.cycle_key()
            request.session['temp_user_id'] = user.user_id
            request.session['otp_attempts'] = 0

            if not user.phone_verified:
                return redirect('core:verify_otp')

            return redirect('core:change_password')

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        _start_session(request, user)

        return redirect('dashboard:index')

    return render(request, 'core/login.html')


def verify_otp_view(request):

    temp_user_id = request.session.get('temp_user_id')

    if not temp_user_id:
        return redirect('core:login')

    user = Users.objects.filter(user_id=temp_user_id).first()

    if not user:
        request.session.flush()
        return redirect('core:login')

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()

        if not otp_code:
            return render(request, 'core/verify_otp.html', {
                'error': 'Please enter verification code'
            })

        if not user.verification_code or _otp_expired(user):
            return render(request, 'core/verify_otp.html', {
                'error': 'This verification code has expired. Please ask an administrator to re-create your account.'
            })

        if otp_code != user.verification_code:
            attempts = request.session.get('otp_attempts', 0) + 1
            request.session['otp_attempts'] = attempts

            if attempts >= settings.OTP_MAX_ATTEMPTS:
                request.session.flush()
                return render(request, 'core/login.html', {
                    'error': 'Too many incorrect codes. Please sign in again.'
                })

            return render(request, 'core/verify_otp.html', {
                'error': 'Invalid verification code'
            })

        user.phone_verified = True
        user.verification_code = None
        user.save(update_fields=['phone_verified', 'verification_code'])
        request.session.pop('otp_attempts', None)

        return redirect('core:change_password')

    return render(request, 'core/verify_otp.html')


def change_password_view(request):

    temp_user_id = request.session.get('temp_user_id')

    if not temp_user_id:
        return redirect('core:login')

    user = Users.objects.filter(user_id=temp_user_id).first()

    if not user:
        request.session.flush()
        return redirect('core:login')

    # The OTP step cannot be skipped by opening this URL directly.
    if not user.phone_verified:
        return redirect('core:verify_otp')

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not new_password or not confirm_password:
            return render(request, 'core/change_password.html', {
                'error': 'Please fill all fields'
            })

        if len(new_password) < 8:
            return render(request, 'core/change_password.html', {
                'error': 'Password must be at least 8 characters'
            })

        if new_password != confirm_password:
            return render(request, 'core/change_password.html', {
                'error': 'Passwords do not match'
            })

        user.password = make_password(new_password)
        user.must_change_password = False
        user.last_login = timezone.now()
        user.save(update_fields=[
            'password',
            'must_change_password',
            'last_login'
        ])

        request.session.pop('temp_user_id', None)
        _start_session(request, user)

        return redirect('dashboard:index')

    return render(request, 'core/change_password.html')


def logout_view(request):
    request.session.flush()
    return redirect('core:login')
