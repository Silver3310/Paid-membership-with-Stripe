from django.db import models


class FitnessPlan(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField()
    premium = models.BooleanField(default=True)

