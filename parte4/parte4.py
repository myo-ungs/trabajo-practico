from basic_solver import Basic
import os
import sys

# Obtener directorio raíz del proyecto
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.append(project_root)

from cargar_input import leer_input
from guardar_output import guardar_resultado

# Cargar datos W, S, LB, UB como hacías antes
archivo_input = os.path.join(project_root, "datos_de_entrada/B/instance_0001.txt")
W, S, LB, UB = leer_input(archivo_input)

# Ejecutar parte 4
# Buscar mejor solución explorando distintas cantidades de pasillos en x segundos
basic = Basic(W, S, LB, UB)
resultado = basic.Opt_ExplorarCantidadPasillos(600)

if resultado is None:
    print("No se encontro ninguna solucion factible.")
    resultado = {
        "valor_objetivo": 0,
        "ordenes_seleccionadas": [],
        "pasillos_seleccionados": []
    }
else:
    print("Mejor valor objetivo:", resultado["valor_objetivo"])
    print("Ordenes seleccionadas:", resultado["ordenes_seleccionadas"])
    print("Pasillos seleccionados:", resultado["pasillos_seleccionados"])


# === Guardar resultados en archivo .out ===

guardar_resultado(
    archivo_input=archivo_input,
    parte="parte4",  
    resultado={
        "valor_objetivo": resultado["valor_objetivo"],
        "ordenes_seleccionadas": list(resultado["ordenes_seleccionadas"]),
        "pasillos_seleccionados": list(resultado["pasillos_seleccionados"])
    }
)