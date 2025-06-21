from columns_solver import Columns  
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input

# Cargar datos desde archivo
archivo_input = "datos_de_entrada/A/instance_0001.txt"
W, S, LB, UB = leer_input(archivo_input)

# Instanciar y ejecutar
solver = Columns(W, S, LB, UB)

resultado = solver.Opt_ExplorarCantidadPasillos(60)

print("\n=== RESULTADO FINAL ===")
print("Valor objetivo:", resultado["valor_objetivo"])
print("Pasillos seleccionados:", resultado["pasillos_seleccionados"])
print("Órdenes seleccionadas:", resultado["ordenes_seleccionadas"])


# === Guardar resultados en archivo .out ===

nombre_dataset = os.path.basename(os.path.dirname(archivo_input))  # A o B
nombre_instancia = os.path.splitext(os.path.basename(archivo_input))[0]  # instance_0001

output_dir = os.path.join("parte5", "OUTPUT", nombre_dataset)
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, f"{nombre_instancia}.out")

# Guardar resultados
with open(output_path, "w") as f:
    f.write(f"Mejor valor objetivo: {resultado['valor_objetivo']}\n")
    f.write("Órdenes seleccionadas:\n")
    f.write(" ".join(map(str, resultado["ordenes_seleccionadas"])) + "\n")
    f.write("Pasillos seleccionados:\n")
    f.write(" ".join(map(str, resultado["pasillos_seleccionados"])) + "\n")