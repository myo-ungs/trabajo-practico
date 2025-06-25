import os
import sys
import csv
import numpy as np
from columns_solver_enhanced import Columns
from cargar_input import leer_input

def escribir_csv(metrica_dict, csv_path, modelos):
    with open(csv_path, 'w', newline='', encoding='cp1252') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Instancia", "Métrica", "Sección 5", "Col. iniciales", "Rankear", "Eliminar col."])
        metricas = [
            ("Restricciones", 'restricciones'),
            ("# variables inicial", 'variables'),
            ("# variables en últ. maestro", 'variables_final'),
            ("Cota dual", 'cota_dual'),
            ("Mejor objetivo", 'mejor_objetivo'),
        ]
        modelo_a_columna = {
            'modelo6': 2,
            'modelo7': 3,  # Asegurate que coincide con el que estás usando
        }
        for instancia, modelos_metricas in metrica_dict.items():
            first = True
            for nombre_metrica, clave in metricas:
                row = [instancia if first else '', nombre_metrica, '', '', '', '']
                for modelo in modelos:
                    m = modelos_metricas.get(modelo, {})
                    valor = m.get(clave, '')
                    col_idx = modelo_a_columna.get(modelo, None)
                    if col_idx is not None:
                        row[col_idx] = valor
                writer.writerow(row)
                first = False

# =========================
#   MAIN SCRIPT
# =========================

# Cargar datos desde archivo
archivo_input = "datos_de_entrada/A/instance_0001.txt"
W, S, LB, UB = leer_input(archivo_input)

# Instanciar y ejecutar
solver = Columns(W, S, LB, UB)
resultado = solver.Opt_ExplorarCantidadPasillos(16000)

if resultado:
    print("=== RESULTADO FINAL ===")
    print("Valor objetivo:", resultado["valor_objetivo"])
    print("Pasillos seleccionados:", resultado["pasillos_seleccionados"])
    print("Órdenes seleccionadas:", resultado["ordenes_seleccionadas"])
else:
    print("No se encontró solución con el umbral de tiempo dado.")

# Obtener nombre de instancia y dataset
nombre_dataset = os.path.basename(os.path.dirname(archivo_input))  # ej: "A"
nombre_instancia = os.path.splitext(os.path.basename(archivo_input))[0]  # ej: "instance_0001"

# Crear diccionario con métricas del resultado
metrica_dict = {
    nombre_instancia: {
        'modelo7': {  # Modelo evaluado
            'mejor_objetivo': resultado.get('valor_objetivo', ''),
            'pasillos_seleccionados': resultado.get('pasillos_seleccionados', ''),
            'ordenes_seleccionadas': resultado.get('ordenes_seleccionadas', ''),
            'cota_dual': resultado.get('cota_dual', ''),
            'restricciones': resultado.get('restricciones', 0),
            'variables': resultado.get('variables', 0),
            'variables_final': resultado.get('variables_final', 0),
        }
    }
}

# Crear carpeta de salida si no existe
output_dir = os.path.join("parte7", "OUTPUT", nombre_dataset)
os.makedirs(output_dir, exist_ok=True)

# Guardar archivo .out con resultados
output_path = os.path.join(output_dir, f"{nombre_instancia}.out")
with open(output_path, "w") as f:
    f.write(f"Mejor valor objetivo: {resultado['valor_objetivo']}\n")
    f.write("Órdenes seleccionadas:\n")
    f.write(" ".join(map(str, resultado["ordenes_seleccionadas"])) + "\n")
    f.write("Pasillos seleccionados:\n")
    f.write(" ".join(map(str, resultado["pasillos_seleccionados"])) + "\n")

# Guardar archivo .csv con métricas
csv_output_path = os.path.join(output_dir, "resumen_metricas.csv")
escribir_csv(metrica_dict, csv_output_path, modelos=['modelo7'])

print(f"\n✅ Resultados guardados en:\n- {output_path}\n- {csv_output_path}")
