from django.urls import path

from .views import GenerateDiagnosticView

app_name = 'diagnostics'

urlpatterns = [
    path('orden/<int:order_id>/generar/', GenerateDiagnosticView.as_view(), name='generate'),
]
