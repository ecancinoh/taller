import mimetypes

from django.views import View
from django.views.generic import DetailView
from django.http import Http404, FileResponse
from apps.service_orders.models import ShareToken


class PublicOrderView(DetailView):
    template_name = 'shared_views/public_order.html'
    context_object_name = 'order'

    def get_object(self):
        token_str = self.kwargs.get('token')
        try:
            share = ShareToken.objects.select_related(
                'service_order__vehicle__customer',
                'service_order__mechanic',
            ).get(token=token_str, is_active=True)
        except (ShareToken.DoesNotExist, ValueError):
            raise Http404('Enlace no válido o expirado.')
        return share.service_order

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        order = self.object
        ctx['parts'] = order.parts.all()
        ctx['photos'] = order.photos.filter(is_public=True)
        # Nunca exponemos datos financieros ni notas internas en vista pública
        return ctx


class PublicOrderPhotoView(View):
    def get(self, request, token, photo_id):
        try:
            share = ShareToken.objects.select_related('service_order').get(token=token, is_active=True)
        except ShareToken.DoesNotExist:
            raise Http404('Enlace no válido o expirado.')

        photo = share.service_order.photos.filter(pk=photo_id, is_public=True).first()
        if not photo or not photo.image:
            raise Http404('Foto no encontrada.')

        content_type, _ = mimetypes.guess_type(photo.image.name)
        if not content_type:
            content_type = 'application/octet-stream'

        return FileResponse(photo.image.open('rb'), content_type=content_type)

