import os
from django.core.management.base import BaseCommand
from django.db.models import Q
from inventario.models import Producto
from openai import OpenAI

class Command(BaseCommand):
    help = 'Genera descripciones y datos curiosos usando IA'

    def handle(self, *args, **options):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Buscamos productos que no tengan descripción aún
        productos_faltantes = Producto.objects.filter(Q(descripcion__isnull=True) | Q(descripcion=""))

        self.stdout.write(f"Encontrados {productos_faltantes.count()} productos sin descripción.")

        
        for p in productos_faltantes: 
            self.stdout.write(f"Generando para: {p.nombre}...")
            
            prompt = f"""
            Eres el informante experto de 'Market Tunka'. Tu misión es generar fichas de producto útiles, variadas y breves. 
            
            PRODUCTO: {p.nombre}
            CATEGORÍA: {p.categoria.nombre if p.categoria else 'General'}

            REGLAS DE CONTENIDO:
            1. DESCRIPCIÓN (Máximo 25 palabras): 
               Define el producto o su uso principal de forma sobria. 
               - Si es un ingrediente, varía entre definir su origen, su función técnica o su perfil de sabor.
               - No repitas marca, peso o formato que ya esté en el título.

            2. DATO (Máximo 25 palabras): 
               Aquí debes VARIAR. Elige CUALQUIERA de estas opciones según lo que sea más interesante para este producto específico:
               - RECETA RÁPIDA: Si es ingrediente, enumera solo los componentes (ej: 'Para Panqueques: Harina, huevos y leche').
               - DIFERENCIA TÉCNICA: Explicar qué lo distingue (ej: 'La diferencia entre leche entera y descremada es...').
               - DATO HISTÓRICO O CURIOSO: Origen del producto o una marca icónica.
               - BENEFICIO O MARIDAJE: Beneficio de un ingrediente (ej: 'El plátano con leche aporta potasio y energía') o con qué combina mejor.
            
            3. REGLA DE GASEOSAS: 
               Si es una bebida y no especifica 'Zero/Sin Azúcar', menciona brevemente que es la fórmula clásica/original.

            4. NO REPETIR: Si ya mencionaste algo en la descripción, no lo repitas en el dato. Sé creativo para que cada ficha sea única.

            Responde estrictamente en este formato:
            DESCRIPCION: (Texto aquí)
            DATO: (Texto aquí)
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini", # AQUÍ ELEGIMOS EL MODELO
                messages=[{"role": "user", "content": prompt}]
            )

            texto = response.choices[0].message.content
            
            # Procesamos la respuesta (esto es un poco de "limpieza" de texto)
            try:
                partes = texto.split("DATO:")
                desc = partes[0].replace("DESCRIPCION:", "").strip()
                dato = partes[1].strip()
                
                # Guardamos en la base de datos
                p.descripcion = desc
                p.dato_curioso = dato
                p.save()
                
                self.stdout.write(self.style.SUCCESS(f"¡Éxito con {p.nombre}!"))
            except:
                self.stdout.write(self.style.ERROR(f"Error procesando {p.nombre}"))