from django.db import models

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=0)
    stock = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)
    codigo_barras = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True, help_text="Descripción detallada del producto")
    dato_curioso = models.TextField(blank=True, null=True, help_text="Un dato histórico o fun fact")
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    disponible = models.BooleanField(default=True, verbose_name="Visible en la web")
    peticiones_volver = models.PositiveIntegerField(default=0, verbose_name="Interesados en reponer")

    def __str__(self):
        return self.nombre

# --- MODELO PARA EL BUZÓN DE SUGERENCIAS ---
class Sugerencia(models.Model):
    TIPOS_OPCIONES = [
        ('PRODUCTO', 'Sugerencia de Producto'),
        ('CRITICA', 'Crítica/Mejora'),
        ('FELICITACION', 'Felicitación'),
        ('OTRO', 'Otro'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPOS_OPCIONES, default='PRODUCTO')
    nombre = models.CharField(max_length=100, blank=True, verbose_name="Nombre (Opcional)")
    email = models.EmailField(blank=True, verbose_name="Correo (Opcional)")
    mensaje = models.TextField(verbose_name="Mensaje")
    imagen = models.ImageField(upload_to='sugerencias/', blank=True, null=True, verbose_name="Imagen de referencia")
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Buzón de Sugerencias"

    def __str__(self):
        return f"{self.tipo} - {self.fecha_envio.strftime('%d/%m/%Y')}"