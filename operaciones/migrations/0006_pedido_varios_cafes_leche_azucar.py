import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def pasar_a_lineas(apps, schema_editor):
    """Cada pedido existente (un solo café) pasa a tener una línea."""
    Pedido = apps.get_model('operaciones', 'Pedido')
    Linea = apps.get_model('operaciones', 'LineaPedido')
    Linea.objects.bulk_create([
        Linea(pedido_id=p.pk, cafe_id=p.cafe_id, cantidad=p.cantidad,
              precio_unitario=p.precio_unitario)
        for p in Pedido.objects.all()
    ])


def volver_a_un_cafe(apps, schema_editor):
    """Reversa: conserva la primera línea de cada pedido (se pierden las demás)."""
    Pedido = apps.get_model('operaciones', 'Pedido')
    Linea = apps.get_model('operaciones', 'LineaPedido')
    for p in Pedido.objects.all():
        l = Linea.objects.filter(pedido_id=p.pk).order_by('id').first()
        if l:
            Pedido.objects.filter(pk=p.pk).update(
                cafe_id=l.cafe_id, cantidad=l.cantidad, precio_unitario=l.precio_unitario)


class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0005_inventario_y_usuario'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido', name='leche',
            field=models.CharField(
                choices=[('ninguna', 'Sin leche'), ('deslactosada', 'Deslactosada'),
                         ('entera', 'Entera'), ('semidescremada', 'Semidescremada'),
                         ('almendras', 'De almendras')],
                default='ninguna', max_length=20, verbose_name='Leche'),
        ),
        migrations.AddField(
            model_name='pedido', name='azucar',
            field=models.BooleanField(default=False, verbose_name='Con azúcar'),
        ),
        migrations.CreateModel(
            name='LineaPedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField(
                    validators=[django.core.validators.MinValueValidator(1)], verbose_name='Cantidad')),
                ('precio_unitario', models.DecimalField(decimal_places=2, editable=False, max_digits=8)),
                ('cafe', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                           related_name='lineas', to='operaciones.cafe', verbose_name='Café')),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='lineas', to='operaciones.pedido')),
            ],
            options={'ordering': ['id']},
        ),
        migrations.AddConstraint(
            model_name='lineapedido',
            constraint=models.UniqueConstraint(fields=('pedido', 'cafe'), name='un_cafe_por_pedido'),
        ),
        migrations.RunPython(pasar_a_lineas, volver_a_un_cafe),
        migrations.RemoveField(model_name='pedido', name='cafe'),
        migrations.RemoveField(model_name='pedido', name='cantidad'),
        migrations.RemoveField(model_name='pedido', name='precio_unitario'),
    ]
