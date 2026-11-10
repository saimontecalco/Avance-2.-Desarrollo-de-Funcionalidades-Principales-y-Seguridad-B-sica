from django import forms
from django.db.models import Q

from .models import Cafe, Pedido
from .servicios import actualizar_pedido, crear_pedido


class CafeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, cafe):
        return f'{cafe.nombre} — ${cafe.precio}'


class PedidoForm(forms.ModelForm):
    """Formulario del sitio con plantillas: un café por pedido.

    La selección de varios cafés se hace en la app React (flujo por pasos);
    un pedido de varios cafés se puede editar aquí (nombre, leche y azúcar),
    pero sus cafés solo se cambian desde la app.
    """

    cafe = CafeChoiceField(
        label='Café',
        queryset=Cafe.objects.none(),
        empty_label='Selecciona un café',
        error_messages={'required': 'Selecciona un café.'},
        widget=forms.Select(attrs={'class': 'input'}),
    )
    cantidad = forms.IntegerField(
        label='Cantidad de cafés', min_value=1,
        widget=forms.NumberInput(attrs={'class': 'input', 'min': 1, 'placeholder': '1'}),
    )

    class Meta:
        model = Pedido
        fields = ['cafe', 'cantidad', 'nombre_cliente', 'leche', 'azucar']
        widgets = {
            'nombre_cliente': forms.TextInput(
                attrs={'class': 'input', 'placeholder': 'Escribe tu nombre'}
            ),
            'leche': forms.Select(attrs={'class': 'input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['leche'].required = False
        self.fields['leche'].choices = Pedido.Leche.choices  # sin opción vacía
        self.lineas_existentes = list(self.instance.lineas.all()) if self.instance.pk else []
        self.multiples_cafes = len(self.lineas_existentes) > 1
        if self.multiples_cafes:
            del self.fields['cafe'], self.fields['cantidad']
            return
        # Solo cafés disponibles; al editar, también el café que ya tenía el pedido.
        filtro = Q(activo=True)
        if self.lineas_existentes:
            filtro |= Q(pk=self.lineas_existentes[0].cafe_id)
            self.initial['cafe'] = self.lineas_existentes[0].cafe_id
            self.initial['cantidad'] = self.lineas_existentes[0].cantidad
        self.fields['cafe'].queryset = Cafe.objects.filter(filtro)

    def save(self, commit=True):
        """Guarda vía servicios: así el inventario se descuenta de forma atómica."""
        d = self.cleaned_data
        lineas = None if self.multiples_cafes else [{'cafe': d['cafe'], 'cantidad': d['cantidad']}]
        if self.instance.pk is None:
            return crear_pedido(
                nombre_cliente=d['nombre_cliente'], lineas=lineas,
                leche=d['leche'] or Pedido.Leche.NINGUNA, azucar=d['azucar'],
            )
        return actualizar_pedido(
            self.instance, nombre_cliente=d['nombre_cliente'], lineas=lineas,
            leche=d['leche'] or Pedido.Leche.NINGUNA, azucar=d['azucar'],
        )
