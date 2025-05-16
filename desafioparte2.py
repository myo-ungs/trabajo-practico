import pulp 
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum, LpBinary

# Parámetros de entrada

# cantidad de elementos por orden (orden x elemento)
W = [
    [3, 0, 1, 0, 0],
    [0, 1, 0, 1, 0],
    [0, 0, 1, 0, 2],
    [1, 0, 2, 1, 1],
    [0, 1, 0, 0, 0]
]

# cantidad de elementos por pasillo (pasillo x elemento)
S = [
    [2, 1, 1, 0, 1],
    [2, 1, 2, 0, 1],
    [0, 2, 0, 1, 2],
    [2, 1, 0, 1, 1],
    [0, 1, 2, 1, 2]
]

# Límite inferior y superior del tamaño de la wave
LB = 5
UB = 12

# Seleccion de pasillos
pasillos = [1,3]  # ejemplo

#cantidades
n_ordenes = len(W)
n_elementos = len(W[0])



# Modelo 
modelo = LpProblem("Desafio_A2", LpMaximize)

# Variables
x = LpVariable.dicts("x", range(n_ordenes), cat="Binary")  # órdenes, vale 1 si se usa, 0 sino


# Función objetivo
# maximizar unidades recolectadas 
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)), "TotalRecolectado"

# Restricción 1: el total de unidades debe ser al menos LB
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) >= LB

# Restricción 2: el total de unidades sea como maximo UB
modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes) for i in range(n_elementos)) <= UB

# Restricción 3: disponibilidad por pasillo, por cada elemento i la cantidad total debe ser menor o igual
# a la suma de lo disponible en los pasillos seleccionados
for i in range(n_elementos):
    disponibilidad_total = sum(S[a][i] for a in pasillos)
    modelo += lpSum(W[o][i] * x[o] for o in range(n_ordenes)) <= disponibilidad_total

# Resolver modelo
modelo.solve()


# Resultados
print("Estado de solución:", LpStatus[modelo.status])
print("Órdenes seleccionadas (O'):", [o for o in range(n_ordenes) if x[o].varValue == 1])
print("Unidades recolectadas:", pulp.value(modelo.objective))
