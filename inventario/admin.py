from django.contrib import admin, messages
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from .models import Producto, Categoria, Sugerencia

# 1. FILTRO DE STOCK
class StockAnomaloFilter(admin.SimpleListFilter):
    title = 'Alertas de Stock'
    parameter_name = 'anomalia'
    def lookups(self, request, model_admin):
        return (('sospechoso', 'Stock sospechoso (>50)'), ('critico', 'Stock muy alto (>200)'),)
    def queryset(self, request, queryset):
        if self.value() == 'sospechoso': return queryset.filter(stock__gt=50)
        if self.value() == 'critico': return queryset.filter(stock__gt=200)
        return queryset

# 2. ACCIÓN PARA CAMBIAR CATEGORÍA
def cambiar_categoria_masivo(modeladmin, request, queryset):
    if 'apply' in request.POST:
        categoria_id = request.POST.get('categoria')
        nueva_cat = Categoria.objects.get(id=categoria_id)
        filas = queryset.update(categoria=nueva_cat)
        modeladmin.message_user(request, f"Se movieron {filas} productos.", messages.SUCCESS)
        return HttpResponseRedirect(request.get_full_path())
    return render(request, 'admin/cambiar_categoria_intermedio.html', {
        'productos': queryset, 
        'categorias': Categoria.objects.all(), 
        'action': 'cambiar_categoria_masivo'
    })

# 3. PANEL PRODUCTOS
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre_display', 'precio', 'stock', 'alerta_stock', 'disponible', 'categoria')
    list_editable = ('stock', 'disponible')
    list_filter = ('disponible', 'categoria', StockAnomaloFilter) 
    search_fields = ('nombre', 'codigo_barras')
    
    readonly_fields = ('ver_buscador',)
    
    fieldsets = (
        ('Información Principal', {
            'fields': (
                'nombre', 
                'codigo_barras', 
                'categoria', 
                'precio', 
                ('stock', 'stock_minimo'), 
                'disponible'
            )
        }),
        ('Multimedia y Contenido', {
            'fields': ('imagen', 'ver_buscador', 'descripcion', 'dato_curioso'),
        }),
    )

    actions = [
        cambiar_categoria_masivo, 
        'ocultar_productos', 
        'mostrar_productos', 
        'resetear_descripcion', 
        'marcar_agotado', 
        'limpiar_images_seleccionadas'
    ]

    @admin.display(description='🔍 Ayuda de Imagen')
    def ver_buscador(self, obj):
        if not obj.nombre: return "Guarda primero"
        url = f"https://www.google.com/search?q={obj.nombre}+fondo+blanco&tbm=isch"
        return format_html('<a href="{}" target="_blank" style="background: #007bff; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">🔍 Buscar Imagen</a>', url)

    @admin.display(description='Nombre', ordering='nombre')
    def nombre_display(self, obj):
        if obj.stock == 0 and hasattr(obj, 'peticiones_volver') and obj.peticiones_volver > 0:
            return format_html('<span style="color: #d9534f; font-weight: bold;">{} 🔥</span>', obj.nombre)
        return obj.nombre

    def alerta_stock(self, obj):
        if obj.stock <= obj.stock_minimo: 
            return format_html('<span style="color: red; font-weight: bold;">⚠️ REPONER</span>')
        return format_html('<span style="color: green;">OK</span>')

    @admin.action(description="🙈 Ocultar")
    def ocultar_productos(self, request, queryset): queryset.update(disponible=False)
    
    @admin.action(description="👁️ Mostrar")
    def mostrar_productos(self, request, queryset): queryset.update(disponible=True)
    
    @admin.action(description="🚫 Agotado")
    def marcar_agotado(self, request, queryset): queryset.update(stock=0)
    
    # MODIFICADO: Ahora limpia ambos campos para que Gemini pueda re-procesarlos
    @admin.action(description="📝 Limpiar descripciones y datos")
    def resetear_descripcion(self, request, queryset): 
        queryset.update(descripcion="", dato_curioso="")
    
    @admin.action(description="🖼️ Limpiar imágenes")
    def limpiar_images_seleccionadas(self, request, queryset): queryset.update(imagen=None)

# 4. PANEL SUGERENCIAS
@admin.register(Sugerencia)
class SugerenciaAdmin(admin.ModelAdmin):
    list_display = ('tipo_color', 'nombre', 'email', 'fecha_envio', 'ver_imagen', 'leido')
    list_filter = ('tipo', 'leido', 'fecha_envio')
    list_editable = ('leido',)
    readonly_fields = ('fecha_envio', 'foto_detalle')

    def tipo_color(self, obj):
        colores = {'PRODUCTO': '#007bff', 'CRITICA': '#dc3545', 'FELICITACION': '#28a745', 'OTRO': '#6c757d'}
        return format_html('<span style="background: {}; color: white; padding: 3px 10px; border-radius: 10px; font-weight: bold;">{}</span>', colores.get(obj.tipo), obj.get_tipo_display())

    def ver_imagen(self, obj):
        return "🖼️ ✅" if obj.imagen else "❌"

    def foto_detalle(self, obj):
        if obj.imagen:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-width: 400px; border-radius: 10px;" /></a>', obj.imagen.url)
        return "Sin foto"