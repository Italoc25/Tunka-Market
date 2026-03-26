import os
import time
from google import genai
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Producto

class Command(BaseCommand):
    help = 'Genera descripciones con el prompt original y auto-corrección de modelo'

    def handle(self, *args, **options):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Falta GEMINI_API_KEY"))
            return

        # Forzamos v1 para evitar errores de beta
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
        
        # Lista de nombres técnicos que Google acepta para este modelo
        nombres_modelo = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
        modelo_actual = nombres_modelo[0]

        productos_faltantes = Producto.objects.filter(
            Q(descripcion__isnull=True) | Q(descripcion="") |
            Q(dato_curioso__isnull=True) | Q(dato_curioso="")
        )

        total = productos_faltantes.count()
        self.stdout.write(f"🚀 Iniciando proceso para {total} productos con {modelo_actual}...")

        contador = 0
        for p in productos_faltantes:
            contador += 1
            tiene_desc = bool(p.descripcion and p.descripcion.strip())
            tiene_dato = bool(p.dato_curioso and p.dato_curioso.strip())

            self.stdout.write(f"[{contador}/{total}] Buscando para: {p.nombre}...")
            
            # --- TU PROMPT ORIGINAL INTEGRO ---
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

            exito = False
            indice_modelo = 0
            
            while not exito and indice_modelo < len(nombres_modelo):
                try:
                    response = client.models.generate_content(
                        model=modelo_actual,
                        contents=prompt
                    )
                    
                    texto = response.text
                    if "DATO:" in texto:
                        partes = texto.split("DATO:")
                        desc_ia = partes[0].replace("DESCRIPCION:", "").strip()
                        dato_ia = partes[1].strip()
                        
                        if not tiene_desc: p.descripcion = desc_ia
                        if not tiene_dato: p.dato_curioso = dato_ia
                        
                        p.save()
                        self.stdout.write(self.style.SUCCESS(f"✅ Éxito con {p.nombre}"))
                        exito = True
                    
                    time.sleep(5)

                except Exception as e:
                    # Si el error es 404 (modelo no encontrado), probamos el siguiente nombre de la lista
                    if "404" in str(e) and indice_modelo < len(nombres_modelo) - 1:
                        indice_modelo += 1
                        modelo_old = modelo_actual
                        modelo_actual = nombres_modelo[indice_modelo]
                        self.stdout.write(f"⚠️ {modelo_old} falló (404), intentando con {modelo_actual}...")
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ Error en {p.nombre}: {e}"))
                        break # Salta al siguiente producto si ya probamos todo o es otro error