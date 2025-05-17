import pulp
from itertools import combinations

# Datos de entrada
W = [
    [1, 3, 0, 1, 1],
    [1, 1, 0, 0, 0],
    [2, 0, 0, 0, 0],
    [0, 0, 0, 2, 4],
    [3, 4, 1, 0, 0]
]

S = [
    [2, 1, 2, 0, 1],
    [1, 3, 0, 2, 0],
    [2, 2, 0, 2, 3],
    [1, 1, 2, 3, 1],
    [0, 1, 2, 1, 1]
]

LB = 5
UB = 12
max_pasillos = 5

n_ordenes = len(W)
n_elementos = len(W[0])
n_pasillos = len(S)

# Verificación de patrones factibles
def es_patron_factible(ordenes, pasillo):
    for i in range(n_elementos):
        demanda_total = sum(W[o][i] for o in ordenes)
        if demanda_total > S[pasillo][i]:
            return False
    return True

# Generación de columnas válidas
columnas_validas = []

for a in range(n_pasillos):
    for r in range(1, n_ordenes + 1):
        for subset in combinations(range(n_ordenes), r):
            if es_patron_factible(subset, a):
                vector = [0] * (n_ordenes + n_pasillos)
                for o in subset:
                    vector[o] = 1
                vector[n_ordenes + a] = 1
                columnas_validas.append((vector, subset, a))

print(f"Total de patrones factibles generados: {len(columnas_validas)}")

# Construcción del modelo
def ConstruirModelo(columnas_validas, n_ordenes, n_pasillos, max_pasillos):
    modelo = pulp.LpProblem("Modelo_Generacion_Columnas", pulp.LpMaximize)
    z = pulp.LpVariable.dicts("z", range(len(columnas_validas)), cat="Binary")
    y = pulp.LpVariable.dicts("y", range(n_pasillos), cat="Binary")

    # Objetivo
    modelo += pulp.lpSum(
        sum(col[0][o] for o in range(n_ordenes)) * z[i]
        for i, col in enumerate(columnas_validas)
    )

    # Restricciones de órdenes (nombradas)
    for o in range(n_ordenes):
        modelo += (
            pulp.lpSum(columnas_validas[i][0][o] * z[i] for i in range(len(columnas_validas))) <= 1,
            f"Orden_{o}_una_vez"
        )

    # Relación z[i] y y[a]
    for i, (_, _, a) in enumerate(columnas_validas):
        modelo += z[i] <= y[a]

    # Restricción: usar exactamente max_pasillos
    modelo += pulp.lpSum(y[a] for a in range(n_pasillos)) == max_pasillos

    return modelo, z, y

modelo, z, y = ConstruirModelo(columnas_validas, n_ordenes, n_pasillos, max_pasillos)


# funcion agregar columna
def AgregarColumna(modelo, z, y, columnas_validas, nueva_columna):
    """
    Agrega una nueva columna (patrón) al modelo existente.

    nueva_columna: tupla (vector_binario, ordenes, pasillo)
    """
    i = len(columnas_validas)  # nuevo índice
    columnas_validas.append(nueva_columna)
    
    vector, ordenes, pasillo = nueva_columna

    # Crear nueva variable binaria z_i
    z[i] = pulp.LpVariable(f"z_{i}", cat="Binary")

    # Actualizar función objetivo
    contribucion_objetivo = sum(vector[o] for o in range(len(W))) * z[i]
    modelo.setObjective(modelo.objective + contribucion_objetivo)

    # Actualizar restricciones de órdenes
    for o in range(len(W)):
        if f"Orden_{o}_una_vez" in modelo.constraints:
            modelo.constraints[f"Orden_{o}_una_vez"] += vector[o] * z[i]

    # Relación z[i] <= y[a]
    modelo += z[i] <= y[pasillo]


# Resolver modelo
modelo.solve()

# Resultados
print("Estado de solución:", pulp.LpStatus[modelo.status])
if pulp.LpStatus[modelo.status] == "Optimal":
    print("Órdenes cubiertas:", pulp.value(modelo.objective))
    for i in range(len(columnas_validas)):
        if z[i].varValue == 1:
            print(f" - Pasillo {columnas_validas[i][2]}, Órdenes: {columnas_validas[i][1]}")
else:
    print("No se encontró solución factible.")
