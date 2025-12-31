from django.shortcuts import render
from .models import Producto
from django.db.models import Q

def buscador_precios(request):
    query = request.GET.get('q', '') # Captura lo que escriben en el cuadro de búsqueda
    resultados = None
    
    if query:
        # Filtra si el nombre contiene el texto O si el código contiene el texto
        resultados = Producto.objects.filter(
            Q(nombre__icontains=query) | Q(codigo_barras__icontains=query)
        )
    
    return render(request, 'inventario/buscador.html', {
        'resultados': resultados,
        'query': query
    })