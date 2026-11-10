from django import forms
from django.db.models import Q

from .models import Cafe, Pedido
from .servicios import actualizar_pedido, crear_pedido


class CafeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, cafe):
        return f'{cafe.nombre} — ${cafe.precio}'


class PedidoForm(forms.ModelForm):
    cafe = CafeChoiceField(
        label='Café',
        queryset=Cafe.objects.none(),
        empty_label='Selecciona un café',
        error_messages={'required': 'Selecciona un café.'},
        widget=forms.Select(attrs={'class': 'input'}),
    )

    class Meta:
        model = Pedido
        fields = ['cafe', 'nombre_cliente', 'cantidad']
        widgets = {
            'nombre_cliente': forms.TextInput(
                attrs={'class': 'input', 'placeholder': 'Escribe tu nombre'}
            ),
            'cantidad': forms.NumberInput(
                attrs={'class': 'input', 'min': 1, 'placeholder': '1'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo cafés disponibles; al editar, también el café que ya tenía el pedido.
        filtro = Q(activo=True)
        if self.instance.pk:
            filtro |= Q(pk=self.instance.cafe_id)
        self.fields['cafe'].queryset = Cafe.objects.filter(filtro)

    def save(self, commit=True):
        """Guarda vía servicios: así el inventario se descuenta de forma atómica."""
        datos = self.cleaned_data
        if self.instance.pk is None:
            return crear_pedido(
                cafe=datos['cafe'], nombre_cliente=datos['nombre_cliente'],
                cantidad=datos['cantidad'],
            )
        return actualizar_pedido(
            self.instance, cafe=datos['cafe'],
            nombre_cliente=datos['nombre_cliente'], cantidad=datos['cantidad'],
        )
