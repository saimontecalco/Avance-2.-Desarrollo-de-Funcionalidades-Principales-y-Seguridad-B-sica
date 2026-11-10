from django.urls import path

from . import views

urlpatterns = [
    path('', views.lista, name='lista'),
    path('pedidos/nuevo/', views.crear, name='crear'),
    path('pedidos/<int:pk>/', views.detalle, name='detalle'),
    path('pedidos/<int:pk>/editar/', views.editar, name='editar'),
    path('pedidos/<int:pk>/eliminar/', views.eliminar, name='eliminar'),
]
