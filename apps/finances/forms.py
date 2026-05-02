from django import forms
from .models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'description', 'amount', 'date']
        widgets = {
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Herramientas, Arriendo, Servicios'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Detalle del gasto'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'category': 'Categoría',
            'description': 'Descripción',
            'amount': 'Monto ($)',
            'date': 'Fecha',
        }
