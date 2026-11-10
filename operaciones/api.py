from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Cafe, Pedido
from .serializers import PedidoSerializer, ProductoSerializer, RegistroSerializer

User = get_user_model()


class SoloAdminEscribe(BasePermission):
    """Cualquier usuario autenticado consulta; solo el personal (is_staff) modifica."""

    message = 'Solo el personal administrativo puede modificar el inventario.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.is_staff


class InventarioViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin, mixins.UpdateModelMixin,
                        viewsets.GenericViewSet):
    """Inventario: agregar (POST), consultar (GET) y actualizar (PUT/PATCH). Sin DELETE."""

    serializer_class = ProductoSerializer
    permission_classes = [SoloAdminEscribe]

    def get_queryset(self):
        qs = Cafe.objects.all().order_by('nombre')
        p = self.request.query_params
        if buscar := p.get('search', '').strip():
            qs = qs.filter(nombre__icontains=buscar)  # ORM => consulta parametrizada
        if (activo := p.get('activo', '').lower()) in ('true', 'false'):
            qs = qs.filter(activo=(activo == 'true'))
        return qs


class PedidoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                    mixins.CreateModelMixin, mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    """Pedidos: crear, consultar y actualizar. Cada usuario ve solo los suyos."""

    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Pedido.objects.select_related('usuario').prefetch_related('lineas__cafe')
        if not self.request.user.is_staff:
            qs = qs.filter(usuario=self.request.user)  # ajeno => 404, no filtra existencia
        p = self.request.query_params
        if buscar := p.get('search', '').strip():
            qs = qs.filter(Q(nombre_cliente__icontains=buscar) | Q(lineas__cafe__nombre__icontains=buscar)).distinct()
        if (cafe := p.get('cafe', '')).isdigit():
            qs = qs.filter(lineas__cafe_id=int(cafe)).distinct()
        return qs


class RegistroView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'registro'

    def post(self, request):
        s = RegistroSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'username': user.username},
                        status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'  # limita intentos para frenar fuerza bruta

    def post(self, request):
        s = AuthTokenSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        user = s.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'username': user.username, 'is_staff': user.is_staff})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class YoView(APIView):
    def get(self, request):
        u = request.user
        return Response({'id': u.id, 'username': u.username, 'is_staff': u.is_staff})

