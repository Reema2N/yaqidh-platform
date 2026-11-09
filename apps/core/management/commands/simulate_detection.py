"""
Pretend to be the detection pipeline, so the platform can be demoed without
cameras or the AI model.

The real pipeline (built by the AI team) inserts a row into `violence_events`
for every detection and keeps writing its latest processed frame to
`apps/static/live_frames/cam1.jpg`. This command does the same two things.

Usage:
    python manage.py simulate_detection              # new incident every 8 s, until Ctrl+C
    python manage.py simulate_detection --interval 3 --count 10
"""

import random
import shutil
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.incidents.models import violence_events
from apps.live_monitoring.models import cameras

DEMO_FRAME = Path(settings.BASE_DIR) / 'docs' / 'demo' / 'live_frame.jpg'
LIVE_FRAME = Path(settings.BASE_DIR) / 'apps' / 'static' / 'live_frames' / 'cam1.jpg'

# Weighted so most simulated detections are lower severity, like real footage.
SEVERITIES = ['High', 'Medium', 'Low']
SEVERITY_WEIGHTS = [2, 3, 5]


class Command(BaseCommand):
    help = 'Simulate the detection pipeline: insert live incidents and a camera frame (demo only).'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=float, default=8.0,
                            help='Seconds between simulated detections (default 8).')
        parser.add_argument('--count', type=int, default=0,
                            help='Stop after this many detections (default 0 = run until Ctrl+C).')
        parser.add_argument('--no-frame', action='store_true',
                            help='Do not write the demo camera frame.')

    def handle(self, *args, **options):
        if not options['no_frame'] and DEMO_FRAME.exists():
            LIVE_FRAME.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(DEMO_FRAME, LIVE_FRAME)
            self.stdout.write('Demo frame written to live_frames/cam1.jpg')

        camera_list = list(cameras.objects.filter(status__iexact='active')) or list(cameras.objects.all())
        if not camera_list:
            self.stdout.write(self.style.WARNING(
                'No cameras found. Run "python manage.py seed_demo" first for nicer data.'
            ))

        self.stdout.write(self.style.SUCCESS(
            'Simulating detections. Open the dashboard to watch alerts arrive. Press Ctrl+C to stop.'
        ))

        created = 0
        try:
            while True:
                camera = random.choice(camera_list) if camera_list else None
                severity = random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS)[0]

                event = violence_events.objects.create(
                    camera_id=camera.camera_id if camera else 'CAM01',
                    location=camera.location if camera else 'Demo Camera',
                    timestamp=timezone.now(),
                    severity=severity,
                    confidence=f'{random.uniform(0.6, 0.98):.2f}',
                    status='Active',
                )
                created += 1
                self.stdout.write(
                    f'[{timezone.localtime(event.timestamp):%H:%M:%S}] '
                    f'#{event.id} {severity} at {event.location}'
                )

                if options['count'] and created >= options['count']:
                    break
                time.sleep(options['interval'])
        except KeyboardInterrupt:
            pass

        self.stdout.write(self.style.SUCCESS(f'Done. {created} simulated incident(s) created.'))
