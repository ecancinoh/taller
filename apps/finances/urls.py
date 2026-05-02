from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('', views.FinancialDashboardView.as_view(), name='dashboard'),
    path('gastos/nuevo/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('gastos/<int:pk>/editar/', views.ExpenseUpdateView.as_view(), name='expense_update'),
    path('gastos/<int:pk>/eliminar/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
]
