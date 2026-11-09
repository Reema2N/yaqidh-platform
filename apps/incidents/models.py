from django.db import models

class violence_events(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)
    camera_id = models.CharField(db_column='Camera_ID', max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(db_column='Timestamp', blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    severity = models.CharField(db_column='Severity', max_length=20, blank=True, null=True)
    confidence = models.CharField(db_column='Confidence', max_length=20, blank=True, null=True)
    # إضافة القيمة الافتراضية 'Active' للحقل لضمان سلامة البيانات الأمنية عند تسجيل أي رصد جديد
    status = models.CharField(max_length=30, blank=True, null=True, default='Active')
    evidence = models.CharField(max_length=200, blank=True, null=True)
    response_time = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True  # تحويلها إلى True لتمكين دجانغو من إدارة وحفظ حالات التعديل بنجاح
        db_table = 'violence_events'