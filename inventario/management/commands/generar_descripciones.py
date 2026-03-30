import os
import time
import requests
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Producto
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Generación Market Tunka - IA Completa + Acceso Superusuario'

    def handle(self, *args, **options):
        # --- BLOQUE DE EMERGENCIA PARA ENTRAR AL ADMIN ---
        if not User.objects.filter(username="jefe_tunka").exists():
            User.objects.create_superuser("jefe_tunka", "admin@tunka.com", "Tunka2026!")
            self.stdout.write(self.style.SUCCESS("✅ NUEVO ACCESO CREADO: Usuario 'jefe_tunka' / Clave 'Tunka2026!'"))
        else:
            self.stdout.write(self.style.WARNING("ℹ️ El usuario 'jefe_tunka' ya existe."))
        # -----------------------------------------------

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Falta GEMINI_API_KEY"))
            return

        # Detección dinámica del modelo activo
        url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        modelo_detectado = "models/gemini-1.5-flash" 
        
        try:
            resp = requests.get(url_list)
            if resp.status_code == 200:
                modelos = resp.json().get('models', [])
                for m in modelos:
                    nombre = m.get('name')
                    if 'flash' in nombre.lower() and 'generateContent' in m.get('supportedGenerationMethods', []):
                        modelo_detectado = nombre
                        break
            self.stdout.write(self.style.SUCCESS(f"✅ Usando modelo: {modelo_detectado}"))
        except:
            self.stdout.write("⚠️ Usando modelo por defecto.")

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/{modelo_detectado}:generateContent"
        
        productos = Producto.objects.filter(
            Q(descripcion__isnull=True) | Q(descripcion="") |
            Q(dato_curioso__isnull=True) | Q(dato_curioso="")
        ).order_by('id')

        total = productos.count()
        self.stdout.write(f"🚀 Procesando {total} productos.")

        for p in productos:
            tiene_desc = bool(p.descripcion and p.descripcion.strip())
            tiene_dato = bool(p.dato_curioso and p.dato_curioso.strip())

            self.stdout.write(f"Procesando: {p.nombre}...")
            
            # --- TU PROMPT ORIGINAL COMPLETO ---
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

            try:
                response = requests.post(
                    endpoint, 
                    params={"key": api_key}, 
                    json={"contents": [{"parts": [{"text": prompt_text}]}]}, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    texto_ia = data['candidates'][0]['content']['parts'][0]['text']
                    
                    if "DATO:" in texto_ia:
                        partes = texto_ia.split("DATO:")
                        desc_limpia = partes[0].replace("DESCRIPCION:", "").strip()
                        dato_limpio = partes[1].replace("**", "").strip()
                        
                        if not tiene_desc: p.descripcion = desc_limpia
                        if not tiene_dato: p.dato_curioso = dato_limpio
                        
                        p.save()
                        self.stdout.write(self.style.SUCCESS(f"✅ OK: {p.nombre}"))
                elif response.status_code == 429:
                    self.stdout.write("⏳ Cuota alcanzada. Esperando 15s...")
                    time.sleep(15)
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Error {response.status_code}"))

            except Exception as e:
                self.stdout.write(f"❌ Error técnico: {e}")

            # Espera de 2 segundos para aprovechar la cuenta de pago
            time.sleep(2)