"""Validadores de entrada compartidos por formularios web y API (prevención de XSS)."""
import re

from django.core.exceptions import ValidationError

_HTML = re.compile(r'[<>]')
_CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def validar_texto_seguro(valor):
    """Rechaza etiquetas HTML (< >) y caracteres de control en textos libres.

    Es una defensa en profundidad: además, las plantillas de Django escapan
    toda salida y la API responde solo JSON con ``nosniff``.
    """
    if _HTML.search(valor):
        raise ValidationError(
            'No se permiten los caracteres < o > (etiquetas HTML).', code='html'
        )
    if _CONTROL.search(valor):
        raise ValidationError('El texto contiene caracteres no permitidos.', code='control')
