from basic_solver import Basic
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input

# Cargar datos W, S, LB, UB como hacías antes
archivo_input = "datos_de_entrada/input_ml.txt"
W, S, LB, UB = leer_input(archivo_input)

# Ejecutar parte 4
# Buscar mejor solución explorando distintas cantidades de pasillos en 60 segundos
basic = Basic(W, S, LB, UB)
resultado = basic.Opt_ExplorarCantidadPasillos(60)
print("Mejor valor objetivo:", resultado["valor_objetivo"])
print("Órdenes seleccionadas:", resultado["ordenes_seleccionadas"])
print("Pasillos seleccionados:", resultado["pasillos_seleccionados"])


# === Guardar resultados en archivo .out ===

nombre_dataset = os.path.basename(os.path.dirname(archivo_input))  # A o B
nombre_instancia = os.path.splitext(os.path.basename(archivo_input))[0]  # instance_0001

output_dir = os.path.join("parte4", "OUTPUT", nombre_dataset)
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, f"{nombre_instancia}.out")

# Guardar resultados
with open(output_path, "w") as f:
    f.write(f"Mejor valor objetivo: {resultado['valor_objetivo']}\n")
    f.write("Órdenes seleccionadas:\n")
    f.write(" ".join(map(str, resultado["ordenes_seleccionadas"])) + "\n")
    f.write("Pasillos seleccionados:\n")
    f.write(" ".join(map(str, resultado["pasillos_seleccionados"])) + "\n")

    