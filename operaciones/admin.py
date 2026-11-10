from django.contrib import admin

from .models import Cafe, LineaPedido, Pedido


@admin.register(Cafe)
class CafeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock', 'activo')
    list_editable = ('precio', 'stock', 'activo')
    search_fields = ('nombre',)


class LineaInline(admin.TabularInline):
    model = LineaPedido
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_cliente', 'nombre_cafe', 'leche', 'azucar', 'total', 'es_mayorista', 'fecha')
    list_filter = ('leche', 'azucar', 'fecha')
    search_fields = ('nombre_cliente', 'lineas__cafe__nombre')
    inlines = [LineaInline]
