from decimal import Decimal
from django.db import migrations

CAFES_INICIALES = [
    ('Mocha', Decimal('7.50')),
    ('Espresso', Decimal('4.00')),
    ('Americano', Decimal('4.50')),
    ('Capuchino', Decimal('6.00')),
    ('Ice Coffee', Decimal('6.50')),
]


def cargar_cafes(apps, schema_editor):
    Cafe = apps.get_model('operaciones', 'Cafe')
    Pedido = apps.get_model('operaciones', 'Pedido')

    for nombre, precio in CAFES_INICIALES:
        Cafe.objects.get_or_create(nombre=nombre, defaults={'precio': precio})

    # Los pedidos anteriores eran todos "Latte" a $6.00: se conservan tal cual.
    # Latte queda como no disponible (no sale en pedidos nuevos, pero se puede reactivar en /admin/).
    if Pedido.objects.exists():
        latte, _ = Cafe.objects.get_or_create(
            nombre='Latte', defaults={'precio': Decimal('6.00'), 'activo': False}
        )
        Pedido.objects.filter(cafe__isnull=True).update(
            cafe=latte, precio_unitario=Decimal('6.00')
        )


class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0002_cafe_y_pedido_cafe'),
    ]

    operations = [
        migrations.RunPython(cargar_cafes, migrations.RunPython.noop),
    ]
