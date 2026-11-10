from django.urls import path
from rest_framework.routers import SimpleRouter

from . import api

router = SimpleRouter()
router.register('inventario', api.InventarioViewSet, basename='inventario')
router.register('pedidos', api.PedidoViewSet, basename='pedido')

urlpatterns = [
    path('auth/registro/', api.RegistroView.as_view(), name='api-registro'),
    path('auth/login/', api.LoginView.as_view(), name='api-login'),
    path('auth/logout/', api.LogoutView.as_view(), name='api-logout'),
    path('auth/yo/', api.YoView.as_view(), name='api-yo'),
    *router.urls,
]
