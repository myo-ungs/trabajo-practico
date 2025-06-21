import pulp 
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum, LpBinary
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input

# Leer datos desde archivo
archivo_input = "datos_de_entrada/A/instance_0001.txt"
W, S, LB, UB = leer_input(archivo_input)

# Cantidad de pasillos a seleccionar
max_pasillos = 2  # ejemplo

# Cantidades
n_ordenes = len(W)
n_elementos = len(W[0])
n_pasillos = len(S)

# Modelo 
modelo = LpProblem("WavePickingOptimization", LpMaximize)

# Variables
x = LpVariable.dicts("x", range(n_ordenes), cat="Binary") 
y = LpVariable.dicts("y", range(n_pasillos), cat="Binary")  

# Función objetivo
total_recolectado = lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos))
modelo += total_recolectado / max_pasillos, "MaximizeItemsPerAisle"

# Restricción 1: el total de unidades debe ser al menos LB
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) >= LB

# Restricción 2: el total de unidades sea como maximo UB
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) <= UB

# Restricción 3: disponibilidad por pasillo, por cada elemento i la cantidad total debe ser menor o igual a la suma de lo disponible en los pasillos seleccionados
for i in range(n_elementos):
    modelo += (
        lpSum(W[o][i] * x[o] for o in range(n_ordenes)) <=
        lpSum(S[a][i] * y[a] for a in range(n_pasillos))
    )

# Restricción 4: cantidad fija de pasillos
modelo += lpSum(y[a] for a in range(n_pasillos)) == max_pasillos

# Resolver modelo
modelo.solve()


# Función para verificar factibilidad
def es_factible(x_sol, y_sol, W, S, LB, UB, max_pasillos):
    n_ordenes = len(W)
    n_elementos = len(W[0])
    n_pasillos = len(S)

    # Total unidades seleccionadas
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

    # Verificar disponibilidad por elemento
    for i in range(n_elementos):
        cantidad_pedida = sum(W[o][i] * x_sol[o] for o in range(n_ordenes))
        cantidad_disponible = sum(S[a][i] * y_sol[a] for a in range(n_pasillos))
        if cantidad_pedida > cantidad_disponible:
            print(f"Falla en restricción disponibilidad para elemento {i}")
            return False

    # Verificar cantidad de pasillos seleccionados
    if sum(y_sol) != max_pasillos:
        print("Falla en restricción cantidad de pasillos seleccionados")
        return False

    return True


# Resultados
print("Estado de solución:", LpStatus[modelo.status])
print("Órdenes seleccionadas (O'):", [o for o in range(n_ordenes) if x[o].varValue == 1])
print("Pasillos seleccionados (A'):", [a for a in range(n_pasillos) if y[a].varValue == 1])
print("Valor objetivo (elementos por pasillo):", pulp.value(modelo.objective))


# Para probar la función de factibilidad 
x_sol = [int(x[o].varValue) for o in range(n_ordenes)]
y_sol = [int(y[a].varValue) for a in range(n_pasillos)]

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
    f.write(f"Valor objetivo: {pulp.value(modelo.objective):.2f}\n")
    f.write("Variables x (órdenes seleccionadas):\n")
    for o in range(n_ordenes):
        f.write(f"x[{o}] = {int(x[o].varValue)}\n")
    f.write("Variables y (pasillos seleccionados):\n")
    for a in range(n_pasillos):
        f.write(f"y[{a}] = {int(y[a].varValue)}\n")
