from django.db import models


class Users(models.Model):
    user_id = models.AutoField(primary_key=True)
    email = models.CharField(max_length=100, unique=True, blank=True, null=True)
    password = models.CharField(max_length=100, blank=True, null=True)

    full_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField(blank=True, null=True)
    must_change_password = models.BooleanField(default=True)
    phone_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    

    def __str__(self):
        return self.full_name if self.full_name else self.email

    class Meta:
        managed = False
        db_table = 'users'