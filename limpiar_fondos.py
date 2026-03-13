import os
from rembg import remove
from PIL import Image
import io

# Configuración de carpetas
input_dir = 'media/productos/'
# Opcional: puedes guardarlas en la misma carpeta o en una nueva
output_dir = 'media/productos_limpios/' 

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("Iniciando la limpieza de fondos... esto puede tardar un poco por cada foto.")

for filename in os.listdir(input_dir):
    if filename.endswith(('.png', '.jpg', '.jpeg')):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename.split('.')[0] + '.png') # Mejor guardar como PNG para transparencia

        if os.path.exists(output_path):
            continue

        print(f"Procesando: {filename}...")

        try:
            with open(input_path, 'rb') as i:
                input_image = i.read()
                # LA MAGIA: Quita el fondo
                output_image = remove(input_image)
                
                # Convertir a imagen de fondo blanco (opcional)
                # Si quieres que el fondo sea BLANCO y no transparente:
                img = Image.open(io.BytesIO(output_image)).convert("RGBA")
                white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                final_img = Image.alpha_composite(white_bg, img).convert("RGB")
                
                final_img.save(output_path, "JPEG", quality=90)
                
            print(f"  [✓] {filename} limpiada.")
        except Exception as e:
            print(f"  [X] Error en {filename}: {e}")

print("¡Listo! Revisa la carpeta media/productos_limpios/")