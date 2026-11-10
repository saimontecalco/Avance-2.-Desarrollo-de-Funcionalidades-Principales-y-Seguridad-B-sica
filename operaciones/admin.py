from django.contrib import admin

from .models import Cafe, Pedido


@admin.register(Cafe)
class CafeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock', 'activo')
    list_editable = ('precio', 'stock', 'activo')
    search_fields = ('nombre',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_cliente', 'cafe', 'cantidad', 'fecha')
