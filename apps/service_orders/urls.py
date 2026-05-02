from django.urls import path
from . import views

app_name = 'service_orders'

urlpatterns = [
    path('', views.ServiceOrderListView.as_view(), name='list'),
    path('nueva/', views.ServiceOrderCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ServiceOrderDetailView.as_view(), name='detail'),
    path('<int:pk>/compartir/', views.ServiceOrderShareLinkView.as_view(), name='share_link'),
    path('<int:pk>/subir-foto/', views.ServiceOrderPhotoUploadView.as_view(), name='upload_photo'),
    path('<int:pk>/editar/', views.ServiceOrderUpdateView.as_view(), name='update'),
    # Repuestos
    path('<int:pk>/repuestos/agregar/', views.ServiceOrderPartCreateView.as_view(), name='part_create'),
    path('repuestos/<int:pk>/editar/', views.ServiceOrderPartUpdateView.as_view(), name='part_update'),
    path('repuestos/<int:pk>/eliminar/', views.ServiceOrderPartDeleteView.as_view(), name='part_delete'),
    # Mano de obra
    path('<int:pk>/mano-obra/agregar/', views.ServiceOrderLaborCreateView.as_view(), name='labor_create'),
    path('mano-obra/<int:pk>/editar/', views.ServiceOrderLaborUpdateView.as_view(), name='labor_update'),
    path('mano-obra/<int:pk>/eliminar/', views.ServiceOrderLaborDeleteView.as_view(), name='labor_delete'),
]
