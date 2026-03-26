import os
import time
from google import genai
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Producto

class Command(BaseCommand):
    help = 'Generación de descripciones Market Tunka con API Key nueva'

    def handle(self, *args, **options):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Falta GEMINI_API_KEY en Railway"))
            return

        # Configuramos el cliente con la librería moderna
        client = genai.Client(api_key=api_key)
        
        # Usamos el nombre estándar que Google pide para la v1
        modelo_a_usar = 'gemini-1.5-flash'

        productos = Producto.objects.filter(
            Q(descripcion__isnull=True) | Q(descripcion="") |
            Q(dato_curioso__isnull=True) | Q(dato_curioso="")
        )

        total = productos.count()
        self.stdout.write(f"🚀 Iniciando con {total} productos usando {modelo_a_usar}...")

        contador = 0
        for p in productos:
            contador += 1
            tiene_desc = bool(p.descripcion and p.descripcion.strip())
            tiene_dato = bool(p.dato_curioso and p.dato_curioso.strip())

            self.stdout.write(f"[{contador}/{total}] Procesando: {p.nombre}...")
            
            # --- TU PROMPT ORIGINAL ---
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
                # Llamada directa
                response = client.models.generate_content(
                    model=modelo_a_usar,
                    contents=prompt
                )
                
                if response.text and "DATO:" in response.text:
                    partes = response.text.split("DATO:")
                    desc_ia = partes[0].replace("DESCRIPCION:", "").strip()
                    # Limpiamos posibles asteriscos o formato markdown que a veces pone la IA
                    dato_ia = partes[1].replace("**", "").strip()
                    
                    if not tiene_desc: p.descripcion = desc_ia
                    if not tiene_dato: p.dato_curioso = dato_ia
                    
                    p.save()
                    self.stdout.write(self.style.SUCCESS(f"✅ ¡Éxito con {p.nombre}!"))
                else:
                    self.stdout.write(self.style.ERROR(f"⚠️ Formato de respuesta no válido en {p.nombre}"))
                
                # Pausa de 5 segundos para no agotar la cuota gratuita
                time.sleep(5) 

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error en {p.nombre}: {e}"))
                # Si hay error de cuota, esperamos un poco más
                time.sleep(10)