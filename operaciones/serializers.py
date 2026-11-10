from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Cafe, Pedido
from .servicios import ErrorNegocio, actualizar_pedido, crear_pedido
from .validators import validar_texto_seguro

MAX_CANTIDAD = 10_000
User = get_user_model()


class ProductoSerializer(serializers.ModelSerializer):
    """Producto del inventario (un café del menú con sus existencias)."""

    class Meta:
        model = Cafe
        fields = ['id', 'nombre', 'precio', 'stock', 'activo']
        read_only_fields = ['id']
        extra_kwargs = {
            'nombre': {'error_messages': {'unique': 'Ya existe un producto con ese nombre.'}},
        }

    def validate_nombre(self, valor):
        return ' '.join(valor.split())  # normaliza espacios


class PedidoSerializer(serializers.ModelSerializer):
    cafe = serializers.PrimaryKeyRelatedField(queryset=Cafe.objects.all())
    cafe_nombre = serializers.CharField(source='cafe.nombre', read_only=True)
    cantidad = serializers.IntegerField(min_value=1, max_value=MAX_CANTIDAD)
    usuario = serializers.CharField(source='usuario.username', read_only=True, default=None)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    impuesto_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    descuento_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Pedido
        fields = [
            'id', 'nombre_cliente', 'cafe', 'cafe_nombre', 'cantidad',
            'precio_unitario', 'subtotal', 'impuesto_total', 'descuento_total',
            'total', 'es_mayorista', 'usuario', 'fecha',
        ]
        # Lista blanca: el cliente nunca puede fijar precio, dueño ni fecha.
        read_only_fields = [
            'id', 'precio_unitario', 'es_mayorista', 'usuario', 'fecha',
        ]

    def validate_nombre_cliente(self, valor):
        return ' '.join(valor.split())

    def create(self, validated_data):
        try:
            return crear_pedido(usuario=self.context['request'].user, **validated_data)
        except ErrorNegocio as e:
            raise serializers.ValidationError({e.campo: e.mensaje})

    def update(self, instance, validated_data):
        try:
            return actualizar_pedido(instance, **validated_data)
        except ErrorNegocio as e:
            raise serializers.ValidationError({e.campo: e.mensaje})


class RegistroSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=150, validators=[validar_texto_seguro])
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, valor):
        if User.objects.filter(username__iexact=valor).exists():
            raise serializers.ValidationError('Ese nombre de usuario ya está en uso.')
        return valor

    def validate(self, datos):
        usuario = User(username=datos['username'], email=datos.get('email', ''))
        try:  # aplica AUTH_PASSWORD_VALIDATORS (longitud, comunes, numéricas, similitud)
            password_validation.validate_password(datos['password'], usuario)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return datos

    def create(self, datos):
        return User.objects.create_user(
            username=datos['username'], password=datos['password'],
            email=datos.get('email', ''),
        )
