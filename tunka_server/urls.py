# tunka_server/urls.py
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from inventario.views import buscador_productos, home, contacto, verificador_precios, api_buscar_producto, detalle_producto, autocomplete_productos, pedir_reposicion

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),                      
    path('productos/', buscador_productos, name='productos'), 
    path('producto/<int:pk>/', detalle_producto, name='detalle_producto'),
    path('contacto/', contacto, name='contacto'),
    path('verificador/', verificador_precios, name='verificador'),
    path('api/producto/<str:codigo>/', api_buscar_producto, name='api_buscar_producto'),
    path('autocomplete/', autocomplete_productos, name='autocomplete'),
    path('pedir-reposicion/<int:pk>/', pedir_reposicion, name='pedir_reposicion'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

try:
    # Esto crea al usuario 'admin' con clave 'Tunka2024!'
    User.objects.create_superuser('admin', 'admin@example.com', 'Tunka2024!')
    print("Superusuario 'admin' creado con éxito en Postgres")
except Exception as e:
    print(f"Error al crear superusuario: {e}")