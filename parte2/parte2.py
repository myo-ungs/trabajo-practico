import pulp 
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum, LpBinary
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input

# Leer datos desde archivo
archivo_input = "datos_de_entrada/A/instance_0001.txt"
W, S, LB, UB = leer_input(archivo_input)

# Seleccion de pasillos
pasillos = [1,3]  # ejemplo

# Cantidades
n_ordenes = len(W)
n_elementos = len(W[0])

# Modelo 
modelo = LpProblem("Desafio_A2", LpMaximize)

# Variables
x = LpVariable.dicts("x", range(n_ordenes), cat="Binary") 

# Función objetivo
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)), "TotalRecolectado"

# Restricción 1: el total de unidades debe ser al menos LB
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) >= LB

# Restricción 2: el total de unidades sea como maximo UB
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) <= UB

# Restricción 3: disponibilidad por pasillo, por cada elemento i la cantidad total debe ser menor o igual a la suma de lo disponible en los pasillos seleccionados
for i in range(n_elementos):
    disponibilidad_total = sum(S[a][i] for a in pasillos)
    modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes)) <= disponibilidad_total

# Resolver modelo
modelo.solve()


# Resultados
print("Estado de solución:", LpStatus[modelo.status])
print("Órdenes seleccionadas (O'):", [o for o in range(n_ordenes) if x[o].varValue == 1])
print("Unidades recolectadas:", pulp.value(modelo.objective))


# === Guardar resultados en archivo .out ===

nombre_dataset = os.path.basename(os.path.dirname(archivo_input))  # A o B
nombre_instancia = os.path.splitext(os.path.basename(archivo_input))[0]  # instance_uvxy

# Crear carpeta de salida
output_dir = os.path.join("parte2", "OUTPUT", nombre_dataset)
os.makedirs(output_dir, exist_ok=True)

# Nombre del archivo de salida
output_path = os.path.join(output_dir, f"{nombre_instancia}.out")

with open(output_path, "w") as f:
    f.write(f"{LpStatus[modelo.status]}\n")
    f.write(f"{int(pulp.value(modelo.objective))}\n")
    ordenes_seleccionadas = [str(o) for o in range(n_ordenes) if x[o].varValue == 1]
    f.write(" ".join(ordenes_seleccionadas) + "\n")
