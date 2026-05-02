from django.urls import path
from . import views

app_name = 'shared_views'

urlpatterns = [
    path('orden/<uuid:token>/', views.PublicOrderView.as_view(), name='public_order'),
]
