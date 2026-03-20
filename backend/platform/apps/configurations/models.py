from django.db import models


class SystemConfig(models.Model):
    config_key = models.CharField(max_length=128, unique=True)
    config_value = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
