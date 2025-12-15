from basic_solver import Basic
import os
import sys
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input
from guardar_output import guardar_resultado

# Cargar datos W, S, LB, UB como hacías antes
archivo_input = "datos_de_entrada/B/instance_0001.txt"
W, S, LB, UB = leer_input(archivo_input)

# Ejecutar parte 4
# Buscar mejor solución explorando distintas cantidades de pasillos en x segundos
basic = Basic(W, S, LB, UB)
start = time.time()
resultado = basic.Opt_ExplorarCantidadPasillos(600)
end = time.time()
print(f"Tiempo total de ejecución: {end - start:.0f} segundos")

if resultado is None:
    print("No se encontró ninguna solución factible dentro del tiempo límite.")
    guardar_resultado(
        archivo_input=archivo_input,
        parte="parte4",
        resultado={
            "valor_objetivo": None,
            "ordenes_seleccionadas": [],
            "pasillos_seleccionados": []
        }
    )
else:
    print("Mejor valor objetivo:", resultado["valor_objetivo"])
    print("Órdenes seleccionadas:", resultado["ordenes_seleccionadas"])
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