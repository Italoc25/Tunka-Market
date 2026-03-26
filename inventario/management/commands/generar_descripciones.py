import os
import time
import requests
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Producto

class Command(BaseCommand):
    help = 'Generación Estable Market Tunka - Modo Tortuga para Cuota Gratuita'

    def handle(self, *args, **options):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Falta GEMINI_API_KEY"))
            return

        # Ya sabemos que tu modelo es gemini-2.5-flash
        modelo_a_usar = "models/gemini-2.5-flash"
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/{modelo_a_usar}:generateContent"
        
        productos = Producto.objects.filter(
            Q(descripcion__isnull=True) | Q(descripcion="") |
            Q(dato_curioso__isnull=True) | Q(dato_curioso="")
        )

        total = productos.count()
        self.stdout.write(self.style.SUCCESS(f"🐢 Modo Tortuga con {modelo_a_usar}. Quedan {total} productos."))

        for p in productos:
            tiene_desc = bool(p.descripcion and p.descripcion.strip())
            tiene_dato = bool(p.dato_curioso and p.dato_curioso.strip())

            self.stdout.write(f"Procesando: {p.nombre}...")
            
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

            reintentar = True
            while reintentar:
                try:
                    response = requests.post(
                        endpoint, 
                        params={"key": api_key}, 
                        json={"contents": [{"parts": [{"text": prompt_text}]}]}, 
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        texto_ia = response.json()['candidates'][0]['content']['parts'][0]['text']
                        if "DATO:" in texto_ia:
                            partes = texto_ia.split("DATO:")
                            desc_ia = partes[0].replace("DESCRIPCION:", "").strip()
                            dato_ia = partes[1].replace("**", "").strip()
                            
                            if not tiene_desc: p.descripcion = desc_ia
                            if not tiene_dato: p.dato_curioso = dato_ia
                            
                            p.save()
                            self.stdout.write(self.style.SUCCESS(f"✅ Éxito con {p.nombre}"))
                            reintentar = False
                    elif response.status_code == 429:
                        self.stdout.write("⏳ Cuota agotada. Esperando 60 segundos para liberar...")
                        time.sleep(60)
                    elif response.status_code == 503:
                        self.stdout.write("⏳ Google saturado. Esperando 30 segundos...")
                        time.sleep(30)
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ Error {response.status_code} en {p.nombre}. Saltando..."))
                        reintentar = False
                except Exception as e:
                    self.stdout.write(f"❌ Error técnico: {e}")
                    reintentar = False

            # Pausa de 25 segundos SIEMPRE entre productos exitosos
            time.sleep(25)