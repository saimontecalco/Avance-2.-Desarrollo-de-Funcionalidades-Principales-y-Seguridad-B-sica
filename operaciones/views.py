from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PedidoForm
from .models import PORCENTAJE_DESCUENTO, PORCENTAJE_IMPUESTO, Pedido
from .servicios import ErrorNegocio, eliminar_pedido

INFO_PRECIOS = {
    'porcentaje_impuesto': PORCENTAJE_IMPUESTO,
    'porcentaje_descuento': PORCENTAJE_DESCUENTO,
}


def lista(request):
    """READ: listado de pedidos."""
    return render(request, 'operaciones/pedido_lista.html',
                  {'pedidos': Pedido.objects.select_related('cafe')})


def detalle(request, pk):
    """READ: ticket de un pedido."""
    pedido = get_object_or_404(Pedido, pk=pk)
    return render(request, 'operaciones/pedido_detalle.html', {'pedido': pedido})


def crear(request):
    """CREATE"""
    form = PedidoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            pedido = form.save()
        except ErrorNegocio as e:
            form.add_error(e.campo, e.mensaje)
        else:
            messages.success(request, f'Pedido #{pedido.pk} realizado con éxito')
            return redirect('lista')
    return render(request, 'operaciones/pedido_form.html',
                  {'form': form, 'titulo': 'Nuevo pedido', **INFO_PRECIOS})


def editar(request, pk):
    """UPDATE"""
    pedido = get_object_or_404(Pedido, pk=pk)
    form = PedidoForm(request.POST or None, instance=pedido)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except ErrorNegocio as e:
            form.add_error(e.campo, e.mensaje)
        else:
            messages.success(request, f'Pedido #{pedido.pk} actualizado')
            return redirect('lista')
    return render(request, 'operaciones/pedido_form.html',
                  {'form': form, 'titulo': f'Editar pedido #{pedido.pk}', **INFO_PRECIOS})


def eliminar(request, pk):
    """DELETE (pide confirmación y borra solo con POST)"""
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        eliminar_pedido(pedido)
        messages.success(request, f'Pedido #{pk} eliminado')
        return redirect('lista')
    return render(request, 'operaciones/pedido_eliminar.html', {'pedido': pedido})
