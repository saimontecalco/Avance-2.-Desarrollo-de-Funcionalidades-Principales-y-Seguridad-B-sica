import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0003_cafes_iniciales'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pedido',
            name='cafe',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pedidos', to='operaciones.cafe', verbose_name='Café'),
        ),
        migrations.AlterField(
            model_name='pedido',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=2, editable=False, max_digits=8),
        ),
    ]
