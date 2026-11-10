"""Lógica de negocio de inventario y pedidos.

Todo cambio de existencias pasa por aquí, dentro de una transacción y con el
café bloqueado (``select_for_update``), para que el stock nunca quede negativo
ni inconsistente, ya sea que el pedido venga del sitio web o de la API.
"""
from django.db import transaction
from django.db.models import F

from .models import Cafe, Pedido


class ErrorNegocio(Exception):
    """Regla de negocio incumplida; ``campo`` indica a qué dato se refiere."""

    def __init__(self, campo, mensaje):
        super().__init__(mensaje)
        self.campo = campo
        self.mensaje = mensaje


def _bloquear_cafe(pk):
    return Cafe.objects.select_for_update().get(pk=pk)


def _validar_stock(cafe, cantidad, disponible):
    if cantidad > disponible:
        raise ErrorNegocio(
            'cantidad',
            f'Existencias insuficientes de {cafe.nombre}: quedan {disponible}.',
        )


@transaction.atomic
def crear_pedido(*, cafe, nombre_cliente, cantidad, usuario=None):
    cafe = _bloquear_cafe(cafe.pk)
    if not cafe.activo:
        raise ErrorNegocio('cafe', f'{cafe.nombre} no está disponible.')
    _validar_stock(cafe, cantidad, cafe.stock)
    Cafe.objects.filter(pk=cafe.pk).update(stock=F('stock') - cantidad)
    return Pedido.objects.create(
        nombre_cliente=nombre_cliente, cafe=cafe, cantidad=cantidad,
        precio_unitario=cafe.precio, usuario=usuario,
    )


@transaction.atomic
def actualizar_pedido(pedido, *, cafe=None, nombre_cliente=None, cantidad=None):
    """Actualiza un pedido y reajusta existencias según la diferencia."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    nuevo_cafe = cafe or pedido.cafe
    nueva_cantidad = pedido.cantidad if cantidad is None else cantidad

    if nuevo_cafe.pk == pedido.cafe_id:
        actual = _bloquear_cafe(pedido.cafe_id)
        disponible = actual.stock + pedido.cantidad  # lo ya apartado vuelve a estar libre
        _validar_stock(actual, nueva_cantidad, disponible)
        Cafe.objects.filter(pk=actual.pk).update(stock=disponible - nueva_cantidad)
    else:
        nuevo = _bloquear_cafe(nuevo_cafe.pk)
        if not nuevo.activo:
            raise ErrorNegocio('cafe', f'{nuevo.nombre} no está disponible.')
        _validar_stock(nuevo, nueva_cantidad, nuevo.stock)
        Cafe.objects.filter(pk=pedido.cafe_id).update(stock=F('stock') + pedido.cantidad)
        Cafe.objects.filter(pk=nuevo.pk).update(stock=F('stock') - nueva_cantidad)
        pedido.cafe = nuevo
        pedido.precio_unitario = nuevo.precio  # al cambiar de café se congela el precio nuevo

    pedido.cantidad = nueva_cantidad
    if nombre_cliente is not None:
        pedido.nombre_cliente = nombre_cliente
    pedido.save()
    return pedido


@transaction.atomic
def eliminar_pedido(pedido):
    """Borra el pedido y devuelve sus unidades al inventario."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    Cafe.objects.filter(pk=pedido.cafe_id).update(stock=F('stock') + pedido.cantidad)
    pedido.delete()
