class CabecerasSeguridadApiMiddleware:
    """Cabeceras defensivas para las respuestas de /api/.

    - CSP ``default-src 'none'``: una respuesta JSON nunca puede ejecutar scripts.
    - ``Cache-Control: no-store``: no se guardan datos privados en cachés.
    (``X-Content-Type-Options: nosniff`` y ``X-Frame-Options`` ya los pone Django.)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/api/'):
            response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
            response['Cache-Control'] = 'no-store'
        return response
