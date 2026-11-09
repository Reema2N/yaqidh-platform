from django.shortcuts import render, redirect
from django.db.models import Count
from django.db.models.functions import ExtractHour, ExtractWeekDay
from apps.incidents.models import violence_events
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta
import json

def reports_view(request):
    if not request.session.get('user_id'):
        return redirect('core:login')

    # Reports are admin-only (the sidebar already hides the link for other roles).
    if request.session.get('role') != 'admin':
        return redirect('dashboard:index')

    incidents = violence_events.objects.all()

    total_incidents = incidents.count()
    high_severity = incidents.filter(severity__iexact='high').count()

    resolved_count = incidents.filter(status__iexact='resolved').count()
    # Share of incidents that operators have closed (not a model-accuracy metric).
    resolution_rate = round((resolved_count / total_incidents) * 100, 1) if total_incidents else 0

    # Daily incidents
    daily_data = incidents.annotate(day=ExtractWeekDay('timestamp')) \
        .values('day') \
        .annotate(count=Count('id')) \
        .order_by('day')

    daily_incidents = [0] * 7
    for item in daily_data:
        index = item['day'] - 1
        if 0 <= index < 7:
            daily_incidents[index] = item['count']

    # Severity distribution
    severity_distribution = {
        'high': incidents.filter(severity__iexact='high').count(),
        'medium': incidents.filter(severity__iexact='medium').count(),
        'low': incidents.filter(severity__iexact='low').count(),
    }

    # Hourly distribution
    hourly_data = incidents.annotate(hour=ExtractHour('timestamp')) \
        .values('hour') \
        .annotate(count=Count('id')) \
        .order_by('hour')

    hourly_distribution = [0] * 24
    for item in hourly_data:
        if item['hour'] is not None:
            hourly_distribution[item['hour']] = item['count']

    # Camera incidents
    camera_data = incidents.values('camera_id') \
        .annotate(count=Count('id')) \
        .order_by('-count')[:6]

    camera_labels = []
    camera_counts = []

    for cam in camera_data:
        camera_labels.append(cam['camera_id'])
        camera_counts.append(cam['count'])

    top_camera = camera_labels[0] if camera_labels else "N/A"

    avg_response = incidents.aggregate(
        Avg('response_time'))['response_time__avg'] 
    avg_response_time = round(avg_response, 1) if avg_response else 0


    peak_hour_data = incidents.annotate(hour=ExtractHour('timestamp')).values('hour').annotate(count=Count('id')).order_by('-count').first()
    if peak_hour_data and peak_hour_data['hour'] is not None:
        start_hour = peak_hour_data['hour']
        end_hour = (start_hour + 1) % 24
        peak_hours = f"{start_hour:02d}:00 - {end_hour:02d}:00"
    else:
        peak_hours = "N/A"

    # Week-over-week change in incident count (last 7 days vs the 7 days before).
    now = timezone.now()
    this_week = incidents.filter(timestamp__gte=now - timedelta(days=7)).count()
    last_week = incidents.filter(
        timestamp__gte=now - timedelta(days=14),
        timestamp__lt=now - timedelta(days=7),
    ).count()

    if last_week:
        weekly_change_value = round(((this_week - last_week) / last_week) * 100, 1)
        weekly_change = f"{weekly_change_value:+}%"
    else:
        weekly_change_value = None
        weekly_change = "N/A"

    context = {
        'total_incidents': total_incidents,
        'high_severity': high_severity,
        'avg_response_time': f'{avg_response_time}m',
        'resolution_rate': resolution_rate,

        'daily_incidents': json.dumps(daily_incidents),
        'severity_distribution': json.dumps(list(severity_distribution.values())),
        'hourly_distribution': json.dumps(hourly_distribution),

        'camera_labels': json.dumps(camera_labels),
        'camera_counts': json.dumps(camera_counts),

        'peak_hours': peak_hours,
        'top_camera': top_camera,
        'weekly_change': weekly_change,
        'weekly_change_value': weekly_change_value,
    }
    return render(request, 'reports/reports.html', context)