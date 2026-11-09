from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db import models
from django.db.models import Q
from django.views.decorators.http import require_POST
import csv
from datetime import datetime, timedelta
from django.utils import timezone
from apps.incidents.models import violence_events

# ==========================================
# 🔥 تحديث دالة الحقول المشتقة: ربط الوصف بمخرجات الـ AI
# ==========================================
def _add_derived_fields(incident):
    # 1. تحويل نسبة اليقين القادمة من المودل إلى نسبة مئوية صحيحة
    try:
        incident.confidence_percent = round(float(incident.confidence) * 100)
    except (TypeError, ValueError):
        try:
            incident.confidence_percent = round(float(str(incident.confidence).replace('%', '')))
        except (TypeError, ValueError):
            incident.confidence_percent = 0

    # 2. جلب تصنيف الحركة الفعلي المستنتج من نموذج الـ AI (المخزن في حقل severity)
    action_type = (incident.severity or '').lower().strip()
    loc = incident.location if incident.location else "the monitored zone"
    cam = incident.camera_id if incident.camera_id else "System Camera"

    # 3. صياغة الوصف الذكي ديناميكياً بناءً على نوع الفئة ونسبة يقين النموذج
    if action_type == 'punching' or action_type == 'high':
        incident.auto_description = f"Physical confrontation (Punching/Fighting) captured via {cam} at {loc}. The  system is highly confident ({incident.confidence_percent}%) that an active physical altercation is taking place."
    
    elif action_type == 'kicking':
        incident.auto_description = f"Violent assault involving kicking detected at {loc}. Computer Vision analysis flags this as a critical safety breach with a certainty level of {incident.confidence_percent}%."
    
    elif action_type == 'pushing' or action_type == 'medium':
        incident.auto_description = f"Aggressive physical pushing or suspicious crowding behavior flagged by the system at {loc}. Confidence score: {incident.confidence_percent}%."
    
    elif action_type == 'slapping':
        incident.auto_description = f"Sudden physical aggression (Slapping action) flagged on {cam}. System detected abnormal kinetic movement with {incident.confidence_percent}% confidence."
    
    else:
        incident.auto_description = f"Anomalous behavioral pattern or low-level disturbance detected at {loc}. Model confidence: {incident.confidence_percent}%."

    return incident


# ==========================================
# UTILITY: تطبيق الفلاتر والفرز لصفحة الحوادث
# ==========================================
def _apply_incident_filters(request, incidents):
    search = request.GET.get('search', '').strip()
    severity = request.GET.get('severity', 'all')
    status = request.GET.get('status', 'all')
    sort_by = request.GET.get('sort_by', 'newest')
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    incident_day = request.GET.get('incident_day', 'all').strip().lower()

    if search:
        incidents = incidents.filter(
            Q(camera_id__icontains=search) |
            Q(location__icontains=search) |
            Q(status__icontains=search) |
            Q(severity__icontains=search)
        )

    if severity != 'all':
        incidents = incidents.filter(severity__iexact=severity)

    if status != 'all':
        incidents = incidents.filter(status__iexact=status)

    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            incidents = incidents.filter(timestamp__gte=start_date)
        except ValueError:
            pass

    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            incidents = incidents.filter(timestamp__lt=end_date)
        except ValueError:
            pass

    if sort_by == 'oldest':
        incidents = incidents.order_by('timestamp')
    elif sort_by == 'severity':
        incidents = incidents.order_by('severity')
    else:
        incidents = incidents.order_by('-timestamp')

    incidents = list(incidents)

    if incident_day != 'all':
        incidents = [
            incident for incident in incidents
            if incident.timestamp and incident.timestamp.strftime('%A').lower() == incident_day
        ]

    filters = {
        'search_query': search,
        'selected_severity': severity,
        'selected_status': status,
        'selected_sort': sort_by,
        'date_from': date_from,
        'date_to': date_to,
        'selected_day': incident_day,
    }

    return incidents, filters


# ==========================================
# 2. VIEW: استعراض جدول الحوادث بالكامل
# ==========================================
def index(request):
    if not request.session.get('user_id'):
        return redirect('core:login')

    if request.session.get('role') == 'viewer':
        return redirect('dashboard:index')

    incidents = violence_events.objects.all().order_by('-timestamp')
    incidents, filters = _apply_incident_filters(request, incidents)

    for incident in incidents:
        _add_derived_fields(incident)

    context = {
        'incidents': incidents,
        'incidents_count': len(incidents),
        **filters,
    }

    return render(request, 'incidents/incidents.html', context)


# ==========================================
# 3. VIEW: تصدير التقارير كملف CSV أوتوماتيكي
# ==========================================
def export_incidents_csv(request):
    if not request.session.get('user_id'):
        return redirect('core:login')

    if request.session.get('role') == 'viewer':
        return redirect('dashboard:index')

    incidents = violence_events.objects.all().order_by('-timestamp')
    incidents, _ = _apply_incident_filters(request, incidents)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="incidents_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Timestamp', 'Camera ID', 'Location', 'Severity', 'Confidence', 'Status', 'Description', 'Evidence'])

    for incident in incidents:
        incident = _add_derived_fields(incident)
        writer.writerow([
            incident.id,
            incident.timestamp,
            incident.camera_id,
            incident.location,
            incident.severity,
            f'{incident.confidence_percent}%',
            incident.status,
            incident.auto_description,
            incident.evidence,
        ])

    return response


# ==========================================
# 4. VIEW: تفاصيل الحادثة (تتحول تلقائياً لـ Under Review)
# ==========================================
def detail(request, incident_id):
    if not request.session.get('user_id'):
        return redirect('core:login')

    if request.session.get('role') == 'viewer':
        return redirect('dashboard:index')

    incident = get_object_or_404(violence_events, id=incident_id)
    
    current_status = (incident.status or '').strip().lower()
    if current_status == 'active' or current_status == '':
        incident.status = 'Under Review'
        incident.save()

    incident = _add_derived_fields(incident)

    return render(request, 'incidents/incident_detail.html', {
        'incident': incident
    })


# ==========================================
# 5. VIEW: إغلاق وحل الحادثة يدوياً بواسطة رجل الأمن
# ==========================================
@require_POST
def resolve_incident(request, incident_id):
    if not request.session.get('user_id'):
        return redirect('core:login')

    # Viewers have read-only access and cannot change an incident's status.
    if request.session.get('role') == 'viewer':
        return redirect('dashboard:index')

    incident = get_object_or_404(violence_events, id=incident_id)

    if (incident.status or '').strip().lower() == 'under review':
        incident.status = 'Resolved'
        incident.save()

    return redirect('incidents:detail', incident_id=incident.id)