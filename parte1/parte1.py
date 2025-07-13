from pyscipopt import Model, quicksum
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input

# Leer datos desde archivo
archivo_input = "datos_de_entrada/A/instance_0001.txt"
# Leer datos desde archivo
W, S, LB, UB = leer_input(archivo_input)

max_pasillos = 2  # ejemplo

n_ordenes = len(W)
n_elementos = len(W[0])
n_pasillos = len(S)

# Crear modelo
modelo = Model("OptimizaciónWavePicking")

# Variables binarias para órdenes
x = {}
for o in range(n_ordenes):
    x[o] = modelo.addVar(vtype="B", name=f"x_{o}")

# Variables binarias para pasillos
y = {}
for a in range(n_pasillos):
    y[a] = modelo.addVar(vtype="B", name=f"y_{a}")

# Función objetivo: maximizar total_recolectado / max_pasillos
total_recolectado = quicksum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos))
modelo.setObjective(total_recolectado / max_pasillos, "maximize")

# Restricción 1: total unidades >= LB
modelo.addCons(quicksum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) >= LB, "LB")

# Restricción 2: total unidades <= UB
modelo.addCons(quicksum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) <= UB, "UB")

# Restricción 3: disponibilidad por elemento
for i in range(n_elementos):
    modelo.addCons(
        quicksum(W[o][i] * x[o] for o in range(n_ordenes)) <=
        quicksum(S[a][i] * y[a] for a in range(n_pasillos)),
        name=f"disponibilidad_elem_{i}"
    )

# Restricción 4: cantidad fija de pasillos seleccionados
modelo.addCons(quicksum(y[a] for a in range(n_pasillos)) == max_pasillos, "cantidad_pasillos")

# Optimizar modelo
modelo.optimize()

# Obtener solución
status = modelo.getStatus()
print("Estado de solución:", status)

if status == "optimal" or status == "optimal_inaccurate":
    x_sol = [int(modelo.getVal(x[o])) for o in range(n_ordenes)]
    y_sol = [int(modelo.getVal(y[a])) for a in range(n_pasillos)]

    print("Órdenes seleccionadas (O'):", [o for o in range(n_ordenes) if x_sol[o] == 1])
    print("Pasillos seleccionados (A'):", [a for a in range(n_pasillos) if y_sol[a] == 1])
    print("Valor objetivo (items por pasillo):", modelo.getObjVal())

else:
    print("No se encontró solución óptima.")


# Función para verificar factibilidad (igual que antes)
def es_factible(x_sol, y_sol, W, S, LB, UB, max_pasillos):
    n_ordenes = len(W)
    n_elementos = len(W[0])
    n_pasillos = len(S)

    total_unidades = 0
    for o in range(n_ordenes):
        if x_sol[o] == 1:
            total_unidades += sum(W[o][i] for i in range(n_elementos))

    if total_unidades < LB:
        print("Falla en restricción LB")
        return False
    if total_unidades > UB:
        print("Falla en restricción UB")
        return False

    for i in range(n_elementos):
        cantidad_pedida = sum(W[o][i] * x_sol[o] for o in range(n_ordenes))
        cantidad_disponible = sum(S[a][i] * y_sol[a] for a in range(n_pasillos))
        if cantidad_pedida > cantidad_disponible:
            print(f"Falla en restricción disponibilidad para elemento {i}")
            return False

    if sum(y_sol) != max_pasillos:
        print("Falla en restricción cantidad de pasillos seleccionados")
        return False

    return True


# Validar factibilidad
if status == "optimal" or status == "optimal_inaccurate":
    if es_factible(x_sol, y_sol, W, S, LB, UB, max_pasillos):
        print("La solución es factible.")
    else:
        print("La solución NO es factible.")

# === Guardar resultados en archivo .out ===

nombre_dataset = os.path.basename(os.path.dirname(archivo_input))  # A o B
nombre_instancia = os.path.splitext(os.path.basename(archivo_input))[0]  # instance_uvxy

# Crear carpeta de salida
output_dir = os.path.join("parte1", "OUTPUT", nombre_dataset)
os.makedirs(output_dir, exist_ok=True)

# Nombre del archivo de salida
output_path = os.path.join(output_dir, f"{nombre_instancia}.out")

# Guardar contenido
with open(output_path, "w") as f:
    if status == "optimal" or status == "optimal_inaccurate":
        f.write(f"Valor objetivo: {modelo.getObjVal():.2f}\n")
        f.write("Variables x (órdenes seleccionadas):\n")
        for o in range(n_ordenes):
            f.write(f"x[{o}] = {int(modelo.getVal(x[o]))}\n")
        f.write("Variables y (pasillos seleccionados):\n")
        for a in range(n_pasillos):
            f.write(f"y[{a}] = {int(modelo.getVal(y[a]))}\n")
    else:
        f.write("No se encontró solución óptima.\n")
