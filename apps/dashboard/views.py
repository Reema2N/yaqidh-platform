from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta, datetime, time

from apps.incidents.models import violence_events
from apps.live_monitoring.models import cameras


def calculate_system_uptime(camera_queryset):
    total_cameras = camera_queryset.count()

    if total_cameras == 0:
        return "100"

    active_cameras = camera_queryset.filter(status__iexact='active').count()
    uptime_percentage = (active_cameras / total_cameras) * 100

    if uptime_percentage == 100:
        return "99.9"

    return f"{round(uptime_percentage, 1)}"


def get_today_range():
    local_now = timezone.localtime(timezone.now())

    today_start = datetime.combine(local_now.date(), time.min)
    today_end = datetime.combine(local_now.date(), time.max)

    if timezone.is_naive(today_start):
        today_start = timezone.make_aware(today_start)

    if timezone.is_naive(today_end):
        today_end = timezone.make_aware(today_end)

    return today_start, today_end


def get_time_ago(alert_time):
    if timezone.is_naive(alert_time):
        alert_time = timezone.make_aware(alert_time)

    time_diff = timezone.now() - alert_time
    minutes_ago = int(time_diff.total_seconds() // 60)

    if minutes_ago < 0:
        minutes_ago = 0

    if minutes_ago < 1:
        return "Just now"
    elif minutes_ago < 60:
        return f"{minutes_ago}m ago"
    elif minutes_ago < 1440:
        return f"{minutes_ago // 60}h ago"
    else:
        return f"{minutes_ago // 1440} days ago"


def get_confidence_value(confidence):
    try:
        raw_conf = float(confidence)
        return int(raw_conf * 100) if raw_conf <= 1.0 else int(raw_conf)
    except:
        return 0


def calculate_resolution_rate(event_queryset):
    total = event_queryset.count()
    if total == 0:
        return 0
    resolved = event_queryset.filter(status__iexact='Resolved').count()
    return round((resolved / total) * 100, 1)


def get_system_status(camera_queryset):
    total_cameras = camera_queryset.count()
    active_cameras = camera_queryset.filter(status__iexact='active').count()

    if total_cameras == 0:
        return "No Cameras", active_cameras, total_cameras
    elif active_cameras == 0:
        return "Offline", active_cameras, total_cameras
    elif active_cameras < total_cameras:
        return "Degraded", active_cameras, total_cameras
    else:
        return "Operational", active_cameras, total_cameras


def build_recent_alerts(active_events_only):
    recent_alerts = []

    for alert in active_events_only[:5]:
        severity_val = alert.severity.lower() if alert.severity else 'low'
        actual_name = alert.location if alert.location else (
            alert.camera_id if alert.camera_id else "Unknown Area"
        )

        recent_alerts.append({
            "camera_name": actual_name,
            "severity": severity_val,
            "severity_display": severity_val.capitalize(),
            "confidence": get_confidence_value(alert.confidence),
            "time": get_time_ago(alert.timestamp),
        })

    return recent_alerts


def index(request):
    if not request.session.get('user_id'):
        return redirect('core:login')

    all_events = violence_events.objects.all().order_by('-timestamp')
    all_cameras = cameras.objects.all()
    active_camera = cameras.objects.filter(status__iexact='active').first()

    today_start, today_end = get_today_range()
    today_events = all_events.filter(timestamp__range=(today_start, today_end))

    high_count = all_events.filter(severity__iexact='High').count()
    medium_count = all_events.filter(severity__iexact='Medium').count()
    low_count = all_events.filter(severity__iexact='Low').count()
    resolved_count = all_events.filter(status__iexact='Resolved').count()

    active_events_only = all_events.filter(status__iexact='Active')

    system_status, active_cameras, total_cameras = get_system_status(all_cameras)
    uptime = calculate_system_uptime(all_cameras)

    context = {
        'active_cameras': active_cameras,
        'active_camera': active_camera,
        'total_incidents': all_events.count(),
        'incidents_today': today_events.count(),
        'high_count': high_count,
        'medium_count': medium_count,
        'low_count': low_count,
        'resolved_count': resolved_count,
        'recent_incidents': build_recent_alerts(active_events_only),
        'cameras': all_cameras,
        'system_status': system_status,
        'uptime': uptime,
        'resolution_rate': calculate_resolution_rate(all_events),
        'active_alerts_count': active_events_only.count(),
    }

    return render(request, 'dashboard/dashboard.html', context)


def dashboard_live_api(request):
    if not request.session.get('user_id'):
        return JsonResponse({'error': 'Authentication required'}, status=401)

    events = violence_events.objects.all().order_by('-timestamp')
    camera_queryset = cameras.objects.all()

    today_start, today_end = get_today_range()
    incidents_today_count = events.filter(timestamp__range=(today_start, today_end)).count()

    high_count = events.filter(severity__iexact='High').count()
    medium_count = events.filter(severity__iexact='Medium').count()
    low_count = events.filter(severity__iexact='Low').count()
    resolved_count = events.filter(status__iexact='Resolved').count()

    active_events_only = events.filter(status__iexact='Active')

    system_status, active_cameras, total_cameras = get_system_status(camera_queryset)
    uptime = calculate_system_uptime(camera_queryset)

    half_minute_ago = timezone.now() - timedelta(seconds=30)
    recent_active_events = active_events_only.filter(
        timestamp__gte=half_minute_ago
    ).order_by('timestamp')

    new_alerts_list = []

    for ev in recent_active_events:
        cam_location = ev.location if ev.location else (
            ev.camera_id if ev.camera_id else "Unknown Location"
        )

        new_alerts_list.append({
            "id": ev.id,
            "title": f"Violence Detected - {cam_location}",
            "level": ev.severity.lower() if ev.severity else 'low',
        })

    data = {
        "active_cameras": active_cameras,
        "incidents_today": incidents_today_count,
        "resolution_rate": calculate_resolution_rate(events),
        "uptime": uptime,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "resolved_count": resolved_count,
        "active_alerts_count": active_events_only.count(),
        "new_alerts": new_alerts_list,
        "alerts_list": build_recent_alerts(active_events_only),
        "system_status": system_status,
        "cameras_data": [
            {
                "camera_id": c.camera_id,
                "status": c.status.lower() if c.status else "offline",
                "location": c.location,
                "model": c.model,
            }
            for c in camera_queryset
        ],
    }

    return JsonResponse(data)