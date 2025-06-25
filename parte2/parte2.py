from pyscipopt import Model, quicksum
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input

# Leer datos desde archivo
archivo_input = "datos_de_entrada/A/instance_0001.txt"

# Leer datos desde archivo
W, S, LB, UB = leer_input(archivo_input)

pasillos = [1, 3]  # pasillos seleccionados (ejemplo)

n_ordenes = len(W)
n_elementos = len(W[0])

# Crear modelo
modelo = Model("Desafio_A2")

# Variables binarias para órdenes
x = {}
for o in range(n_ordenes):
    x[o] = modelo.addVar(vtype="B", name=f"x_{o}")

# Función objetivo: maximizar total recolectado
total_recolectado = quicksum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos))
modelo.setObjective(total_recolectado, "maximize")

# Restricción 1: total unidades >= LB
modelo.addCons(total_recolectado >= LB, "LB")

# Restricción 2: total unidades <= UB
modelo.addCons(total_recolectado <= UB, "UB")

# Restricción 3: disponibilidad por elemento solo en pasillos seleccionados
for i in range(n_elementos):
    disponibilidad_total = sum(S[a][i] for a in pasillos)
    modelo.addCons(
        quicksum(W[o][i] * x[o] for o in range(n_ordenes)) <= disponibilidad_total,
        name=f"disponibilidad_elem_{i}"
    )

# Optimizar modelo
modelo.optimize()

# Estado de la solución
status = modelo.getStatus()
print("Estado de solución:", status)

if status == "optimal" or status == "optimal_inaccurate":
    x_sol = [int(modelo.getVal(x[o])) for o in range(n_ordenes)]

    print("Órdenes seleccionadas (O'):", [o for o in range(n_ordenes) if x_sol[o] == 1])
    print("Unidades recolectadas:", modelo.getObjVal())
else:
    print("No se encontró solución óptima.")


# === Guardar resultados en archivo .out ===

nombre_dataset = os.path.basename(os.path.dirname(archivo_input))  # A o B
nombre_instancia = os.path.splitext(os.path.basename(archivo_input))[0]  # instance_uvxy

# Crear carpeta de salida
output_dir = os.path.join("parte2", "OUTPUT", nombre_dataset)
os.makedirs(output_dir, exist_ok=True)

# Nombre del archivo de salida
output_path = os.path.join(output_dir, f"{nombre_instancia}.out")

with open(output_path, "w") as f:
    f.write(f"{status}\n")
    if status == "optimal":
        f.write(f"{int(modelo.getObjVal())}\n")
        ordenes_seleccionadas = [str(o) for o in range(n_ordenes) if modelo.getVal(x[o]) > 0.5]
        f.write(" ".join(ordenes_seleccionadas) + "\n")
    else:
        f.write("No se encontró solución óptima.")
    
