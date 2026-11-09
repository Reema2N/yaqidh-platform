from django.shortcuts import render, redirect

from apps.incidents.models import violence_events
from .models import cameras


def index(request):

    if not request.session.get('user_id'):
        return redirect('core:login')

    # Prefer an active camera; fall back to the first registered one.
    camera = cameras.objects.filter(status__iexact='active').first() or cameras.objects.first()

    context = {
        'camera': camera,
        'active_cameras_count': cameras.objects.filter(status__iexact='active').count(),
        'active_alerts_count': violence_events.objects.filter(status__iexact='Active').count(),
    }

    return render(request, 'live_monitoring/live_monitoring.html', context)
