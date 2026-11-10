from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .forms import PedidoForm
from .models import Cafe, LineaPedido, Pedido
from .servicios import ErrorNegocio, actualizar_pedido, crear_pedido, eliminar_pedido


def nuevo_pedido(nombre, cafe, cantidad, **extra):
    """Pedido de un solo café, directo en la base (sin pasar por inventario)."""
    p = Pedido.objects.create(nombre_cliente=nombre, **extra)
    LineaPedido.objects.create(pedido=p, cafe=cafe, cantidad=cantidad)
    return p


def crear_cafe(nombre='Café de prueba', precio='6.00', activo=True, stock=100):
    return Cafe.objects.create(
        nombre=nombre, precio=Decimal(precio), activo=activo, stock=stock
    )


class CafeInicialesTests(TestCase):
    def test_menu_inicial_tiene_los_cinco_cafes(self):
        nombres = set(Cafe.objects.filter(activo=True).values_list('nombre', flat=True))
        self.assertTrue(
            {'Mocha', 'Espresso', 'Americano', 'Capuchino', 'Ice Coffee'} <= nombres
        )


class PedidoModeloTests(TestCase):
    def setUp(self):
        self.cafe = crear_cafe()

    def test_totales_de_un_cafe(self):
        p = nuevo_pedido('Ana', self.cafe, 1)
        self.assertEqual(p.subtotal, Decimal('6.00'))
        self.assertEqual(p.impuesto_total, Decimal('0.96'))
        self.assertEqual(p.descuento_total, Decimal('0.60'))
        self.assertEqual(p.total, Decimal('6.36'))

    def test_totales_de_siete_cafes(self):
        p = nuevo_pedido('Ana', self.cafe, 7)
        self.assertEqual(p.total, Decimal('44.52'))

    def test_precio_depende_del_cafe(self):
        caro = crear_cafe('Caro', '10.00')
        p = nuevo_pedido('Ana', caro, 2)
        self.assertEqual(p.subtotal, Decimal('20.00'))
        self.assertEqual(p.impuesto_total, Decimal('3.20'))   # 16 % sin cambios
        self.assertEqual(p.descuento_total, Decimal('2.00'))  # 10 % sin cambios
        self.assertEqual(p.total, Decimal('21.20'))

    def test_mayorista_solo_si_mas_de_cinco(self):
        self.assertFalse(nuevo_pedido('A', self.cafe, 5).es_mayorista)
        self.assertTrue(nuevo_pedido('A', self.cafe, 6).es_mayorista)

    def test_totales_con_varios_cafes(self):
        otro = crear_cafe('Otro', '4.00')
        p = nuevo_pedido('Ana', self.cafe, 1)  # 6.00
        LineaPedido.objects.create(pedido=p, cafe=otro, cantidad=2)  # 8.00
        self.assertEqual(p.subtotal, Decimal('14.00'))
        self.assertEqual(p.total, Decimal('14.84'))  # +16 % -10 %
        self.assertEqual(p.cantidad, 3)

    def test_mayorista_cuenta_cafes_de_todas_las_lineas(self):
        otro = crear_cafe('Otro', '4.00')
        p = nuevo_pedido('Ana', self.cafe, 3)
        LineaPedido.objects.create(pedido=p, cafe=otro, cantidad=3)
        self.assertTrue(p.es_mayorista)

    def test_leche_y_azucar_por_defecto(self):
        p = nuevo_pedido('Ana', self.cafe, 1)
        self.assertEqual((p.leche, p.azucar), ('ninguna', False))

    def test_opciones_de_leche(self):
        self.assertEqual(
            {v for v, _ in Pedido.Leche.choices},
            {'ninguna', 'deslactosada', 'entera', 'semidescremada', 'almendras'})

    def test_cambiar_precio_del_menu_no_altera_pedidos_anteriores(self):
        p = nuevo_pedido('Ana', self.cafe, 1)
        self.cafe.precio = Decimal('9.00')
        self.cafe.save()
        p.refresh_from_db()
        self.assertEqual(p.total, Decimal('6.36'))


class PedidoFormTests(TestCase):
    def setUp(self):
        self.cafe = crear_cafe()
        self.inactivo = crear_cafe('Descontinuado', '5.00', activo=False)

    def test_solo_ofrece_cafes_disponibles(self):
        opciones = PedidoForm().fields['cafe'].queryset
        self.assertIn(self.cafe, opciones)
        self.assertNotIn(self.inactivo, opciones)

    def test_rechaza_cafe_no_disponible(self):
        form = PedidoForm({'cafe': self.inactivo.pk, 'nombre_cliente': 'Ana', 'cantidad': 1})
        self.assertFalse(form.is_valid())

    def test_cafe_es_obligatorio(self):
        form = PedidoForm({'nombre_cliente': 'Ana', 'cantidad': 1})
        self.assertFalse(form.is_valid())
        self.assertIn('cafe', form.errors)

    def test_al_editar_se_conserva_el_cafe_aunque_ya_no_este_disponible(self):
        p = nuevo_pedido('Ana', self.inactivo, 1)
        self.assertIn(self.inactivo, PedidoForm(instance=p).fields['cafe'].queryset)


class PedidoCrudTests(TestCase):
    def setUp(self):
        self.cafe = crear_cafe()
        self.pedido = nuevo_pedido('Luis', self.cafe, 2)

    # READ
    def test_lista_muestra_pedidos_y_su_cafe(self):
        r = self.client.get(reverse('lista'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Luis')
        self.assertContains(r, 'Café de prueba')

    def test_lista_vacia(self):
        Pedido.objects.all().delete()
        r = self.client.get(reverse('lista'))
        self.assertContains(r, 'Todavía no hay pedidos')

    def test_detalle(self):
        r = self.client.get(reverse('detalle', args=[self.pedido.pk]))
        self.assertContains(r, 'Total a pagar')
        self.assertContains(r, 'Café de prueba')
        self.assertContains(r, '12.72')

    def test_detalle_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse('detalle', args=[999])).status_code, 404)

    # CREATE
    def test_formulario_muestra_selector_con_los_cafes_y_precios(self):
        r = self.client.get(reverse('crear'))
        self.assertContains(r, '<select')
        self.assertContains(r, 'Mocha — $7.50')
        self.assertContains(r, 'Espresso — $4.00')
        self.assertContains(r, 'Americano — $4.50')
        self.assertContains(r, 'Capuchino — $6.00')
        self.assertContains(r, 'Ice Coffee — $6.50')
        self.assertContains(r, 'Impuesto: 16%')
        self.assertContains(r, 'Descuento: 10%')

    def test_crear_valido_guarda_cafe_y_precio(self):
        mocha = Cafe.objects.get(nombre='Mocha')
        r = self.client.post(reverse('crear'),
                             {'nombre_cliente': 'Ana', 'cafe': mocha.pk, 'cantidad': 3})
        self.assertRedirects(r, reverse('lista'))
        nuevo = Pedido.objects.get(nombre_cliente='Ana')
        linea = nuevo.lineas.get()
        self.assertEqual((linea.cafe, linea.precio_unitario), (mocha, Decimal('7.50')))
        self.assertEqual(nuevo.subtotal, Decimal('22.50'))

    def test_crear_rechaza_cantidad_cero_negativa_nombre_vacio_y_sin_cafe(self):
        for datos in ({'nombre_cliente': 'Ana', 'cafe': self.cafe.pk, 'cantidad': 0},
                      {'nombre_cliente': 'Ana', 'cafe': self.cafe.pk, 'cantidad': -2},
                      {'nombre_cliente': '   ', 'cafe': self.cafe.pk, 'cantidad': 2},
                      {'nombre_cliente': 'Ana', 'cantidad': 2}):
            r = self.client.post(reverse('crear'), datos)
            self.assertEqual(r.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 1)

    # UPDATE
    def test_editar(self):
        r = self.client.post(reverse('editar', args=[self.pedido.pk]),
                             {'nombre_cliente': 'Luis M.', 'cafe': self.cafe.pk, 'cantidad': 8})
        self.assertRedirects(r, reverse('lista'))
        self.pedido.refresh_from_db()
        self.assertEqual((self.pedido.nombre_cliente, self.pedido.cantidad), ('Luis M.', 8))

    def test_editar_cambiando_de_cafe_actualiza_el_precio(self):
        espresso = Cafe.objects.get(nombre='Espresso')
        self.client.post(reverse('editar', args=[self.pedido.pk]),
                         {'nombre_cliente': 'Luis', 'cafe': espresso.pk, 'cantidad': 2})
        self.pedido.refresh_from_db()
        linea = self.pedido.lineas.get()
        self.assertEqual((linea.cafe, linea.precio_unitario), (espresso, Decimal('4.00')))

    def test_editar_sin_cambiar_cafe_conserva_precio_original(self):
        self.cafe.precio = Decimal('9.00')
        self.cafe.save()
        self.client.post(reverse('editar', args=[self.pedido.pk]),
                         {'nombre_cliente': 'Luis', 'cafe': self.cafe.pk, 'cantidad': 3})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.lineas.get().precio_unitario, Decimal('6.00'))

    def test_editar_invalido_no_guarda(self):
        self.client.post(reverse('editar', args=[self.pedido.pk]),
                         {'nombre_cliente': 'Luis', 'cafe': self.cafe.pk, 'cantidad': 0})
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.cantidad, 2)

    def test_crear_guarda_leche_y_azucar(self):
        self.client.post(reverse('crear'), {'nombre_cliente': 'Ana', 'cafe': self.cafe.pk,
                                            'cantidad': 1, 'leche': 'almendras', 'azucar': 'on'})
        p = Pedido.objects.get(nombre_cliente='Ana')
        self.assertEqual((p.leche, p.azucar), ('almendras', True))

    def test_editar_pedido_de_varios_cafes_no_toca_sus_lineas(self):
        otro = crear_cafe('Otro', '4.00')
        LineaPedido.objects.create(pedido=self.pedido, cafe=otro, cantidad=1)
        r = self.client.get(reverse('editar', args=[self.pedido.pk]))
        self.assertNotContains(r, 'name="cafe"')
        self.client.post(reverse('editar', args=[self.pedido.pk]),
                         {'nombre_cliente': 'Luis M.', 'leche': 'entera'})
        self.pedido.refresh_from_db()
        self.assertEqual((self.pedido.nombre_cliente, self.pedido.leche), ('Luis M.', 'entera'))
        self.assertEqual(self.pedido.lineas.count(), 2)

    # DELETE
    def test_eliminar_pide_confirmacion_y_no_borra_con_get(self):
        r = self.client.get(reverse('eliminar', args=[self.pedido.pk]))
        self.assertContains(r, 'Sí, eliminar')
        self.assertEqual(Pedido.objects.count(), 1)

    def test_eliminar_con_post(self):
        r = self.client.post(reverse('eliminar', args=[self.pedido.pk]))
        self.assertRedirects(r, reverse('lista'))
        self.assertEqual(Pedido.objects.count(), 0)


class ServiciosVariosCafesTests(TestCase):
    def setUp(self):
        self.a = crear_cafe('A', '10.00', stock=10)
        self.b = crear_cafe('B', '4.00', stock=10)

    def lineas(self, qa, qb):
        return [{'cafe': self.a, 'cantidad': qa}, {'cafe': self.b, 'cantidad': qb}]

    def stock(self):
        self.a.refresh_from_db(); self.b.refresh_from_db()
        return self.a.stock, self.b.stock

    def test_crear_descuenta_cada_cafe(self):
        p = crear_pedido(nombre_cliente='Ana', lineas=self.lineas(2, 3), leche='entera', azucar=True)
        self.assertEqual(self.stock(), (8, 7))
        self.assertEqual((p.subtotal, p.leche, p.azucar), (Decimal('32.00'), 'entera', True))

    def test_cafe_repetido_se_suma(self):
        p = crear_pedido(nombre_cliente='Ana', lineas=[{'cafe': self.a, 'cantidad': 1},
                                                       {'cafe': self.a, 'cantidad': 2}])
        self.assertEqual(p.lineas.get().cantidad, 3)
        self.assertEqual(self.stock(), (7, 10))

    def test_sin_lineas_se_rechaza(self):
        with self.assertRaises(ErrorNegocio):
            crear_pedido(nombre_cliente='Ana', lineas=[])

    def test_si_un_cafe_no_alcanza_no_se_descuenta_ninguno(self):
        with self.assertRaises(ErrorNegocio):
            crear_pedido(nombre_cliente='Ana', lineas=self.lineas(2, 11))
        self.assertEqual(self.stock(), (10, 10))
        self.assertEqual(Pedido.objects.count(), 0)

    def test_actualizar_reajusta_agrega_y_quita_lineas(self):
        p = crear_pedido(nombre_cliente='Ana', lineas=self.lineas(2, 3))
        actualizar_pedido(p, lineas=[{'cafe': self.a, 'cantidad': 5}])  # +3 de A, B se repone
        self.assertEqual(self.stock(), (5, 10))
        self.assertEqual(p.lineas.count(), 1)
        actualizar_pedido(p, lineas=self.lineas(1, 4))
        self.assertEqual(self.stock(), (9, 6))

    def test_actualizar_sin_lineas_solo_cambia_leche_y_azucar(self):
        p = crear_pedido(nombre_cliente='Ana', lineas=self.lineas(2, 3))
        actualizar_pedido(p, leche='almendras', azucar=True)
        p.refresh_from_db()
        self.assertEqual((p.leche, p.azucar, p.lineas.count()), ('almendras', True, 2))
        self.assertEqual(self.stock(), (8, 7))

    def test_eliminar_repone_todos_los_cafes(self):
        p = crear_pedido(nombre_cliente='Ana', lineas=self.lineas(2, 3))
        eliminar_pedido(p)
        self.assertEqual(self.stock(), (10, 10))
