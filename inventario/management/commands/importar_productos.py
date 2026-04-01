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
            limpio = (str(valor)
                      .replace('$', '')
                      .replace('"', '').replace('“', '').replace('”', '')
                      .strip())
            if ',' in limpio:
                limpio = limpio.split(',')[0]
            limpio = limpio.replace('.', '')
            return int(float(limpio))
        except (ValueError, TypeError):
            return 0

    # IMPORTANTE: Esta función DEBE estar indentada (con espacios a la derecha)
    def handle(self, *args, **options):
        ruta = options['archivo_excel']
        
        if not os.path.exists(ruta):
            self.stdout.write(self.style.ERROR(f'El archivo "{ruta}" no existe.'))
            return

        try:
            workbook = openpyxl.load_workbook(ruta, data_only=True)
            sheet = workbook.active
            self.stdout.write(self.style.SUCCESS(f'🚀 Iniciando importación: Protegiendo Nombres y Categorías'))

            with transaction.atomic():
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    codigo_raw = row[0]
                    if codigo_raw is None: continue
                    
                    codigo_ext  = str(codigo_raw).split('.')[0].strip()
                    nombre_ext  = str(row[1]).strip() if row[1] else "Sin Nombre"
                    precio_ext  = self.limpiar_numero(row[3])
                    stock_ext   = self.limpiar_numero(row[5])
                    stk_min_ext = self.limpiar_numero(row[6])
                    depto_ext   = str(row[8]).strip() if row[8] else "General"

                    producto = Producto.objects.filter(codigo_barras=codigo_ext).first()

                    if producto:
                        # EXISTENTE: Solo actualizamos números
                        producto.precio = precio_ext
                        producto.stock = stock_ext
                        producto.stock_minimo = stk_min_ext
                        producto.save()
                        self.stdout.write(f'✅ Actualizado (Precio/Stock): {producto.nombre}')
                    
                    else:
                        # NUEVO: Usamos datos del Excel
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
                        self.stdout.write(self.style.SUCCESS(f'➕ Añadido nuevo: {nombre_ext}'))

            self.stdout.write(self.style.SUCCESS('--- Proceso terminado con éxito ---'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fatal: {str(e)}'))