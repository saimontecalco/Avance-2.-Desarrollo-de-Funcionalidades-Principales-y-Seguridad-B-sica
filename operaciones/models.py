from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .validators import validar_texto_seguro

PORCENTAJE_IMPUESTO = 16  # %
PORCENTAJE_DESCUENTO = 10  # %


def redondear(valor):
    return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class Cafe(models.Model):
    """Tipo de café del menú. Se administra desde /admin/."""
    nombre = models.CharField(
        'Nombre', max_length=60, unique=True, validators=[validar_texto_seguro]
    )
    precio = models.DecimalField(
        'Precio', max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    stock = models.PositiveIntegerField(
        'Existencias', default=0, validators=[MaxValueValidator(1_000_000)],
        help_text='Unidades disponibles en inventario. Cada pedido las descuenta.',
    )
    activo = models.BooleanField(
        'Disponible', default=True,
        help_text='Si lo desmarcas, ya no aparece al crear pedidos nuevos.',
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'café'
        verbose_name_plural = 'cafés'

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    """Pedido de un cliente: uno o varios cafés (``lineas``) más leche y azúcar."""

    class Leche(models.TextChoices):
        NINGUNA = 'ninguna', 'Sin leche'
        DESLACTOSADA = 'deslactosada', 'Deslactosada'
        ENTERA = 'entera', 'Entera'
        SEMIDESCREMADA = 'semidescremada', 'Semidescremada'
        ALMENDRAS = 'almendras', 'De almendras'

    nombre_cliente = models.CharField(
        'Nombre del cliente', max_length=100, validators=[validar_texto_seguro]
    )
    # Quién hizo el pedido por la API (los pedidos del sitio web no tienen usuario).
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name='pedidos',
    )
    leche = models.CharField(
        'Leche', max_length=20, choices=Leche.choices, default=Leche.NINGUNA
    )
    azucar = models.BooleanField('Con azúcar', default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'Pedido #{self.pk} - {self.nombre_cliente}'

    # Los totales se calculan sobre las líneas (``prefetch_related('lineas__cafe')``
    # evita una consulta por pedido en los listados).
    @property
    def lineas_lista(self):
        return list(self.lineas.all())

    @property
    def cantidad(self):
        """Total de cafés del pedido (suma de todas las líneas)."""
        return sum(l.cantidad for l in self.lineas_lista)

    @property
    def nombre_cafe(self):
        return ', '.join(f'{l.cantidad} × {l.cafe.nombre}' for l in self.lineas_lista)

    @property
    def subtotal(self):
        return redondear(sum((l.importe for l in self.lineas_lista), Decimal('0')))

    @property
    def impuesto_total(self):
        return redondear(self.subtotal * PORCENTAJE_IMPUESTO / 100)

    @property
    def descuento_total(self):
        return redondear(self.subtotal * PORCENTAJE_DESCUENTO / 100)

    @property
    def total(self):
        return self.subtotal + self.impuesto_total - self.descuento_total

    @property
    def es_mayorista(self):
        return self.cantidad > 5


class LineaPedido(models.Model):
    """Un tipo de café dentro de un pedido, con su cantidad."""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='lineas')
    cafe = models.ForeignKey(
        Cafe, verbose_name='Café', on_delete=models.PROTECT, related_name='lineas'
    )
    cantidad = models.PositiveIntegerField(
        'Cantidad', validators=[MinValueValidator(1)]
    )
    # Precio del café al momento del pedido: si el menú cambia después,
    # los pedidos anteriores conservan su total original.
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2, editable=False)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['pedido', 'cafe'], name='un_cafe_por_pedido'),
        ]

    def __str__(self):
        return f'{self.cantidad} × {self.cafe.nombre}'

    def save(self, *args, **kwargs):
        if self.precio_unitario is None:
            self.precio_unitario = self.cafe.precio
        super().save(*args, **kwargs)

    @property
    def importe(self):
        return self.precio_unitario * self.cantidad
