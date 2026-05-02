import csv
import io
import quopri
import re

import vobject
from django.db.models import Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from apps.core.mixins import MechanicRequiredMixin
from .models import Customer
from .forms import CustomerForm, CustomerImportForm


def _decode_uploaded_file(uploaded_file):
    raw = uploaded_file.read()
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('No se pudo decodificar el archivo. Usa UTF-8, UTF-8 BOM o Latin-1.')


def _safe_get(data, keys):
    for key in keys:
        value = data.get(key)
        if value is not None:
            value = str(value).strip()
            if value:
                return value
    return ''


def _split_full_name(full_name):
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return ' '.join(parts[:-1]), parts[-1]


def _normalize_phone(phone):
    return ''.join(ch for ch in phone if ch.isdigit() or ch == '+')


def _normalize_email(email):
    return email.strip().lower()


def _normalize_contact_row(row):
    phone = _normalize_phone(row.get('phone', ''))
    email = _normalize_email(row.get('email', ''))
    return {
        'first_name': row.get('first_name', '').strip(),
        'last_name': row.get('last_name', '').strip(),
        'phone': phone,
        'email': email,
        'address': row.get('address', '').strip(),
        'notes': row.get('notes', '').strip(),
    }


def _parse_csv_contacts(decoded_text):
    reader = csv.DictReader(io.StringIO(decoded_text))
    rows = []
    for raw in reader:
        first_name = _safe_get(raw, ('first_name', 'nombre', 'name', 'given_name'))
        last_name = _safe_get(raw, ('last_name', 'apellido', 'surname', 'family_name'))
        full_name = _safe_get(raw, ('full_name', 'nombre_completo'))

        if not first_name and full_name:
            first_name, last_name = _split_full_name(full_name)

        row = {
            'first_name': first_name,
            'last_name': last_name,
            'phone': _safe_get(raw, ('phone', 'telefono', 'tel', 'mobile', 'celular')),
            'email': _safe_get(raw, ('email', 'correo', 'mail')),
            'address': _safe_get(raw, ('address', 'direccion', 'dirección')),
            'notes': _safe_get(raw, ('notes', 'nota', 'observaciones')),
        }
        row = _normalize_contact_row(row)
        if any(row.values()):
            rows.append(row)
    return rows


def _unescape_vcard_text(value):
    return (
        value.replace('\\n', '\n')
        .replace('\\N', '\n')
        .replace('\\,', ',')
        .replace('\\;', ';')
        .replace('\\\\', '\\')
    )


def _decode_vcard_value(raw_value, left_side):
    left_upper = left_side.upper()
    is_quoted_printable = 'ENCODING=QUOTED-PRINTABLE' in left_upper

    charset = 'utf-8'
    charset_match = re.search(r'CHARSET=([^;:]+)', left_side, re.IGNORECASE)
    if charset_match:
        charset = charset_match.group(1).strip().strip('"')

    value = raw_value.strip()
    if not is_quoted_printable:
        return _unescape_vcard_text(value)

    try:
        raw_bytes = quopri.decodestring(value)
    except Exception:
        raw_bytes = value.encode('latin-1', errors='replace')

    for encoding in (charset, 'utf-8', 'latin-1'):
        try:
            return _unescape_vcard_text(raw_bytes.decode(encoding))
        except (UnicodeDecodeError, LookupError):
            continue

    return _unescape_vcard_text(raw_bytes.decode('utf-8', errors='replace'))


def _parse_vcf_contacts_fallback(decoded_text):
    rows = []
    blocks = re.findall(r'BEGIN:VCARD(.*?)END:VCARD', decoded_text, flags=re.DOTALL | re.IGNORECASE)

    for block in blocks:
        first_name = ''
        last_name = ''
        full_name = ''
        phone = ''
        email = ''
        notes = ''
        address = ''

        for line in block.split('\n'):
            line = line.strip()
            if not line or ':' not in line:
                continue

            left, raw_value = line.split(':', 1)
            prop = left.split(';', 1)[0].upper()
            decoded_value = _decode_vcard_value(raw_value, left)

            if prop == 'N':
                parts = decoded_value.split(';')
                if len(parts) >= 2:
                    last_name = parts[0].strip()
                    first_name = parts[1].strip()
            elif prop == 'FN' and not full_name:
                full_name = decoded_value.strip()
            elif prop == 'TEL' and not phone:
                phone = decoded_value.strip()
            elif prop == 'EMAIL' and not email:
                email = decoded_value.strip()
            elif prop == 'NOTE' and not notes:
                notes = decoded_value.strip()
            elif prop == 'ADR' and not address:
                adr_parts = decoded_value.split(';')
                # ADR: pobox;extended;street;city;region;postal;country
                street = adr_parts[2].strip() if len(adr_parts) > 2 else ''
                city = adr_parts[3].strip() if len(adr_parts) > 3 else ''
                region = adr_parts[4].strip() if len(adr_parts) > 4 else ''
                address = ', '.join([part for part in (street, city, region) if part])

        if not first_name and full_name:
            first_name, last_name = _split_full_name(full_name)

        row = _normalize_contact_row(
            {
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'email': email,
                'address': address,
                'notes': notes,
            }
        )
        if any(row.values()):
            rows.append(row)

    return rows


def _parse_vcf_contacts(decoded_text):
    def _prepare_vcf_text(text):
        # Normaliza saltos de línea y repara líneas partidas por exportadores de contactos.
        text = text.replace('\r\n', '\n').replace('\r', '\n').lstrip('\ufeff')

        unfolded = []
        for line in text.split('\n'):
            if not line:
                unfolded.append(line)
                continue
            if line.startswith((' ', '\t')) and unfolded:
                # RFC 6350 line folding: una línea que empieza con espacio/tab continúa la anterior.
                unfolded[-1] += line[1:]
            else:
                unfolded.append(line)

        repaired = []
        qp_cont_re = re.compile(r'^[=A-Fa-f0-9]+$')

        def _looks_like_qp_fragment(line):
            # Fragmento típico de Quoted-Printable: inicia con '=' y contiene solo
            # bytes hex codificados y separadores comunes de vCard.
            return bool(re.match(r'^=[0-9A-Fa-f=;,:()\-\s]+$', line))

        for line in unfolded:
            if repaired and repaired[-1].endswith('=') and qp_cont_re.match(line):
                # Algunos teléfonos cortan Quoted-Printable sin folding RFC; recomponemos el valor.
                repaired[-1] = repaired[-1][:-1] + line
            elif repaired and _looks_like_qp_fragment(line):
                prev = repaired[-1].upper()
                if (
                    'QUOTED-PRINTABLE' in prev
                    or repaired[-1].endswith('=')
                    or re.search(r'(?:=[0-9A-Fa-f]{2}){2,}$', repaired[-1])
                ):
                    # Algunos exportadores parten la siguiente línea en bloques '=XX=YY...'
                    # sin dejar '=' al final de la línea previa.
                    repaired[-1] += line
                else:
                    repaired.append(line)
            else:
                repaired.append(line)

        normalized = []
        custom_tel_re = re.compile(r'^([A-Z-]+);X-CUSTOM\((.*?)\):(.*)$', re.IGNORECASE)
        for line in repaired:
            match = custom_tel_re.match(line)
            if match:
                # Algunos exportadores usan "X-CUSTOM(...)" no válido para vobject.
                # Conservamos la propiedad y el valor, descartando el parámetro inválido.
                prop_name = match.group(1).upper()
                value = match.group(3).strip()
                normalized.append(f'{prop_name}:{value}')
            else:
                normalized.append(line)

        return '\n'.join(normalized)

    decoded_text = _prepare_vcf_text(decoded_text)
    rows = []
    try:
        for card in vobject.readComponents(decoded_text):
            first_name = ''
            last_name = ''
            if hasattr(card, 'n'):
                name_value = card.n.value
                first_name = getattr(name_value, 'given', '') or ''
                last_name = getattr(name_value, 'family', '') or ''

            if not first_name and hasattr(card, 'fn'):
                first_name, last_name = _split_full_name(str(card.fn.value))

            phone_entries = card.contents.get('tel', [])
            email_entries = card.contents.get('email', [])
            note_entries = card.contents.get('note', [])
            adr_entries = card.contents.get('adr', [])

            phone = str(phone_entries[0].value).strip() if phone_entries else ''
            email = str(email_entries[0].value).strip() if email_entries else ''
            notes = str(note_entries[0].value).strip() if note_entries else ''

            address = ''
            if adr_entries:
                adr = adr_entries[0].value
                address_parts = [
                    getattr(adr, 'street', ''),
                    getattr(adr, 'city', ''),
                    getattr(adr, 'region', ''),
                ]
                address = ', '.join([part for part in address_parts if part])

            row = _normalize_contact_row(
                {
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': phone,
                    'email': email,
                    'address': address,
                    'notes': notes,
                }
            )
            if any(row.values()):
                rows.append(row)
        return rows
    except Exception:
        return _parse_vcf_contacts_fallback(decoded_text)


class CustomerListView(MechanicRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        qs = Customer.objects.select_related('created_by')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                first_name__icontains=q
            ) | qs.filter(
                last_name__icontains=q
            ) | qs.filter(
                phone__icontains=q
            )
        return qs.order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class CustomerDetailView(MechanicRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['vehicles'] = self.object.vehicles.all()
        ctx['recent_orders'] = (
            self.object.vehicles
            .values_list('service_orders', flat=True)
        )
        return ctx


class CustomerCreateView(MechanicRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Cliente creado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nuevo cliente'
        ctx['btn_text'] = 'Guardar cliente'
        return ctx


class CustomerUpdateView(MechanicRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente actualizado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Editar: {self.object.full_name}'
        ctx['btn_text'] = 'Guardar cambios'
        return ctx


class CustomerImportView(MechanicRequiredMixin, TemplateView):
    template_name = 'customers/customer_import.html'
    session_key = 'customers_import_preview'

    def get(self, request, *args, **kwargs):
        form = CustomerImportForm()
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        if 'confirm_import' in request.POST:
            return self._confirm_import()

        form = CustomerImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        uploaded_file = form.cleaned_data['file']
        extension = uploaded_file.name.lower().rsplit('.', 1)[-1] if '.' in uploaded_file.name else ''
        if extension not in ('csv', 'vcf'):
            messages.error(request, 'Formato no soportado. Sube un archivo .csv o .vcf.')
            return self.render_to_response(self.get_context_data(form=form))

        try:
            decoded_text = _decode_uploaded_file(uploaded_file)
            if extension == 'csv':
                rows = _parse_csv_contacts(decoded_text)
            else:
                rows = _parse_vcf_contacts(decoded_text)
        except Exception as exc:
            messages.error(request, f'No se pudo leer el archivo: {exc}')
            return self.render_to_response(self.get_context_data(form=form))

        if not rows:
            messages.warning(request, 'No se encontraron contactos válidos para importar.')
            return self.render_to_response(self.get_context_data(form=form))

        request.session[self.session_key] = rows
        request.session.modified = True
        messages.info(request, f'Se cargaron {len(rows)} contactos. Revisa la vista previa antes de importar.')
        return redirect('customers:import_contacts')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        preview_rows = self.request.session.get(self.session_key, [])

        rows_with_flags = []
        duplicate_count = 0
        for idx, row in enumerate(preview_rows):
            is_duplicate = self._is_duplicate(row)
            if is_duplicate:
                duplicate_count += 1
            rows_with_flags.append({
                'index': idx,
                **row,
                'is_duplicate': is_duplicate,
            })

        ctx['preview_rows'] = rows_with_flags
        ctx['preview_count'] = len(rows_with_flags)
        ctx['duplicate_count'] = duplicate_count
        return ctx

    def _is_duplicate(self, row):
        query = Q()
        if row.get('phone'):
            query |= Q(phone__iexact=row['phone'])
        if row.get('email'):
            query |= Q(email__iexact=row['email'])
        if not query:
            return False
        return Customer.objects.filter(query).exists()

    def _confirm_import(self):
        rows = self.request.session.get(self.session_key, [])
        if not rows:
            messages.warning(self.request, 'No hay datos en vista previa para importar.')
            return redirect('customers:import_contacts')

        selected_indices_raw = self.request.POST.getlist('selected_rows')
        if not selected_indices_raw:
            messages.warning(self.request, 'Selecciona al menos un contacto para importar.')
            return redirect('customers:import_contacts')

        selected_indices = []
        for value in selected_indices_raw:
            try:
                idx = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(rows):
                selected_indices.append(idx)

        # Evita duplicados y mantiene el orden de selección original del archivo.
        selected_indices = sorted(set(selected_indices))
        if not selected_indices:
            messages.warning(self.request, 'No hay contactos válidos seleccionados para importar.')
            return redirect('customers:import_contacts')

        import_duplicates = self.request.POST.get('import_duplicates') == '1'
        created_count = 0
        skipped_duplicates = 0
        skipped_invalid = 0
        skipped_unselected = len(rows) - len(selected_indices)

        for idx in selected_indices:
            row = rows[idx]
            if self._is_duplicate(row) and not import_duplicates:
                skipped_duplicates += 1
                continue

            first_name = row.get('first_name', '').strip()
            if not first_name:
                skipped_invalid += 1
                continue

            Customer.objects.create(
                first_name=first_name,
                last_name=row.get('last_name', '').strip(),
                phone=row.get('phone', '').strip(),
                email=row.get('email', '').strip(),
                address=row.get('address', '').strip(),
                notes=row.get('notes', '').strip(),
                created_by=self.request.user,
            )
            created_count += 1

        self.request.session.pop(self.session_key, None)
        self.request.session.modified = True

        messages.success(
            self.request,
            f'Importación finalizada: {created_count} creados, '
            f'{skipped_duplicates} duplicados omitidos, {skipped_invalid} inválidos omitidos, '
            f'{skipped_unselected} no seleccionados.',
        )
        return redirect('customers:list')

