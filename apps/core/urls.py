from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('buscar/', views.GlobalSearchView.as_view(), name='search'),
]
