from django.urls import path
from . import views

app_name = 'shared_views'

urlpatterns = [
    path('orden/<uuid:token>/', views.PublicOrderView.as_view(), name='public_order'),
    path('orden/<uuid:token>/foto/<int:photo_id>/', views.PublicOrderPhotoView.as_view(), name='public_order_photo'),
]
