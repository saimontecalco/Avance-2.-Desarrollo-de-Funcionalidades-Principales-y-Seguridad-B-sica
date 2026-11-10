"""Pruebas de la API REST: inventario, pedidos y medidas de seguridad."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Cafe, Pedido

User = get_user_model()
CLAVE = 'Cl4ve-Segura-2026!'

SQLI = ["' OR '1'='1", "'; DROP TABLE operaciones_cafe; --", '" OR ""="', "1 UNION SELECT * FROM auth_user"]
XSS = ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>', '"><svg/onload=alert(1)>']


class ApiBase(TestCase):
    def setUp(self):
        cache.clear()  # reinicia los contadores de throttling
        self.admin = User.objects.create_user('admin', password=CLAVE, is_staff=True)
        self.ana = User.objects.create_user('ana', password=CLAVE)
        self.luis = User.objects.create_user('luis', password=CLAVE)
        self.cafe = Cafe.objects.create(nombre='Moka Test', precio=Decimal('10.00'), stock=20)
        self.anon = APIClient()

    def cliente(self, usuario):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + Token.objects.get_or_create(user=usuario)[0].key)
        return c

    def pedido_payload(self, **extra):
        return {'nombre_cliente': 'Ana', 'cafe': self.cafe.pk, 'cantidad': 2, **extra}


class AutenticacionTests(ApiBase):
    def test_registro_crea_usuario_normal_y_devuelve_token(self):
        r = self.anon.post(reverse('api-registro'), {'username': 'nuevo', 'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.json()['token'])
        self.assertFalse(User.objects.get(username='nuevo').is_staff)

    def test_registro_no_permite_hacerse_staff(self):
        self.anon.post(reverse('api-registro'),
                       {'username': 'listo', 'password': CLAVE, 'is_staff': True, 'is_superuser': True},
                       format='json')
        u = User.objects.get(username='listo')
        self.assertFalse(u.is_staff or u.is_superuser)

    def test_registro_rechaza_contrasena_debil_y_duplicado(self):
        r = self.anon.post(reverse('api-registro'), {'username': 'usuario1', 'password': '12345678'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.json())
        r = self.anon.post(reverse('api-registro'), {'username': 'ANA', 'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_registro_rechaza_html_en_usuario(self):
        r = self.anon.post(reverse('api-registro'),
                           {'username': '<script>x</script>', 'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_login_correcto_e_incorrecto(self):
        ok = self.anon.post(reverse('api-login'), {'username': 'ana', 'password': CLAVE}, format='json')
        self.assertEqual(ok.status_code, 200)
        self.assertIn('token', ok.json())
        mal = self.anon.post(reverse('api-login'), {'username': 'ana', 'password': 'mala'}, format='json')
        self.assertEqual(mal.status_code, 400)

    def test_login_limita_intentos_contra_fuerza_bruta(self):
        codigos = [self.anon.post(reverse('api-login'), {'username': 'ana', 'password': 'x'},
                                  format='json').status_code for _ in range(25)]
        self.assertIn(429, codigos)

    def test_logout_invalida_el_token(self):
        c = self.cliente(self.ana)
        self.assertEqual(c.post(reverse('api-logout')).status_code, 204)
        self.assertEqual(c.get(reverse('pedido-list')).status_code, 401)

    def test_endpoints_protegidos_sin_token_dan_401(self):
        for nombre in ('inventario-list', 'pedido-list', 'api-yo'):
            self.assertEqual(self.anon.get(reverse(nombre)).status_code, 401, nombre)
        self.assertEqual(self.anon.post(reverse('pedido-list'), self.pedido_payload(), format='json').status_code, 401)

    def test_token_falso_da_401(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Bearer ' + 'a' * 40)
        self.assertEqual(c.get(reverse('pedido-list')).status_code, 401)


class InventarioTests(ApiBase):
    def test_consultar_lista_y_detalle(self):
        c = self.cliente(self.ana)
        r = c.get(reverse('inventario-list'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('Moka Test', [p['nombre'] for p in r.json()['results']])
        d = c.get(reverse('inventario-detail', args=[self.cafe.pk])).json()
        self.assertEqual((d['precio'], d['stock']), ('10.00', 20))

    def test_filtros_de_busqueda_y_activo(self):
        Cafe.objects.create(nombre='Viejo', precio=Decimal('3'), stock=1, activo=False)
        c = self.cliente(self.ana)
        r = c.get(reverse('inventario-list'), {'search': 'moka'}).json()
        self.assertEqual([p['nombre'] for p in r['results']], ['Moka Test'])
        r = c.get(reverse('inventario-list'), {'activo': 'false'}).json()
        self.assertEqual([p['nombre'] for p in r['results']], ['Viejo'])

    def test_admin_agrega_producto(self):
        r = self.cliente(self.admin).post(reverse('inventario-list'),
                                          {'nombre': '  Flat   White ', 'precio': '8.50', 'stock': 30}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['nombre'], 'Flat White')  # espacios normalizados
        self.assertTrue(Cafe.objects.filter(nombre='Flat White', stock=30, activo=True).exists())

    def test_admin_actualiza_con_put_y_patch(self):
        c = self.cliente(self.admin)
        url = reverse('inventario-detail', args=[self.cafe.pk])
        r = c.patch(url, {'stock': 55}, format='json')
        self.assertEqual((r.status_code, r.json()['stock']), (200, 55))
        r = c.put(url, {'nombre': 'Moka Test', 'precio': '12.00', 'stock': 5, 'activo': False}, format='json')
        self.assertEqual(r.status_code, 200)
        self.cafe.refresh_from_db()
        self.assertEqual((self.cafe.precio, self.cafe.stock, self.cafe.activo), (Decimal('12.00'), 5, False))

    def test_usuario_normal_no_puede_modificar_inventario(self):
        c = self.cliente(self.ana)
        self.assertEqual(c.post(reverse('inventario-list'), {'nombre': 'Hack', 'precio': '1', 'stock': 1},
                                format='json').status_code, 403)
        self.assertEqual(c.patch(reverse('inventario-detail', args=[self.cafe.pk]), {'precio': '0.01'},
                                 format='json').status_code, 403)
        self.cafe.refresh_from_db()
        self.assertEqual(self.cafe.precio, Decimal('10.00'))

    def test_no_se_puede_borrar_producto(self):
        r = self.cliente(self.admin).delete(reverse('inventario-detail', args=[self.cafe.pk]))
        self.assertEqual(r.status_code, 405)
        self.assertTrue(Cafe.objects.filter(pk=self.cafe.pk).exists())

    def test_validaciones_de_datos(self):
        c = self.cliente(self.admin)
        antes = Cafe.objects.count()
        casos = [
            {'nombre': '', 'precio': '5', 'stock': 1},
            {'nombre': 'X', 'precio': '0', 'stock': 1},
            {'nombre': 'X', 'precio': '-3', 'stock': 1},
            {'nombre': 'X', 'precio': 'abc', 'stock': 1},
            {'nombre': 'X', 'precio': '5', 'stock': -1},
            {'nombre': 'X', 'precio': '5', 'stock': 'muchos'},
            {'nombre': 'X', 'precio': '5', 'stock': 99999999999999999999},
            {'nombre': 'N' * 61, 'precio': '5', 'stock': 1},
            {'nombre': 'Moka Test', 'precio': '5', 'stock': 1},  # duplicado
            {'precio': '5', 'stock': 1},                          # falta nombre
        ]
        for datos in casos:
            r = c.post(reverse('inventario-list'), datos, format='json')
            self.assertEqual(r.status_code, 400, datos)
        self.assertEqual(Cafe.objects.count(), antes)

    def test_producto_inexistente_404(self):
        self.assertEqual(self.cliente(self.ana).get(reverse('inventario-detail', args=[9999])).status_code, 404)


class PedidoTests(ApiBase):
    def test_crear_pedido_calcula_totales_y_descuenta_stock(self):
        r = self.cliente(self.ana).post(reverse('pedido-list'), self.pedido_payload(), format='json')
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual((d['subtotal'], d['impuesto_total'], d['descuento_total'], d['total']),
                         ('20.00', '3.20', '2.00', '21.20'))
        self.assertEqual((d['cafe_nombre'], d['usuario'], d['es_mayorista']), ('Moka Test', 'ana', False))
        self.cafe.refresh_from_db()
        self.assertEqual(self.cafe.stock, 18)

    def test_pedido_mayorista(self):
        r = self.cliente(self.ana).post(reverse('pedido-list'), self.pedido_payload(cantidad=6), format='json')
        self.assertTrue(r.json()['es_mayorista'])

    def test_consultar_lista_y_detalle(self):
        c = self.cliente(self.ana)
        pk = c.post(reverse('pedido-list'), self.pedido_payload(), format='json').json()['id']
        self.assertEqual(c.get(reverse('pedido-list')).json()['count'], 1)
        self.assertEqual(c.get(reverse('pedido-detail', args=[pk])).json()['nombre_cliente'], 'Ana')

    def test_actualizar_cantidad_reajusta_stock(self):
        c = self.cliente(self.ana)
        pk = c.post(reverse('pedido-list'), self.pedido_payload(cantidad=5), format='json').json()['id']
        self.cafe.refresh_from_db(); self.assertEqual(self.cafe.stock, 15)
        r = c.patch(reverse('pedido-detail', args=[pk]), {'cantidad': 8}, format='json')
        self.assertEqual((r.status_code, r.json()['cantidad']), (200, 8))
        self.cafe.refresh_from_db(); self.assertEqual(self.cafe.stock, 12)
        c.patch(reverse('pedido-detail', args=[pk]), {'cantidad': 1}, format='json')
        self.cafe.refresh_from_db(); self.assertEqual(self.cafe.stock, 19)

    def test_actualizar_con_put_y_cambio_de_cafe(self):
        otro = Cafe.objects.create(nombre='Otro', precio=Decimal('4.00'), stock=10)
        c = self.cliente(self.ana)
        pk = c.post(reverse('pedido-list'), self.pedido_payload(cantidad=3), format='json').json()['id']
        r = c.put(reverse('pedido-detail', args=[pk]),
                  {'nombre_cliente': 'Ana B.', 'cafe': otro.pk, 'cantidad': 2}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()['precio_unitario'], r.json()['subtotal']), ('4.00', '8.00'))
        self.cafe.refresh_from_db(); otro.refresh_from_db()
        self.assertEqual((self.cafe.stock, otro.stock), (20, 8))  # el anterior se repone

    def test_editar_sin_cambiar_cafe_conserva_precio_original(self):
        c = self.cliente(self.ana)
        pk = c.post(reverse('pedido-list'), self.pedido_payload(), format='json').json()['id']
        self.cafe.precio = Decimal('99.00'); self.cafe.save()
        r = c.patch(reverse('pedido-detail', args=[pk]), {'cantidad': 3}, format='json')
        self.assertEqual(r.json()['precio_unitario'], '10.00')

    def test_stock_insuficiente_se_rechaza_sin_cambios(self):
        r = self.cliente(self.ana).post(reverse('pedido-list'), self.pedido_payload(cantidad=21), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('cantidad', r.json())
        self.cafe.refresh_from_db()
        self.assertEqual((self.cafe.stock, Pedido.objects.count()), (20, 0))

    def test_actualizar_por_encima_del_stock_se_rechaza(self):
        c = self.cliente(self.ana)
        pk = c.post(reverse('pedido-list'), self.pedido_payload(cantidad=10), format='json').json()['id']
        r = c.patch(reverse('pedido-detail', args=[pk]), {'cantidad': 31}, format='json')  # 10 libres + 10 propios = 20
        self.assertEqual(r.status_code, 400)
        self.cafe.refresh_from_db(); self.assertEqual(self.cafe.stock, 10)
        self.assertEqual(Pedido.objects.get(pk=pk).cantidad, 10)

    def test_agotar_exactamente_el_stock_es_valido(self):
        r = self.cliente(self.ana).post(reverse('pedido-list'), self.pedido_payload(cantidad=20), format='json')
        self.assertEqual(r.status_code, 201)
        self.cafe.refresh_from_db(); self.assertEqual(self.cafe.stock, 0)

    def test_producto_no_disponible_se_rechaza(self):
        self.cafe.activo = False; self.cafe.save()
        r = self.cliente(self.ana).post(reverse('pedido-list'), self.pedido_payload(), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('cafe', r.json())

    def test_validaciones_de_datos(self):
        c = self.cliente(self.ana)
        casos = [
            self.pedido_payload(cantidad=0), self.pedido_payload(cantidad=-1),
            self.pedido_payload(cantidad='dos'), self.pedido_payload(cantidad=1.5),
            self.pedido_payload(cantidad=10**30), self.pedido_payload(cantidad=10_001),
            self.pedido_payload(nombre_cliente=''), self.pedido_payload(nombre_cliente='   '),
            self.pedido_payload(nombre_cliente='N' * 101), self.pedido_payload(cafe=9999),
            self.pedido_payload(cafe='abc'), {'nombre_cliente': 'Ana', 'cantidad': 1},
            {'cafe': self.cafe.pk, 'cantidad': 1}, {},
        ]
        for datos in casos:
            r = c.post(reverse('pedido-list'), datos, format='json')
            self.assertEqual(r.status_code, 400, datos)
        self.assertEqual(Pedido.objects.count(), 0)
        self.cafe.refresh_from_db(); self.assertEqual(self.cafe.stock, 20)

    def test_pedido_inexistente_404(self):
        self.assertEqual(self.cliente(self.ana).get(reverse('pedido-detail', args=[9999])).status_code, 404)

    def test_no_se_puede_borrar_pedido_por_la_api(self):
        c = self.cliente(self.ana)
        pk = c.post(reverse('pedido-list'), self.pedido_payload(), format='json').json()['id']
        self.assertEqual(c.delete(reverse('pedido-detail', args=[pk])).status_code, 405)

    def test_busqueda_por_cliente_y_filtro_por_cafe(self):
        c = self.cliente(self.ana)
        c.post(reverse('pedido-list'), self.pedido_payload(nombre_cliente='Zoe'), format='json')
        c.post(reverse('pedido-list'), self.pedido_payload(nombre_cliente='Beto'), format='json')
        self.assertEqual(c.get(reverse('pedido-list'), {'search': 'zo'}).json()['count'], 1)
        self.assertEqual(c.get(reverse('pedido-list'), {'cafe': self.cafe.pk}).json()['count'], 2)
        self.assertEqual(c.get(reverse('pedido-list'), {'cafe': 9999}).json()['count'], 0)


class AutorizacionPedidosTests(ApiBase):
    def setUp(self):
        super().setUp()
        self.pk_ana = self.cliente(self.ana).post(
            reverse('pedido-list'), self.pedido_payload(), format='json').json()['id']

    def test_usuario_no_ve_ni_modifica_pedidos_ajenos(self):
        luis = self.cliente(self.luis)
        self.assertEqual(luis.get(reverse('pedido-list')).json()['count'], 0)
        self.assertEqual(luis.get(reverse('pedido-detail', args=[self.pk_ana])).status_code, 404)
        r = luis.patch(reverse('pedido-detail', args=[self.pk_ana]), {'cantidad': 1}, format='json')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Pedido.objects.get(pk=self.pk_ana).cantidad, 2)

    def test_staff_ve_y_actualiza_todos_los_pedidos(self):
        c = self.cliente(self.admin)
        self.assertEqual(c.get(reverse('pedido-list')).json()['count'], 1)
        self.assertEqual(c.patch(reverse('pedido-detail', args=[self.pk_ana]), {'cantidad': 4},
                                 format='json').status_code, 200)


class SeguridadTests(ApiBase):
    # ---- Inyección SQL ----
    def test_sqli_en_parametros_de_busqueda_no_rompe_ni_filtra_datos(self):
        c = self.cliente(self.ana)
        for payload in SQLI:
            for nombre in ('inventario-list', 'pedido-list'):
                r = c.get(reverse(nombre), {'search': payload, 'cafe': payload, 'activo': payload})
                self.assertEqual(r.status_code, 200, (nombre, payload))
                self.assertEqual(r.json()['count'], 0)  # "' OR '1'='1" no devuelve todo
        self.assertTrue(Cafe.objects.filter(pk=self.cafe.pk).exists())  # la tabla sigue ahí
        self.assertEqual(User.objects.count(), 3)

    def test_sqli_en_cuerpo_se_guarda_como_texto_inerte_o_se_rechaza(self):
        c = self.cliente(self.ana)
        r = c.post(reverse('pedido-list'), self.pedido_payload(nombre_cliente="Robert'); DROP TABLE operaciones_pedido;--"),
                   format='json')
        self.assertEqual(r.status_code, 201)  # comillas no son HTML: se trata como dato (consulta parametrizada)
        self.assertEqual(Pedido.objects.get().nombre_cliente, "Robert'); DROP TABLE operaciones_pedido;--")
        self.assertEqual(c.get(reverse('pedido-list')).status_code, 200)  # la tabla sigue existiendo

    def test_sqli_en_login_no_autentica(self):
        for payload in SQLI:
            r = self.anon.post(reverse('api-login'), {'username': payload, 'password': payload}, format='json')
            self.assertEqual(r.status_code, 400)
            cache.clear()

    def test_sqli_en_id_de_url_da_404(self):
        c = self.cliente(self.ana)
        self.assertEqual(c.get('/api/pedidos/1%20OR%201=1/').status_code, 404)
        self.assertEqual(c.get("/api/inventario/1'--/").status_code, 404)

    # ---- XSS ----
    def test_xss_se_rechaza_en_todos_los_campos_de_texto(self):
        admin, ana = self.cliente(self.admin), self.cliente(self.ana)
        antes = Cafe.objects.count()
        for payload in XSS:
            self.assertEqual(ana.post(reverse('pedido-list'), self.pedido_payload(nombre_cliente=payload),
                                      format='json').status_code, 400, payload)
            self.assertEqual(admin.post(reverse('inventario-list'),
                                        {'nombre': payload, 'precio': '5', 'stock': 1},
                                        format='json').status_code, 400, payload)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(Cafe.objects.count(), antes)

    def test_xss_tampoco_entra_por_actualizacion(self):
        c = self.cliente(self.ana)
        pk = c.post(reverse('pedido-list'), self.pedido_payload(), format='json').json()['id']
        r = c.patch(reverse('pedido-detail', args=[pk]), {'nombre_cliente': XSS[0]}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Pedido.objects.get(pk=pk).nombre_cliente, 'Ana')

    def test_sitio_web_tambien_rechaza_xss_en_formulario(self):
        r = self.client.post(reverse('crear'),
                             {'nombre_cliente': XSS[0], 'cafe': self.cafe.pk, 'cantidad': 1})
        self.assertEqual(r.status_code, 200)  # vuelve al formulario con error
        self.assertEqual(Pedido.objects.count(), 0)

    def test_plantillas_escapan_html_aunque_exista_en_la_base(self):
        # Defensa en profundidad: si algo malicioso llegara a la BD, la salida se escapa.
        p = Pedido.objects.create(nombre_cliente='<script>alert(1)</script>', cafe=self.cafe,
                                  cantidad=1, precio_unitario=Decimal('10'))
        for url in (reverse('lista'), reverse('detalle', args=[p.pk]), reverse('editar', args=[p.pk])):
            r = self.client.get(url)
            self.assertNotContains(r, '<script>alert(1)</script>')
            self.assertContains(r, '&lt;script&gt;')

    def test_api_responde_json_con_cabeceras_defensivas(self):
        r = self.cliente(self.ana).get(reverse('pedido-list'))
        self.assertEqual(r['Content-Type'], 'application/json')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(r['X-Frame-Options'], 'DENY')
        self.assertIn("default-src 'none'", r['Content-Security-Policy'])
        self.assertEqual(r['Cache-Control'], 'no-store')

    # ---- Otros ataques comunes ----
    def test_asignacion_masiva_ignora_campos_protegidos(self):
        r = self.cliente(self.ana).post(
            reverse('pedido-list'),
            self.pedido_payload(precio_unitario='0.01', usuario='admin', id=777,
                                fecha='2000-01-01T00:00:00Z', es_mayorista=True), format='json')
        self.assertEqual(r.status_code, 201)
        p = Pedido.objects.get()
        self.assertEqual((p.precio_unitario, p.usuario, p.es_mayorista), (Decimal('10.00'), self.ana, False))
        self.assertNotEqual(p.pk, 777)

    def test_json_malformado_da_400_sin_detalles_internos(self):
        r = self.cliente(self.ana).post(reverse('pedido-list'), data='{no es json', content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertNotIn('Traceback', r.content.decode())

    def test_solo_acepta_json(self):
        r = self.cliente(self.ana).post(reverse('pedido-list'), data='nombre_cliente=Ana',
                                        content_type='application/x-www-form-urlencoded')
        self.assertEqual(r.status_code, 415)

    def test_cuerpo_demasiado_grande_se_rechaza(self):
        r = self.cliente(self.ana).post(reverse('pedido-list'),
                                        data='{"nombre_cliente": "' + 'a' * 200_000 + '"}',
                                        content_type='application/json')
        self.assertIn(r.status_code, (400, 413))
        self.assertEqual(Pedido.objects.count(), 0)

    def test_contrasenas_se_guardan_con_hash(self):
        self.assertTrue(self.ana.password.startswith(('pbkdf2_', 'argon2', 'bcrypt')))
        r = self.anon.post(reverse('api-registro'), {'username': 'nuevo', 'password': CLAVE}, format='json')
        self.assertNotIn(CLAVE, r.content.decode())

    def test_api_no_expone_la_contrasena_ni_hash(self):
        r = self.cliente(self.ana).get(reverse('api-yo'))
        self.assertNotIn('password', r.json())
