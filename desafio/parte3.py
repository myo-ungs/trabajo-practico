import pulp
from itertools import combinations
from cargar_input import leer_input

# --- Lectura de datos ---
W, S, LB, UB = leer_input("datos_de_entrada/input_0001.txt")

max_pasillos = 2  # cantidad fija de pasillos a seleccionar (A conocido)
n_ordenes = len(W)
n_elementos = len(W[0])
n_pasillos = len(S)

# Verifica si un subconjunto de órdenes puede servirse por un pasillo
def es_patron_factible(ordenes, pasillo):
    for i in range(n_elementos):
        demanda_total = sum(W[o][i] for o in ordenes)
        if demanda_total > S[pasillo][i]:
            return False
    return True

# PARÁMETROS PARA ACELERAR
max_r = 2  # Máximo tamaño de subconjuntos de órdenes
max_patrones_por_pasillo = 10  # Límite por pasillo

# Generar columnas (patrones) válidas
columnas_validas = []

for a in range(n_pasillos):
    cuenta_patrones = 0
    for r in range(1, max_r + 1):
        for subset in combinations(range(n_ordenes), r):
            if es_patron_factible(subset, a):
                vector = [0] * (n_ordenes + n_pasillos)
                for o in subset:
                    vector[o] = 1
                vector[n_ordenes + a] = 1
                columnas_validas.append((vector, subset, a))
                cuenta_patrones += 1
                if cuenta_patrones >= max_patrones_por_pasillo:
                    break
        if cuenta_patrones >= max_patrones_por_pasillo:
            break


print(f"Total de patrones factibles generados: {len(columnas_validas)}")

# Construcción del modelo
def ConstruirModelo(columnas_validas, n_ordenes, n_pasillos, max_pasillos):
    modelo = pulp.LpProblem("Modelo_Generacion_Columnas", pulp.LpMaximize)
    z = pulp.LpVariable.dicts("z", range(len(columnas_validas)), cat="Binary")
    y = pulp.LpVariable.dicts("y", range(n_pasillos), cat="Binary")

    modelo += pulp.lpSum(
        sum(col[0][o] for o in range(n_ordenes)) * z[i]
        for i, col in enumerate(columnas_validas)
    )

    for o in range(n_ordenes):
        modelo += (
            pulp.lpSum(columnas_validas[i][0][o] * z[i] for i in range(len(columnas_validas))) <= 1,
            f"Orden_{o}_una_vez"
        )

    for i, (_, _, a) in enumerate(columnas_validas):
        modelo += z[i] <= y[a]

    modelo += pulp.lpSum(y[a] for a in range(n_pasillos)) == max_pasillos

    return modelo, z, y

modelo, z, y = ConstruirModelo(columnas_validas, n_ordenes, n_pasillos, max_pasillos)

# AgregarColumna
def AgregarColumna(modelo, z, y, columnas_validas, nueva_columna):
    i = len(columnas_validas)
    columnas_validas.append(nueva_columna)
    vector, ordenes, pasillo = nueva_columna

    z[i] = pulp.LpVariable(f"z_{i}", cat="Binary")

    contribucion_objetivo = sum(vector[o] for o in range(n_ordenes)) * z[i]
    modelo.setObjective(modelo.objective + contribucion_objetivo)

    for o in range(n_ordenes):
        if f"Orden_{o}_una_vez" in modelo.constraints:
            modelo.constraints[f"Orden_{o}_una_vez"] += vector[o] * z[i]

    modelo += z[i] <= y[pasillo]

# Resolver modelo inicial
solver = pulp.SCIP()
modelo.solve(solver)

# Resultados iniciales
print("Estado inicial:", pulp.LpStatus[modelo.status])
print("Órdenes cubiertas:", pulp.value(modelo.objective))
for i in range(len(columnas_validas)):
    if z[i].varValue == 1:
        print(f" - Pasillo {columnas_validas[i][2]}, Órdenes: {columnas_validas[i][1]}")

# ====================
# Probar AgregarColumna
# ====================

print("\nIntentando agregar una columna adicional factible...")

nueva_columna = None
for o in range(n_ordenes):
    for a in range(n_pasillos):
        if es_patron_factible([o], a):
            vector = [0] * (n_ordenes + n_pasillos)
            vector[o] = 1
            vector[n_ordenes + a] = 1
            nueva_columna = (vector, [o], a)
            break
    if nueva_columna:
        break

if nueva_columna:
    AgregarColumna(modelo, z, y, columnas_validas, nueva_columna)
    print("Columna agregada. Reoptimizando.")
    modelo.solve(solver)

    print("Nuevo estado:", pulp.LpStatus[modelo.status])
    print("Nueva solución con columna agregada:")
    for i in range(len(columnas_validas)):
        if z[i].varValue == 1:
            print(f" - Pasillo {columnas_validas[i][2]}, Órdenes: {columnas_validas[i][1]}")
else:
    print("No se encontró ninguna columna factible para agregar.")