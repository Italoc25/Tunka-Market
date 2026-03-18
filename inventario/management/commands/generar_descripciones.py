import os
import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Producto
from openai import OpenAI

class Command(BaseCommand):
    help = 'Genera descripciones y datos curiosos usando IA (Universal con contador)'

    def handle(self, *args, **options):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Filtro general: entra cualquier producto con al menos un campo vacío
        productos_faltantes = Producto.objects.filter(
            Q(descripcion__isnull=True) | Q(descripcion="") |
            Q(dato_curioso__isnull=True) | Q(dato_curioso="")
        )

        total = productos_faltantes.count()
        self.stdout.write(f"Se encontraron {total} productos para trabajar.")

        contador = 0
        for p in productos_faltantes: 
            contador += 1
            # Detectamos qué tenemos ya en la base de datos
            tiene_desc = bool(p.descripcion and p.descripcion.strip())
            tiene_dato = bool(p.dato_curioso and p.dato_curioso.strip())

            self.stdout.write(f"[{contador}/{total}] Generando para: {p.nombre}...")
            
            prompt = f"""
            Eres el informante experto de 'Market Tunka'. Tu misión es generar fichas de producto útiles, variadas y breves. 
            
            PRODUCTO: {p.nombre}
            CATEGORÍA: {p.categoria.nombre if p.categoria else 'General'}

            ESTADO ACTUAL:
            - DESCRIPCIÓN: {p.descripcion if tiene_desc else "VACÍO"}
            - DATO CURIOSO: {p.dato_curioso if tiene_dato else "VACÍO"}

            REGLAS DE CONTENIDO (APLICAR SOLO A LO QUE ESTÉ 'VACÍO'):
            1. DESCRIPCIÓN (Máximo 25 palabras): 
                Define el producto o su uso principal de forma sobria. 
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

            4. NO REPETIR: Si ya hay una descripción (manual o generada), no repitas esa info en el dato.

            IMPORTANTE: Si un campo NO está 'VACÍO', devuélvelo exactamente como está.
            Responde estrictamente en este formato:
            DESCRIPCION: (Texto aquí)
            DATO: (Texto aquí)
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )

                texto = response.choices[0].message.content
                partes = texto.split("DATO:")
                desc_ia = partes[0].replace("DESCRIPCION:", "").strip()
                dato_ia = partes[1].strip()
                
                if not tiene_desc:
                    p.descripcion = desc_ia
                if not tiene_dato:
                    p.dato_curioso = dato_ia
                
                p.save()
                self.stdout.write(self.style.SUCCESS(f"[{contador}/{total}] ¡Éxito con {p.nombre}!"))
                
                # Pausa mínima para estabilidad de la API
                time.sleep(0.3) 

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error en {p.nombre}: {e}"))