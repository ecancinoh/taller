from django import forms
from .models import ServiceOrder, ServiceOrderPart, ServiceOrderLabor


class ServiceOrderForm(forms.ModelForm):
    class Meta:
        model = ServiceOrder
        fields = [
            'vehicle', 'mechanic', 'status', 'service_date', 'mileage',
            'customer_complaint', 'mechanic_observations', 'diagnosis',
            'work_done', 'recommendations', 'internal_notes',
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'mechanic': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'service_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mileage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'km'}),
            'customer_complaint': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '¿Qué reporta el cliente?'}),
            'mechanic_observations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'work_done': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'internal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import CustomUser
        from apps.vehicles.models import Vehicle
        self.fields['vehicle'].queryset = Vehicle.objects.select_related('customer').order_by('brand', 'model')
        self.fields['mechanic'].queryset = CustomUser.objects.filter(is_active=True).order_by('first_name')

        # Campos financieros e internos: solo para admin
        if user and not user.is_admin:
            self.fields.pop('internal_notes', None)

        if not self.instance.pk:
            import datetime
            self.fields['service_date'].initial = datetime.date.today()
            if user:
                self.fields['mechanic'].initial = user


class ServiceOrderPartForm(forms.ModelForm):
    class Meta:
        model = ServiceOrderPart
        fields = ['name', 'quantity', 'unit_price', 'unit_cost', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ServiceOrderLaborForm(forms.ModelForm):
    class Meta:
        model = ServiceOrderLabor
        fields = ['description', 'hours', 'price_per_hour', 'cost_per_hour']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost_per_hour': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
