from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    path('', views.VehicleListView.as_view(), name='list'),
    path('nuevo/', views.VehicleCreateView.as_view(), name='create'),
    path('<int:pk>/', views.VehicleDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.VehicleUpdateView.as_view(), name='update'),
]
