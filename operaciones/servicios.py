"""Lógica de negocio de inventario y pedidos.

Todo cambio de existencias pasa por aquí, dentro de una transacción y con el
café bloqueado (``select_for_update``), para que el stock nunca quede negativo
ni inconsistente, ya sea que el pedido venga del sitio web o de la API.
"""
from django.db import transaction
from django.db.models import F

from .models import Cafe, LineaPedido, Pedido


class ErrorNegocio(Exception):
    """Regla de negocio incumplida; ``campo`` indica a qué dato se refiere."""

    def __init__(self, campo, mensaje):
        super().__init__(mensaje)
        self.campo = campo
        self.mensaje = mensaje


def _unir_lineas(lineas):
    """{cafe_pk: (cafe, cantidad)}. Si un café se repite, suma sus cantidades."""
    unidas = {}
    for l in lineas:
        cafe, cantidad = l['cafe'], l['cantidad']
        previo = unidas.get(cafe.pk, (cafe, 0))[1]
        unidas[cafe.pk] = (cafe, previo + cantidad)
    if not unidas:
        raise ErrorNegocio('lineas', 'Elige al menos un café.')
    return unidas


def _bloquear_cafes(pks):
    """Bloquea los cafés en orden de pk (evita interbloqueos entre pedidos)."""
    cafes = Cafe.objects.select_for_update().filter(pk__in=pks).order_by('pk')
    return {c.pk: c for c in cafes}


def _validar_linea(cafe, cantidad, disponible, *, exigir_activo):
    if exigir_activo and not cafe.activo:
        raise ErrorNegocio('lineas', f'{cafe.nombre} no está disponible.')
    if cantidad > disponible:
        raise ErrorNegocio(
            'lineas',
            f'Existencias insuficientes de {cafe.nombre}: quedan {disponible}.',
        )


@transaction.atomic
def crear_pedido(*, nombre_cliente, lineas, leche=Pedido.Leche.NINGUNA, azucar=False, usuario=None):
    """``lineas``: lista de ``{'cafe': Cafe, 'cantidad': int}`` (uno o más cafés)."""
    unidas = _unir_lineas(lineas)
    bloqueados = _bloquear_cafes(unidas)
    for pk, (_, cantidad) in unidas.items():
        _validar_linea(bloqueados[pk], cantidad, bloqueados[pk].stock, exigir_activo=True)

    pedido = Pedido.objects.create(
        nombre_cliente=nombre_cliente, leche=leche, azucar=azucar, usuario=usuario)
    for pk, (_, cantidad) in unidas.items():
        cafe = bloqueados[pk]
        Cafe.objects.filter(pk=pk).update(stock=F('stock') - cantidad)
        LineaPedido.objects.create(
            pedido=pedido, cafe=cafe, cantidad=cantidad, precio_unitario=cafe.precio)
    return pedido


@transaction.atomic
def actualizar_pedido(pedido, *, nombre_cliente=None, lineas=None, leche=None, azucar=None):
    """Actualiza un pedido; si cambian los cafés, reajusta existencias por diferencia."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)

    if lineas is not None:
        nuevas = _unir_lineas(lineas)
        previas = {l.cafe_id: l for l in pedido.lineas.all()}
        bloqueados = _bloquear_cafes(set(nuevas) | set(previas))

        for pk, (_, cantidad) in nuevas.items():
            cafe = bloqueados[pk]
            apartado = previas[pk].cantidad if pk in previas else 0  # lo apartado vuelve a estar libre
            # Un café ya incluido en el pedido puede conservarse aunque se haya desactivado.
            _validar_linea(cafe, cantidad, cafe.stock + apartado, exigir_activo=pk not in previas)

        for pk in set(nuevas) | set(previas):
            antes = previas[pk].cantidad if pk in previas else 0
            ahora = nuevas[pk][1] if pk in nuevas else 0
            if antes != ahora:
                Cafe.objects.filter(pk=pk).update(stock=F('stock') + antes - ahora)

        for pk, linea in previas.items():
            if pk not in nuevas:
                linea.delete()
        for pk, (_, cantidad) in nuevas.items():
            if pk in previas:  # conserva el precio con el que se pidió
                if previas[pk].cantidad != cantidad:
                    previas[pk].cantidad = cantidad
                    previas[pk].save(update_fields=['cantidad'])
            else:
                LineaPedido.objects.create(
                    pedido=pedido, cafe=bloqueados[pk], cantidad=cantidad,
                    precio_unitario=bloqueados[pk].precio)

    if nombre_cliente is not None:
        pedido.nombre_cliente = nombre_cliente
    if leche is not None:
        pedido.leche = leche
    if azucar is not None:
        pedido.azucar = azucar
    pedido.save()
    return pedido


@transaction.atomic
def eliminar_pedido(pedido):
    """Borra el pedido y devuelve sus unidades al inventario."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    lineas = list(pedido.lineas.order_by('cafe_id'))
    _bloquear_cafes([l.cafe_id for l in lineas])
    for l in lineas:
        Cafe.objects.filter(pk=l.cafe_id).update(stock=F('stock') + l.cantidad)
    pedido.delete()
