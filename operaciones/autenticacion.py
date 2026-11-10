from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """Token en la cabecera estándar ``Authorization: Bearer <token>`` (la que usa Postman)."""

    keyword = 'Bearer'
