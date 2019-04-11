from django.db import models
from django.contrib.auth.models import User


class FitnessPlan(models.Model):
    """
    A custom model for fitness plans

    Attributes:
        title (str): a title of a plan
        text (str): text of a plan
        premium (bool): if a plan is premium or not
    """
    title = models.CharField(max_length=255)
    text = models.TextField()
    premium = models.BooleanField(default=True)


class Customer(models.Model):
    """
    A custom model for customers

    Attributes:
        user (user): a user a customer model belongs to
        stripe_id (str): the customer's stripe id
        stripe_sub_id (str): the stripe id of a customer's subscription
        cancel_at_period_end (bool): if a customer has canceled the subscription
        membership (bool): if a customer is a member for premium content
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    stripe_id = models.CharField(max_length=255)
    stripe_sub_id = models.CharField(max_length=255)
    cancel_at_period_end = models.BooleanField(default=False)
    membership = models.BooleanField(default=False)

