from django import forms
from django.utils import timezone
from .models import ServiceOrder, ServiceOrderPart, ServiceOrderLabor, ServiceOrderPhoto


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
            'service_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'},
            ),
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
        self.fields['service_date'].input_formats = ['%Y-%m-%d', '%d/%m/%Y']

        # Campos financieros e internos: solo para admin
        if user and not user.is_admin:
            self.fields.pop('internal_notes', None)
            # Mecánico: solo puede asignarse a sí mismo.
            self.fields['mechanic'].queryset = CustomUser.objects.filter(pk=user.pk)
            self.fields['mechanic'].initial = user

        if not self.instance.pk and not self.initial.get('service_date'):
            self.fields['service_date'].initial = timezone.localdate()

        if user and (not self.instance.pk or not self.instance.mechanic_id):
            self.fields['mechanic'].initial = user

        if self.instance.pk and self.instance.service_date:
            self.initial['service_date'] = self.instance.service_date.strftime('%Y-%m-%d')


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
        fields = ['description', 'price_per_hour']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Cambio de aceite, Alineación...'}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0'}),
        }
        labels = {
            'description': 'Descripción',
            'price_per_hour': 'Monto ($)',
        }


class ServiceOrderPhotoForm(forms.ModelForm):
    class Meta:
        model = ServiceOrderPhoto
        fields = ['image', 'caption', 'is_public']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción de la foto'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
