import openpyxl
from django.core.management.base import BaseCommand
from inventario.models import Producto, Categoria

class Command(BaseCommand):
    help = 'Importa productos desde un Excel limpiando simbolos de moneda'

    def add_arguments(self, parser):
        parser.add_argument('archivo_excel', type=str)

    # --- AQUÍ AGREGAMOS LA FUNCIÓN DE LIMPIEZA ---
    def limpiar_numero(self, valor):
        """Convierte '$800' o '1.500' en el número entero 800 o 1500."""
        if valor is None or str(valor).strip() == "":
            return 0
        try:
            # Convertimos a texto y quitamos todo lo que no sea número
            # Eliminamos $, comillas, puntos de miles y espacios
            limpio = (str(valor)
                      .replace('$', '')
                      .replace('“', '')
                      .replace('”', '')
                      .replace('"', '')
                      .replace('.', '') 
                      .replace(',', '')
                      .strip())
            return int(float(limpio))
        except (ValueError, TypeError):
            return 0

    def handle(self, *args, **options):
        ruta = options['archivo_excel']
        try:
            # data_only=True es vital para leer el resultado de fórmulas
            workbook = openpyxl.load_workbook(ruta, data_only=True)
            sheet = workbook.active
            
            self.stdout.write(self.style.SUCCESS(f'Iniciando importación: {ruta}'))

            for row in sheet.iter_rows(min_row=2, values_only=True):
                # Ajustamos los índices según tu Excel:
                # 0:Código, 1:Producto, 3:P.Venta, 5:Existencia, 6:Inv.Min, 8:Depto
                codigo_raw = row[0]
                if codigo_raw is None: continue
                
                codigo_ext  = str(codigo_raw).split('.')[0].strip()
                nombre_ext  = str(row[1]).strip() if row[1] else "Sin Nombre"
                
                # USAMOS LA NUEVA FUNCIÓN AQUÍ
                precio_ext  = self.limpiar_numero(row[3])
                stock_ext   = self.limpiar_numero(row[5])
                stk_min_ext = self.limpiar_numero(row[6])
                depto_ext   = str(row[8]).strip() if row[8] else "General"

                # 1. Manejo de Categoría
                categoria_obj, _ = Categoria.objects.get_or_create(nombre=depto_ext)

                # 2. Crear o Actualizar
                obj, created = Producto.objects.update_or_create(
                    codigo_barras=codigo_ext,
                    defaults={
                        'nombre': nombre_ext,
                        'precio': precio_ext,
                        'stock': stock_ext,
                        'stock_minimo': stk_min_ext,
                        'categoria': categoria_obj,
                    }
                )
                
                status = "Añadido" if created else "Actualizado"
                self.stdout.write(f'{status}: {nombre_ext}')

            self.stdout.write(self.style.SUCCESS('¡Importación finalizada con éxito!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fatal: {str(e)}'))