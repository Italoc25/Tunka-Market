from django.shortcuts import render, get_object_or_404
from .models import Producto, Categoria, Sugerencia, ConfiguracionSistema
from django.db.models import Q
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.contrib import messages

# 1. El Buscador
def buscador_productos(request):
    query = request.GET.get('q', '')
    cat_id = request.GET.get('cat', '')
    
    productos_base = Producto.objects.filter(disponible=True)
    
    if query:
        resultados = productos_base.filter(nombre__icontains=query)
    elif cat_id:
        resultados = productos_base.filter(categoria_id=cat_id)
    else:
        resultados = productos_base.all()

    # Excluimos algunas categorias
    categorias_visibles = Categoria.objects.exclude(
        nombre__in=["- Sin Departamento -", "Pan granel"]
    )

    return render(request, 'inventario/buscador.html', {
        'resultados': resultados,
        'query': query,
        'cantidad': resultados.count(),
        'categorias': categorias_visibles, 
        'cat_activa': int(cat_id) if cat_id else None
    })

# 2. El Home
def home(request):
    return render(request, 'inventario/home.html')

# 3. Contacto / Buzón de Sugerencias
# He modificado esta vista para que procese el formulario del buzón
def contacto(request):
    if request.method == "POST":
        tipo = request.POST.get('tipo')
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        mensaje = request.POST.get('mensaje')
        imagen = request.FILES.get('imagen') # Captura la foto si existe

        if mensaje: # El mensaje es el único campo obligatorio
            Sugerencia.objects.create(
                tipo=tipo,
                nombre=nombre,
                email=email,
                mensaje=mensaje,
                imagen=imagen
            )
            messages.success(request, "¡Muchas gracias! Tu mensaje ha sido enviado al equipo de Tunka Market.")
            return HttpResponseRedirect(request.path)
            
    return render(request, 'inventario/contacto.html')

# 4. Verificador de Precios (Página)
def verificador_precios(request):
    # IPs autorizadas (Agregamos la nueva detectada por Railway)
    IPV4_TUNKA_TIENDA = "200.111.224.125"
    IPV4_TUNKA_RAILWAY = "186.10.141.46"  # <-- Tu IP nueva
    PREFIJO_IPV6_TUNKA = "2800:300:6b53:cbc0"

    # Obtener la IP real
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        user_ip = x_forwarded.split(',')[0].strip()
    else:
        user_ip = request.META.get('REMOTE_ADDR')

    # Obtenemos la configuración del admin (el interruptor)
    config = ConfiguracionSistema.objects.first()
    debug_activo = config.mostrar_ip_debug if config else False

    # VALIDACIÓN MEJORADA
    es_ip_valida = (
        user_ip == IPV4_TUNKA_TIENDA or 
        user_ip == IPV4_TUNKA_RAILWAY or 
        user_ip.startswith(PREFIJO_IPV6_TUNKA) or 
        user_ip in ['127.0.0.1', '::1']
    )
    
    # La llave maestra ?tienda=ok
    llave_maestra = request.GET.get('tienda') == 'ok'
    
    # Si entra por IP o por Llave, le damos acceso
    en_tienda = es_ip_valida or llave_maestra

    return render(request, 'inventario/verificador.html', {
        'en_tienda': en_tienda,
        'user_ip': user_ip,
        'debug_mode': debug_activo  # Enviamos el estado del switch al HTML
    })

# 5. API para el Verificador
def api_buscar_producto(request, codigo):
    try:
        producto = Producto.objects.get(codigo_barras=codigo, disponible=True)
        data = {
            'success': True,
            'nombre': producto.nombre,
            'precio': f"{producto.precio:,.0f}".replace(",", "."),
            'categoria': producto.categoria.nombre if producto.categoria else "General"
        }
    except Producto.DoesNotExist:
        data = {'success': False, 'message': 'Producto no encontrado'}
    return JsonResponse(data)

# 6. Detalle del Producto
def detalle_producto(request, pk):
    p = get_object_or_404(Producto, pk=pk)
    
    # Verificamos si ya existe la marca en la sesión
    session_key = f'voto_producto_{pk}'
    ya_voto = request.session.get(session_key, False)
    
    return render(request, 'inventario/detalle.html', {
        'p': p,
        'ya_voto': ya_voto 
    })

# 7. Buscador tipo google
def autocomplete_productos(request):
    query = request.GET.get('term', '') 
    productos = Producto.objects.filter(
        nombre__icontains=query, 
        disponible=True
    )[:10] 
    
    results = []
    for p in productos:
        results.append({
            'label': p.nombre, 
            'value': p.nombre, 
            'id': p.id        
        })
    return JsonResponse(results, safe=False)

# 8. "Quiero que vuelva"
def pedir_reposicion(request, pk):
    if request.method == "POST":
        nombre_sesion = f'voto_producto_{pk}'
        
        if request.session.get(nombre_sesion):
            return JsonResponse({
                'success': False, 
                'message': 'Ya registramos tu interés para este producto.'
            }, status=400)
        
        producto = get_object_or_404(Producto, pk=pk)
        producto.peticiones_volver += 1
        producto.save()
        
        request.session[nombre_sesion] = True
        
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)