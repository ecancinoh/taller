from django import forms
from .models import Vehicle
from apps.customers.models import Customer


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['customer', 'brand', 'model', 'year', 'license_plate', 'vin', 'color', 'engine', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Toyota, Chevrolet...'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Corolla, Spark...'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2020', 'min': 1900, 'max': 2100}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCD12'}),
            'vin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VIN / Número de serie'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Blanco, Negro...'}),
            'engine': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1.6L, 2.0T...'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, customer_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if customer_id:
            self.fields['customer'].initial = customer_id
        self.fields['customer'].queryset = Customer.objects.order_by('last_name', 'first_name')
