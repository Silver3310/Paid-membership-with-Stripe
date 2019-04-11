from django.urls import path, include
from .views import *

urlpatterns = [
    path(
        '',
        home,
        name='home'
    ),
    path(
        'plans/<int:pk>',
        plan,
        name='plan'
    ),
    path(
        'auth/',
        include('django.contrib.auth.urls')
    ),
    path(
        'auth/signup',
        SignUp.as_view(),
        name='signup'
    ),
    path(
        'join',
        join,
        name='join'
    ),
    path(
        'checkout',
        CheckoutView.as_view(),
        name='checkout'
    ),
    path(
        'auth/settings',
        SettingsView.as_view(),
        name='settings'
    ),
    path(
        'update-accounts',
        update_accounts,
        name='update_accounts'
    )
]
