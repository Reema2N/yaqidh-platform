from django.db import models

STATUS_CHOICES = [
    ('active', 'Active'),
    ('offline', 'Offline'),
    ('maintenance', 'Maintenance')
]

class cameras(models.Model):
    camera_id = models.CharField(primary_key=True, max_length=20)
    model = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    stream_url = models.CharField(max_length=200, blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)

    # الجديد
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline'
    )

    class Meta:
        managed = True
        db_table = 'cameras'

    def __str__(self):
        return f"{self.camera_id} - {self.location}"