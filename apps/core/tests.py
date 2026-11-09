from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Users
from apps.incidents.models import violence_events


def make_user(email='admin@example.com', password='StrongPass123', role='admin', **extra):
    defaults = dict(
        full_name='Test User',
        email=email,
        password=make_password(password),
        phone='0500000000',
        role=role,
        status='active',
        must_change_password=False,
        phone_verified=True,
        created=timezone.now(),
    )
    defaults.update(extra)
    return Users.objects.create(**defaults)


def login(client, email, password):
    return client.post(reverse('core:login'), {'username': email, 'password': password})


class LoginTests(TestCase):

    def test_valid_login_opens_dashboard(self):
        make_user()
        response = login(self.client, 'admin@example.com', 'StrongPass123')
        self.assertRedirects(response, reverse('dashboard:index'))
        self.assertIn('user_id', self.client.session)

    def test_wrong_password_and_unknown_email_give_same_message(self):
        make_user()
        wrong = login(self.client, 'admin@example.com', 'nope')
        unknown = login(self.client, 'ghost@example.com', 'nope')
        self.assertContains(wrong, 'Invalid email or password')
        self.assertContains(unknown, 'Invalid email or password')

    def test_legacy_plain_text_password_is_upgraded_to_hash(self):
        user = make_user(password='x')
        Users.objects.filter(pk=user.pk).update(password='LegacyPass1')
        response = login(self.client, 'admin@example.com', 'LegacyPass1')
        self.assertRedirects(response, reverse('dashboard:index'))
        user.refresh_from_db()
        self.assertNotEqual(user.password, 'LegacyPass1')
        self.assertTrue(check_password('LegacyPass1', user.password))

    def test_inactive_account_is_blocked(self):
        make_user(status='inactive')
        response = login(self.client, 'admin@example.com', 'StrongPass123')
        self.assertContains(response, 'This account is inactive')


class FirstLoginFlowTests(TestCase):

    def setUp(self):
        self.user = make_user(
            email='new@example.com',
            password='TempPass123',
            must_change_password=True,
            phone_verified=False,
            verification_code='123456',
        )

    def test_full_first_login_flow(self):
        response = login(self.client, 'new@example.com', 'TempPass123')
        self.assertRedirects(response, reverse('core:verify_otp'))

        response = self.client.post(reverse('core:verify_otp'), {'otp_code': '123456'})
        self.assertRedirects(response, reverse('core:change_password'))

        response = self.client.post(reverse('core:change_password'), {
            'new_password': 'BrandNewPass9',
            'confirm_password': 'BrandNewPass9',
        })
        self.assertRedirects(response, reverse('dashboard:index'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)

    def test_cannot_skip_otp_by_opening_change_password(self):
        login(self.client, 'new@example.com', 'TempPass123')
        response = self.client.post(reverse('core:change_password'), {
            'new_password': 'BrandNewPass9',
            'confirm_password': 'BrandNewPass9',
        })
        self.assertRedirects(response, reverse('core:verify_otp'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.must_change_password)

    @override_settings(OTP_EXPIRY_MINUTES=60)
    def test_expired_otp_is_rejected(self):
        Users.objects.filter(pk=self.user.pk).update(created=timezone.now() - timedelta(hours=2))
        login(self.client, 'new@example.com', 'TempPass123')
        response = self.client.post(reverse('core:verify_otp'), {'otp_code': '123456'})
        self.assertContains(response, 'expired')
        self.user.refresh_from_db()
        self.assertFalse(self.user.phone_verified)

    @override_settings(OTP_MAX_ATTEMPTS=3)
    def test_too_many_wrong_codes_ends_the_session(self):
        login(self.client, 'new@example.com', 'TempPass123')
        for _ in range(3):
            response = self.client.post(reverse('core:verify_otp'), {'otp_code': '000000'})
        self.assertContains(response, 'Too many incorrect codes')
        self.assertNotIn('temp_user_id', self.client.session)


class AccessControlTests(TestCase):

    def setUp(self):
        self.incident = violence_events.objects.create(
            camera_id='CAM01', timestamp=timezone.now(), location='Gate',
            severity='High', confidence='0.9', status='Under Review',
        )

    def test_live_api_requires_login(self):
        response = self.client.get(reverse('dashboard:dashboard_live_api'))
        self.assertEqual(response.status_code, 401)

    def test_live_api_works_when_logged_in(self):
        make_user()
        login(self.client, 'admin@example.com', 'StrongPass123')
        response = self.client.get(reverse('dashboard:dashboard_live_api'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('resolution_rate', response.json())

    def test_viewer_cannot_resolve_incident(self):
        make_user(email='viewer@example.com', role='viewer')
        login(self.client, 'viewer@example.com', 'StrongPass123')
        self.client.post(reverse('incidents:resolve_incident', args=[self.incident.id]))
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'Under Review')

    def test_operator_can_resolve_incident(self):
        make_user(email='op@example.com', role='operator')
        login(self.client, 'op@example.com', 'StrongPass123')
        self.client.post(reverse('incidents:resolve_incident', args=[self.incident.id]))
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'Resolved')

    def test_opening_active_incident_moves_it_to_under_review(self):
        self.incident.status = 'Active'
        self.incident.save()
        make_user(email='op@example.com', role='operator')
        login(self.client, 'op@example.com', 'StrongPass123')
        self.client.get(reverse('incidents:detail', args=[self.incident.id]))
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'Under Review')

    def test_operator_cannot_open_reports(self):
        make_user(email='op@example.com', role='operator')
        login(self.client, 'op@example.com', 'StrongPass123')
        response = self.client.get(reverse('reports:index'))
        self.assertRedirects(response, reverse('dashboard:index'))

    def test_viewer_cannot_open_users_page(self):
        make_user(email='viewer@example.com', role='viewer')
        login(self.client, 'viewer@example.com', 'StrongPass123')
        response = self.client.get(reverse('users:index'))
        self.assertRedirects(response, reverse('dashboard:index'))


class UserManagementTests(TestCase):

    def setUp(self):
        self.admin = make_user()
        login(self.client, 'admin@example.com', 'StrongPass123')

    def test_new_user_gets_random_password_and_email(self):
        response = self.client.post(
            reverse('users:add_user'),
            data='{"full_name": "Sara Ali", "email": "sara@example.com", "phone": "0551234567", '
                 '"role": "operator", "status": "active"}',
            content_type='application/json',
        )
        self.assertTrue(response.json()['success'])
        user = Users.objects.get(email='sara@example.com')
        self.assertFalse(check_password('123456', user.password))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.verification_code, mail.outbox[0].body)

    def test_admin_cannot_delete_own_account(self):
        response = self.client.post(
            reverse('users:delete_user'),
            data=f'{{"user_id": {self.admin.user_id}}}',
            content_type='application/json',
        )
        self.assertFalse(response.json()['success'])
        self.assertTrue(Users.objects.filter(pk=self.admin.pk).exists())


class PageSmokeTests(TestCase):
    """Every main page renders for an admin."""

    def test_pages_render(self):
        make_user()
        login(self.client, 'admin@example.com', 'StrongPass123')
        for name in ['dashboard:index', 'incidents:index', 'live_monitoring:index',
                     'reports:index', 'users:index', 'incidents:export_csv']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)


class ManagementCommandTests(TestCase):

    def test_seed_and_simulate_detection(self):
        from django.core.management import call_command
        from io import StringIO

        call_command('seed_demo', incidents=5, stdout=StringIO())
        before = violence_events.objects.filter(status='Active').count()
        call_command('simulate_detection', count=2, interval=0, no_frame=True, stdout=StringIO())
        self.assertEqual(violence_events.objects.filter(status='Active').count(), before + 2)

    def test_create_admin(self):
        from django.core.management import call_command
        from io import StringIO

        call_command('create_admin', email='boss@example.com', password='LongEnough1', stdout=StringIO())
        user = Users.objects.get(email='boss@example.com')
        self.assertEqual(user.role, 'admin')
        self.assertTrue(check_password('LongEnough1', user.password))
