from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.CustomerListView.as_view(), name='list'),
    path('importar/', views.CustomerImportView.as_view(), name='import_contacts'),
    path('nuevo/', views.CustomerCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.CustomerUpdateView.as_view(), name='update'),
]
