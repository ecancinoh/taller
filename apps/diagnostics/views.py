import google.generativeai as genai
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from apps.diagnostics.models import AIDiagnosticRequest
from apps.service_orders.models import ServiceOrder


def _model_without_prefix(model_name):
	return model_name.replace('models/', '', 1)


def _get_candidate_models():
	preferred = [
		'models/gemini-2.5-flash',
		'models/gemini-2.0-flash',
		'models/gemini-flash-latest',
	]

	try:
		available = [
			model.name
			for model in genai.list_models()
			if 'generateContent' in getattr(model, 'supported_generation_methods', [])
		]
	except Exception:
		# Fallback seguro cuando no se puede listar modelos.
		return [_model_without_prefix(name) for name in preferred]

	ordered = []
	for name in preferred:
		if name in available:
			ordered.append(name)

	# Toma otros modelos Gemini con generateContent, evitando variantes TTS.
	for name in available:
		if name in ordered:
			continue
		if name.startswith('models/gemini') and 'tts' not in name.lower():
			ordered.append(name)

	if not ordered:
		ordered = preferred

	return [_model_without_prefix(name) for name in ordered]


def _extract_tokens_used(ai_result):
	usage = getattr(ai_result, 'usage_metadata', None)
	if not usage:
		return None
	return getattr(usage, 'total_token_count', None)


class GenerateDiagnosticView(View):
	def post(self, request, order_id):
		order_qs = ServiceOrder.objects.select_related('vehicle__customer', 'mechanic')
		if not request.user.is_admin:
			order_qs = order_qs.filter(mechanic=request.user)
		order = get_object_or_404(order_qs, pk=order_id)

		if not settings.GEMINI_API_KEY:
			messages.error(request, 'GEMINI_API_KEY no está configurada en el entorno.')
			return redirect('service_orders:detail', pk=order.pk)

		user_prompt = request.POST.get('prompt', '').strip()
		fallback_prompt = (
			f"Vehículo: {order.vehicle}. "
			f"Motivo cliente: {order.customer_complaint}. "
			f"Observaciones mecánico: {order.mechanic_observations or 'Sin observaciones'}."
		)
		prompt = user_prompt or fallback_prompt

		system_hint = (
			'Eres un asistente técnico para taller automotriz. Responde en español de forma breve y accionable. '
			'Máximo 6 viñetas cortas y máximo 120 palabras. Incluye: '
			'1) causas probables, 2) prueba prioritaria, 3) riesgo (alto/medio/bajo), '
			'4) repuesto probable, 5) acción recomendada.'
		)

		try:
			genai.configure(api_key=settings.GEMINI_API_KEY)
			candidate_models = _get_candidate_models()

			ai_result = None
			model_name = None
			last_error = None
			for candidate in candidate_models:
				try:
					model = genai.GenerativeModel(candidate)
					ai_result = model.generate_content(
						f'{system_hint}\n\n{prompt}',
						generation_config={
							'temperature': 0.3,
							'max_output_tokens': 220,
						},
					)
					model_name = candidate
					break
				except Exception as exc:
					last_error = exc

			if ai_result is None or model_name is None:
				raise RuntimeError(last_error or 'No se encontró un modelo compatible para generateContent.')

			response_text = getattr(ai_result, 'text', '').strip()
			if not response_text:
				response_text = 'Gemini no devolvió texto en esta solicitud.'
			# Capa extra de control de longitud para mantener respuestas operativas en móvil.
			if len(response_text) > 1200:
				response_text = response_text[:1200].rstrip() + '...'

			AIDiagnosticRequest.objects.create(
				service_order=order,
				prompt=prompt,
				response=response_text,
				model_used=model_name,
				tokens_used=_extract_tokens_used(ai_result),
			)
			messages.success(request, f'Diagnóstico IA generado correctamente con {model_name}.')
		except Exception as exc:
			messages.error(request, f'No se pudo generar diagnóstico IA: {exc}')

		return redirect('service_orders:detail', pk=order.pk)
