# inventario/admin.py
import os
import time
import requests
import openpyxl
from django.db import transaction
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.urls import path, reverse

from .models import Producto, Categoria, Sugerencia, ConfiguracionSistema, ImportacionExcel

# ==============================================================================
# 🤖 FUNCIÓN AUXILIAR DE INTELIGENCIA ARTIFICIAL (GEMINI)
# Conserva 100% tu prompt y lógica original
# ==============================================================================
def llamar_gemini(p):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False, "Falta GEMINI_API_KEY en las variables de entorno de Railway."

    url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    modelo_detectado = "models/gemini-1.5-flash" 
    
    try:
        resp = requests.get(url_list)
        if resp.status_code == 200:
            modelos = resp.json().get('models', [])
            for m in modelos:
                nombre = m.get('name')
                if 'flash' in nombre.lower() and 'generateContent' in m.get('supportedGenerationMethods', []):
                    modelo_detectado = nombre
                    break
    except:
        pass

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/{modelo_detectado}:generateContent"
    
    tiene_desc = bool(p.descripcion and p.descripcion.strip())
    tiene_dato = bool(p.dato_curioso and p.dato_curioso.strip())

    if tiene_desc and tiene_dato:
        return False, "El producto ya tiene descripción y dato curioso completos."

    # --- TU PROMPT ORIGINAL COMPLETO ---
    prompt_text = f"""
    Eres el informante experto de 'Market Tunka'. Tu misión es generar fichas de producto útiles, variadas y breves. 
    Busca información REAL en internet si es necesario para ser preciso.

    PRODUCTO: {p.nombre}
    CATEGORÍA: {p.categoria.nombre if p.categoria else 'General'}

    ESTADO ACTUAL:
    - DESCRIPCIÓN: {p.descripcion if tiene_desc else "VACÍO"}
    - DATO CURIOSO: {p.dato_curioso if tiene_dato else "VACÍO"}

    REGLAS DE CONTENIDO (APLICAR SOLO A LO QUE ESTÉ 'VACÍO'):
    1. DESCRIPCIÓN (Máximo 25 palabras): 
        Define el producto o su uso principal de forma sobria y real. 
        - Si es un ingrediente, varía entre definir su origen, su función técnica o su perfil de sabor.
        - No repitas marca, peso o formato que ya esté en el título.

    2. DATO (Máximo 25 palabras): 
        Aquí debes VARIAR. Elige CUALQUIERA de estas opciones:
        - RECETA RÁPIDA: Si es ingrediente, enumera solo los componentes.
        - DIFERENCIA TÉCNICA: Explicar qué lo distingue.
        - DATO HISTÓRICO O CURIOSO: Origen del producto o una marca icónica.
        - BENEFICIO O MARIDAJE: Beneficio de un ingrediente o con qué combina mejor.
    
    3. REGLA DE GASEOSAS: 
        Si es una bebida y no especifica 'Zero/Sin Azúcar', menciona que es la fórmula clásica.

    4. NO REPETIR: Si ya hay una descripción, no repitas esa info en el dato.

    IMPORTANTE: Si un campo NO está 'VACÍO', devuélvelo exactamente como está.
    Responde estrictamente en este formato:
    DESCRIPCION: (Texto aquí)
    DATO: (Texto aquí)
    """

    try:
        response = requests.post(
            endpoint, 
            params={"key": api_key}, 
            json={"contents": [{"parts": [{"text": prompt_text}]}]}, 
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            texto_ia = data['candidates'][0]['content']['parts'][0]['text']
            
            if "DATO:" in texto_ia:
                partes = texto_ia.split("DATO:")
                desc_limpia = partes[0].replace("DESCRIPCION:", "").strip()
                dato_limpio = partes[1].replace("**", "").strip()
                
                if not tiene_desc: p.descripcion = desc_limpia
                if not tiene_dato: p.dato_curioso = dato_limpio
                
                p.save()
                return True, "Generado con éxito."
            else:
                return False, "Formato de IA incorrecto."
        elif response.status_code == 429:
            return False, "Cuota de IA alcanzada. Espera unos segundos."
        else:
            return False, f"Error {response.status_code}"

    except Exception as e:
        return False, str(e)


# ==============================================================================
# 1. FILTRO DE STOCK
# ==============================================================================
class StockAnomaloFilter(admin.SimpleListFilter):
    title = 'Alertas de Stock'
    parameter_name = 'anomalia'
    def lookups(self, request, model_admin):
        return (('sospechoso', 'Stock sospechoso (>50)'), ('critico', 'Stock muy alto (>200)'),)
    def queryset(self, request, queryset):
        if self.value() == 'sospechoso': return queryset.filter(stock__gt=50)
        if self.value() == 'critico': return queryset.filter(stock__gt=200)
        return queryset

# ==============================================================================
# 2. ACCIÓN PARA CAMBIAR CATEGORÍA
# ==============================================================================
def cambiar_categoria_masivo(modeladmin, request, queryset):
    if 'apply' in request.POST:
        categoria_id = request.POST.get('categoria')
        nueva_cat = Categoria.objects.get(id=categoria_id)
        filas = queryset.update(categoria=nueva_cat)
        modeladmin.message_user(request, f"Se movieron {filas} productos.", messages.SUCCESS)
        return HttpResponseRedirect(request.get_full_path())
    return render(request, 'admin/cambiar_categoria_intermedio.html', {
        'productos': queryset, 
        'categorias': Categoria.objects.all().order_by('nombre'), 
        'action': 'cambiar_categoria_masivo'
    })

# ==============================================================================
# 3. PANEL PRODUCTOS
# ==============================================================================
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre_display', 'precio', 'stock', 'alerta_stock', 'disponible', 'categoria')
    list_editable = ('stock', 'disponible')
    list_filter = ('disponible', 'categoria', StockAnomaloFilter) 
    search_fields = ('nombre', 'codigo_barras')
    
    # MODIFICADO: Agregamos el botón de IA a los campos de solo lectura
    readonly_fields = ('ver_buscador', 'boton_generar_ia')
    
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
            # MODIFICADO: Añadimos el botón a este bloque visual
            'fields': ('imagen', 'ver_buscador', 'boton_generar_ia', 'descripcion', 'dato_curioso'),
        }),
    )

    actions = [
        cambiar_categoria_masivo, 
        'generar_descripciones_masivas', # <--- NUEVA ACCIÓN MASIVA IA
        'ocultar_productos', 
        'mostrar_productos', 
        'resetear_descripcion', 
        'marcar_agotado', 
        'limpiar_images_seleccionadas'
    ]

    # --- LÓGICA DEL BOTÓN INDIVIDUAL ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/generar-ia/',
                self.admin_site.admin_view(self.generar_ia_individual_view),
                name='inventario_producto_generar_ia',
            ),
        ]
        return custom_urls + urls

    def generar_ia_individual_view(self, request, object_id):
        producto = self.get_object(request, object_id)
        if producto:
            exito, mensaje = llamar_gemini(producto)
            if exito:
                self.message_user(request, f"¡IA aplicada con éxito a: {producto.nombre}!", messages.SUCCESS)
            else:
                self.message_user(request, f"Info IA: {mensaje}", messages.WARNING)
        return redirect('admin:inventario_producto_change', object_id)

    @admin.display(description='🤖 Asistente IA')
    def boton_generar_ia(self, obj):
        if not obj.id: 
            return "Guarda el producto primero"
        url = reverse('admin:inventario_producto_generar_ia', args=[obj.id])
        return format_html('<a href="{}" style="background: #6f42c1; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-weight: bold;">✨ Auto-completar con Gemini</a>', url)

    # --- LÓGICA DE LA ACCIÓN MASIVA ---
    @admin.action(description="🤖 Generar descripciones con IA (Masivo)")
    def generar_descripciones_masivas(self, request, queryset):
        exitos = 0
        omitidos = 0
        for p in queryset:
            exito, _ = llamar_gemini(p)
            if exito:
                exitos += 1
            else:
                omitidos += 1
            # Pausa breve para cuidar la cuota de la API
            time.sleep(1.5)
        
        if exitos > 0:
            self.message_user(request, f"Se generaron descripciones para {exitos} productos.", messages.SUCCESS)
        if omitidos > 0:
            self.message_user(request, f"{omitidos} productos omitidos (ya tenían datos o hubo error).", messages.WARNING)

    # --- DISPLAYS ORIGINALES ---
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
    
    @admin.action(description="📝 Limpiar descripciones y datos")
    def resetear_descripcion(self, request, queryset): 
        queryset.update(descripcion="", dato_curioso="")
    
    @admin.action(description="🖼️ Limpiar imágenes")
    def limpiar_images_seleccionadas(self, request, queryset): queryset.update(imagen=None)


# ==============================================================================
# 4. PANEL SUGERENCIAS
# ==============================================================================
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


# ==============================================================================
# 5. CONFIGURACIÓN DEL SISTEMA
# ==============================================================================
@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'mostrar_ip_debug')
    
    def has_add_permission(self, request):
        if ConfiguracionSistema.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False


# ==============================================================================
# 6. IMPORTADOR DE EXCELS
# ==============================================================================
@admin.register(ImportacionExcel)
class ImportacionExcelAdmin(admin.ModelAdmin):
    list_display = ('fecha_subida', 'archivo')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            workbook = openpyxl.load_workbook(obj.archivo, data_only=True)
            sheet = workbook.active
            
            def limpiar_numero(valor):
                if valor is None or str(valor).strip() == "": return 0
                try:
                    limpio = str(valor).replace('$', '').replace('"', '').replace('“', '').replace('”', '').strip()
                    if ',' in limpio: limpio = limpio.split(',')[0]
                    limpio = limpio.replace('.', '')
                    return int(float(limpio))
                except (ValueError, TypeError):
                    return 0

            actualizados = 0
            creados = 0

            with transaction.atomic():
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    codigo_raw = row[0]
                    if codigo_raw is None: continue
                    
                    codigo_ext  = str(codigo_raw).split('.')[0].strip()
                    nombre_ext  = str(row[1]).strip() if row[1] else "Sin Nombre"
                    precio_ext  = limpiar_numero(row[3])
                    stock_ext   = limpiar_numero(row[5])
                    stk_min_ext = limpiar_numero(row[6])
                    depto_ext   = str(row[8]).strip() if row[8] else "General"

                    producto = Producto.objects.filter(codigo_barras=codigo_ext).first()

                    if producto:
                        producto.precio = precio_ext
                        producto.stock = stock_ext
                        producto.stock_minimo = stk_min_ext
                        producto.save()
                        actualizados += 1
                    else:
                        categoria_obj, _ = Categoria.objects.get_or_create(nombre=depto_ext)
                        Producto.objects.create(
                            codigo_barras=codigo_ext,
                            nombre=nombre_ext,
                            categoria=categoria_obj,
                            precio=precio_ext,
                            stock=stock_ext,
                            stock_minimo=stk_min_ext,
                            disponible=False 
                        )
                        creados += 1
            
            messages.success(request, f'🚀 ¡Importación exitosa! Actualizados: {actualizados} | Nuevos: {creados}.')
        except Exception as e:
            messages.error(request, f'Error fatal al leer el Excel: {str(e)}')