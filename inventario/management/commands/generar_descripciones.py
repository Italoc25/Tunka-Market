import os
import time
import requests
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Producto

class Command(BaseCommand):
    help = 'Auto-Detección de Modelo y Generación - Market Tunka'

    def handle(self, *args, **options):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Falta GEMINI_API_KEY"))
            return

        # 1. PREGUNTARLE A GOOGLE QUÉ MODELOS EXISTEN
        self.stdout.write("🔍 Consultando a Google qué modelos están disponibles para tu llave...")
        url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        
        modelo_a_usar = None
        try:
            resp = requests.get(url_list)
            if resp.status_code == 200:
                modelos = resp.json().get('models', [])
                for m in modelos:
                    # Buscamos uno que permita generar texto
                    if 'generateContent' in m.get('supportedGenerationMethods', []):
                        nombre = m.get('name') # Ej: "models/gemini-1.5-flash"
                        # Si tiene la palabra flash, lo priorizamos
                        if 'flash' in nombre.lower():
                            modelo_a_usar = nombre
                            break
                        # Si no, guardamos el primero que aparezca
                        if not modelo_a_usar:
                            modelo_a_usar = nombre
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error al consultar modelos: {resp.json()}"))
                return
            
            if not modelo_a_usar:
                self.stdout.write(self.style.ERROR("❌ Tu API Key no tiene modelos de texto habilitados."))
                return
            
            self.stdout.write(self.style.SUCCESS(f"✅ ¡Modelo detectado! Usaremos la URL exacta: {modelo_a_usar}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error de conexión: {e}"))
            return

        # 2. CONSTRUIR LA URL CON EL MODELO EXACTO QUE GOOGLE NOS DIO
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/{modelo_a_usar}:generateContent"
        
        productos_faltantes = Producto.objects.filter(
            Q(descripcion__isnull=True) | Q(descripcion="") |
            Q(dato_curioso__isnull=True) | Q(dato_curioso="")
        )

        total = productos_faltantes.count()
        self.stdout.write(f"🚀 Iniciando procesamiento para {total} productos.")

        contador = 0
        for p in productos_faltantes: 
            contador += 1
            tiene_desc = bool(p.descripcion and p.descripcion.strip())
            tiene_dato = bool(p.dato_curioso and p.dato_curioso.strip())

            self.stdout.write(f"[{contador}/{total}] Procesando: {p.nombre}...")
            
            # --- TU PROMPT ORIGINAL INTEGRO ---
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

            payload = {
                "contents": [{
                    "parts": [{"text": prompt_text}]
                }]
            }

            try:
                response = requests.post(
                    endpoint, 
                    params={"key": api_key},
                    json=payload, 
                    timeout=30
                )
                data = response.json()

                if response.status_code == 200:
                    texto_ia = data['candidates'][0]['content']['parts'][0]['text']
                    
                    if "DATO:" in texto_ia:
                        partes = texto_ia.split("DATO:")
                        desc_ia = partes[0].replace("DESCRIPCION:", "").strip()
                        dato_ia = partes[1].replace("**", "").strip()
                        
                        if not tiene_desc: p.descripcion = desc_ia
                        if not tiene_dato: p.dato_curioso = dato_ia
                        
                        p.save()
                        self.stdout.write(self.style.SUCCESS(f"✅ ¡Éxito con {p.nombre}!"))
                    else:
                        self.stdout.write(self.style.ERROR(f"⚠️ Formato inesperado"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Error API ({response.status_code}): {data.get('error', {}).get('message')}"))
                
                time.sleep(5) 

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error en {p.nombre}: {e}"))
                time.sleep(10)