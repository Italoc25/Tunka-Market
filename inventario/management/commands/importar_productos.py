import openpyxl
import os
from django.core.management.base import BaseCommand
from inventario.models import Producto, Categoria
from django.db import transaction

class Command(BaseCommand):
    help = 'Importa productos desde Excel protegiendo nombres y categorías existentes'

    def add_arguments(self, parser):
        parser.add_argument('archivo_excel', type=str)

    def limpiar_numero(self, valor):
        """Convierte precios y stock eliminando decimales sobrantes."""
        if valor is None or str(valor).strip() == "":
            return 0
        
        try:
            # 1. Lo pasamos a string y limpiamos símbolos de moneda o espacios
            limpio = (str(valor)
                      .replace('$', '')
                      .replace('"', '').replace('“', '').replace('”', '')
                      .strip())
            
            # 2. Manejo de Comas y Puntos (El truco para el 20,00)
            # Si hay una coma, asumimos que lo que sigue son decimales y lo cortamos.
            if ',' in limpio:
                limpio = limpio.split(',')[0]
            
            # 3. Quitar puntos de miles (si los hubiera)
            # Solo quitamos el punto si NO es un decimal (ej: 1.000 -> 1000)
            limpio = limpio.replace('.', '')

            # 4. Convertimos a float primero por si acaso y luego a int
            return int(float(limpio))
            
        except (ValueError, TypeError):
            return 0

    def handle(self, *args, **options):
        ruta = options['archivo_excel']
        
        if not os.path.exists(ruta):
            self.stdout.write(self.style.ERROR(f'El archivo "{ruta}" no existe.'))
            return

        try:
            workbook = openpyxl.load_workbook(ruta, data_only=True)
            sheet = workbook.active
            self.stdout.write(self.style.SUCCESS(f'Iniciando importación protegida: {ruta}'))

            # Usamos una transacción para que si algo falla, no quede la carga a medias
            with transaction.atomic():
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    codigo_raw = row[0]
                    if codigo_raw is None: 
                        continue
                    
                    # Limpieza básica de los datos del Excel
                    codigo_ext  = str(codigo_raw).split('.')[0].strip()
                    nombre_ext  = str(row[1]).strip() if row[1] else "Sin Nombre"
                    precio_ext  = self.limpiar_numero(row[3])
                    stock_ext   = self.limpiar_numero(row[5])
                    stk_min_ext = self.limpiar_numero(row[6])
                    depto_ext   = str(row[8]).strip() if row[8] else "General"

                    # 1. Buscamos o creamos la categoría que viene en el Excel
                    categoria_obj, _ = Categoria.objects.get_or_create(nombre=depto_ext)

                    # 2. Intentamos buscar el producto por su código de barras
                    producto, created = Producto.objects.get_or_create(
                        codigo_barras=codigo_ext,
                        defaults={
                            'nombre': nombre_ext,
                            'categoria': categoria_obj,
                            'precio': precio_ext,
                            'stock': stock_ext,
                            'stock_minimo': stk_min_ext,
                            'disponible': False #Para limpiar productos nuevos
                        }
                    )

                    if not created:
                        # SI EL PRODUCTO YA EXISTÍA: Solo actualizamos Precio y Stock
                        # El nombre y la categoría NO se tocan para proteger la limpieza manual.
                        producto.precio = precio_ext
                        producto.stock = stock_ext
                        producto.stock_minimo = stk_min_ext
                        producto.save()
                        self.stdout.write(f'Actualizado (Stock/Precio): {producto.nombre}')
                    else:
                        # SI EL PRODUCTO ES NUEVO: Ya se creó con los defaults de arriba
                        self.stdout.write(self.style.SUCCESS(f'Añadido nuevo: {nombre_ext}'))

            self.stdout.write(self.style.SUCCESS('--- Proceso finalizado con éxito ---'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fatal: {str(e)}'))