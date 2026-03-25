import os
import time
import google.generativeai as genai
from google.generativeai.types import RequestOptions # Requerido para el parche
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Producto

class Command(BaseCommand):
    help = 'Genera descripciones y datos curiosos usando Gemini (Google AI) con tus reglas'

    def handle(self, *args, **options):
        # CORRECCIÓN 1: Leer la variable de entorno correctamente
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        
        # CORRECCIÓN 2: Usar el nombre del modelo sin prefijos
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        productos_faltantes = Producto.objects.filter(
            Q(descripcion__isnull=True) | Q(descripcion="") |
            Q(dato_curioso__isnull=True) | Q(dato_curioso="")
        )

        total = productos_faltantes.count()
        self.stdout.write(f"Se encontraron {total} productos para trabajar con Gemini.")

        contador = 0
        for p in productos_faltantes: 
            contador += 1
            tiene_desc = bool(p.descripcion and p.descripcion.strip())
            tiene_dato = bool(p.dato_curioso and p.dato_curioso.strip())

            self.stdout.write(f"[{contador}/{total}] Buscando info real para: {p.nombre}...")
            
            prompt = f"""
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
                # CORRECCIÓN 3: Forzar la versión v1 para evitar el error 404
                response = model.generate_content(
                    prompt,
                    request_options=RequestOptions(api_version='v1')
                )
                texto = response.text
                
                if "DATO:" in texto:
                    partes = texto.split("DATO:")
                    desc_ia = partes[0].replace("DESCRIPCION:", "").strip()
                    dato_ia = partes[1].strip()
                    
                    if not tiene_desc:
                        p.descripcion = desc_ia
                    if not tiene_dato:
                        p.dato_curioso = dato_ia
                    
                    p.save()
                    self.stdout.write(self.style.SUCCESS(f"✅ [{contador}/{total}] ¡Éxito con {p.nombre}!"))
                else:
                    self.stdout.write(self.style.ERROR(f"Formato incorrecto en {p.nombre}"))

                time.sleep(4) 

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error en {p.nombre}: {e}"))
                time.sleep(10)