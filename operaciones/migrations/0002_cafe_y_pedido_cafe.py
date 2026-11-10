import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cafe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=60, unique=True, verbose_name='Nombre')),
                ('precio', models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='Precio')),
                ('activo', models.BooleanField(default=True, help_text='Si lo desmarcas, ya no aparece al crear pedidos nuevos.', verbose_name='Disponible')),
            ],
            options={
                'verbose_name': 'café',
                'verbose_name_plural': 'cafés',
                'ordering': ['nombre'],
            },
        ),
        # Temporalmente opcionales; la migración 0003 los rellena y la 0004 los vuelve obligatorios.
        migrations.AddField(
            model_name='pedido',
            name='cafe',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='pedidos', to='operaciones.cafe', verbose_name='Café'),
        ),
        migrations.AddField(
            model_name='pedido',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=2, editable=False, max_digits=8, null=True),
        ),
    ]
