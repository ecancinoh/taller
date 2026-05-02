from django.urls import path
from . import views

app_name = 'service_orders'

urlpatterns = [
    path('', views.ServiceOrderListView.as_view(), name='list'),
    path('nueva/', views.ServiceOrderCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ServiceOrderDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.ServiceOrderUpdateView.as_view(), name='update'),
]
