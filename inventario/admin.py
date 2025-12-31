from django.contrib import admin
from .models import Producto, Categoria
from django.utils.html import format_html

# Definimos un filtro personalizado para la barra lateral
class StockAnomaloFilter(admin.SimpleListFilter):
    title = 'Alertas de Stock' # Nombre que verás en el panel
    parameter_name = 'anomalia'

    def lookups(self, request, model_admin):
        # Opciones que aparecerán al hacer clic
        return (
            ('sospechoso', 'Stock sospechoso (>50)'),
            ('critico', 'Stock muy alto (>200)'),
        )

    def queryset(self, request, queryset):
        # La lógica de filtrado
        if self.value() == 'sospechoso':
            return queryset.filter(stock__gt=50) # gt significa "greater than" (mayor que)
        if self.value() == 'critico':
            return queryset.filter(stock__gt=200)
        return queryset

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock', 'stock_minimo', 'alerta_stock', 'categoria')
    list_filter = ('categoria', StockAnomaloFilter) # <-- Agregamos el filtro aquí
    search_fields = ('nombre', 'codigo_barras')
    list_editable = ('stock',) # <-- TRUCO PRO: permite editar el stock sin entrar al producto

    def alerta_stock(self, obj):
        if obj.stock > 1000:
            return format_html('<span style="color: purple; font-weight: bold;">🚨 ANOMALÍA</span>')
        if obj.stock <= obj.stock_minimo:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ REPONER</span>')
        return format_html('<span style="color: green;">OK</span>')
    
    alerta_stock.short_description = 'Estado'