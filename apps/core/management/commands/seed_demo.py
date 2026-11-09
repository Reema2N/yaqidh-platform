import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.incidents.models import violence_events
from apps.live_monitoring.models import cameras

DEMO_CAMERAS = [
    ('CAM01', 'Entrance Gate', 'Hikvision DS-2CD2143', 'active'),
    ('CAM02', 'Parking Area', 'Dahua IPC-HFW2431', 'active'),
    ('CAM03', 'Main Lobby', 'Hikvision DS-2CD2143', 'active'),
    ('CAM04', 'Corridor B', 'Axis M3106', 'maintenance'),
]


class Command(BaseCommand):
    help = 'Fill an empty database with demo cameras and incidents (for local testing only).'

    def add_arguments(self, parser):
        parser.add_argument('--incidents', type=int, default=40)

    def handle(self, *args, **options):
        for camera_id, location, model, status in DEMO_CAMERAS:
            cameras.objects.update_or_create(
                camera_id=camera_id,
                defaults={'location': location, 'model': model, 'status': status},
            )

        now = timezone.now()
        rng = random.Random(42)
        severities = ['High', 'Medium', 'Low']
        statuses = ['Active', 'Under Review', 'Resolved', 'Resolved']

        for _ in range(options['incidents']):
            camera_id, location, _, _ = rng.choice(DEMO_CAMERAS)
            violence_events.objects.create(
                camera_id=camera_id,
                location=location,
                timestamp=now - timedelta(minutes=rng.randint(1, 14 * 24 * 60)),
                severity=rng.choice(severities),
                confidence=f'{rng.uniform(0.6, 0.98):.2f}',
                status=rng.choice(statuses),
                response_time=rng.randint(1, 10),
            )

        self.stdout.write(self.style.SUCCESS(
            f'Created {len(DEMO_CAMERAS)} cameras and {options["incidents"]} demo incidents.'
        ))
