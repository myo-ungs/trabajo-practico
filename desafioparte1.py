import pulp 
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum, LpBinary

# Parámetros de entrada

# cantidad de elementos por orden (orden x elemento)
W = [
    [1, 3, 0, 1, 1],
    [1, 1, 0, 0, 0],
    [2, 0, 0, 0, 0],
    [0, 0, 0, 2, 4],
    [3, 4, 1, 0, 0]
]

# cantidad de elementos por pasillo (pasillo x elemento)
S = [
    [2, 1, 2, 0, 1],
    [1, 3, 0, 2, 0],
    [2, 2, 0, 2, 3],
    [1, 1, 2, 3, 1],
    [0, 1, 2, 1, 1]
]

# Límite inferior y superior del tamaño de la wave
LB = 5
UB = 12

# Cantidad de pasillos a seleccionar
max_pasillos = 3  # ejemplo

#cantidades
n_ordenes = len(W)
n_elementos = len(W[0])
n_pasillos = len(S)


# Modelo 
modelo = LpProblem("WavePickingOptimization", LpMaximize)

# Variables
x = LpVariable.dicts("x", range(n_ordenes), cat="Binary")  # órdenes, vale 1 si se usa, 0 sino
y = LpVariable.dicts("y", range(n_pasillos), cat="Binary")  # pasillos, simil


# Función objetivo
# Maximizar la cantidad total de elementos recolectados dividido por pasillos usados
total_recolectado = lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos))
modelo += total_recolectado / max_pasillos, "MaximizeItemsPerAisle"

# Restricción 1: el total de unidades debe ser al menos LB
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) >= LB

# Restricción 2: el total de unidades sea como maximo UB
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) <= UB

# Restricción 3: disponibilidad por pasillo, por cada elemento i la cantidad total debe ser menor o igual
# a la suma de lo disponible en los pasillos seleccionados
for i in range(n_elementos):
    modelo += (
        lpSum(W[o][i] * x[o] for o in range(n_ordenes)) <=
        lpSum(S[a][i] * y[a] for a in range(n_pasillos))
    )

# Restricción 4: cantidad fija de pasillos
modelo += lpSum(y[a] for a in range(n_pasillos)) == max_pasillos

# Resolver modelo
modelo.solve()


# Resultados
print("Estado de solución:", LpStatus[modelo.status])
print("Órdenes seleccionadas (O'):", [o for o in range(n_ordenes) if x[o].varValue == 1])
print("Pasillos seleccionados (A'):", [a for a in range(n_pasillos) if y[a].varValue == 1])
print("Valor objetivo (elementos por pasillo):", pulp.value(modelo.objective))
