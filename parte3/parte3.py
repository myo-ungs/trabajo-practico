from pyscipopt import Model, quicksum, SCIP_PARAMSETTING
from itertools import combinations
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input

# Leer datos desde archivo
archivo_input = "datos_de_entrada/A/instance_0001.txt"
W, S, LB, UB = leer_input(archivo_input)

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
    modelo = Model("Modelo_Generacion_Columnas")
    modelo.setParam('display/verblevel', 0)
    modelo.setParam('limits/time', 300)

    # Variables
    z = {}
    for i in range(len(columnas_validas)):
        z[i] = modelo.addVar(vtype="B", name=f"z_{i}")
    y = {}
    for a in range(n_pasillos):
        y[a] = modelo.addVar(vtype="B", name=f"y_{a}")

    # modelo.update() ← ELIMINAR ESTA LÍNEA

    # Función objetivo
    obj_expr = quicksum(
        sum(columnas_validas[i][0][o] for o in range(n_ordenes)) * z[i]
        for i in range(len(columnas_validas))
    )
    modelo.setObjective(obj_expr, "maximize")

    # Restricciones
    for o in range(n_ordenes):
        modelo.addCons(
            quicksum(columnas_validas[i][0][o] * z[i] for i in range(len(columnas_validas))) <= 1,
            name=f"Orden_{o}_una_vez"
        )

    for i, (_, _, a) in enumerate(columnas_validas):
        modelo.addCons(z[i] <= y[a], name=f"Vinculacion_z{i}_y{a}")

    modelo.addCons(quicksum(y[a] for a in range(n_pasillos)) == max_pasillos, name="MaxPasillos")

    # modelo.update() ← ELIMINAR ESTA LÍNEA

    return modelo, z, y

modelo, z, y = ConstruirModelo(columnas_validas, n_ordenes, n_pasillos, max_pasillos)

# Resolver modelo inicial
modelo.optimize()

status = modelo.getStatus()
print("Estado inicial:", status)
if status == "optimal" or status == "optimal_inaccurate":
    print("Órdenes cubiertas:", modelo.getObjVal())
    for i in range(len(columnas_validas)):
        if modelo.getVal(z[i]) > 0.5:
            print(f" - Pasillo {columnas_validas[i][2]}, Órdenes: {columnas_validas[i][1]}")
else:
    print("No se encontró solución óptima.")

# ====================
# Intentar agregar una nueva columna factible
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
    print("Columna agregada. Reconstruyendo modelo y reoptimizando.")
    columnas_validas.append(nueva_columna)
    modelo, z, y = ConstruirModelo(columnas_validas, n_ordenes, n_pasillos, max_pasillos)
    modelo.optimize()

    status = modelo.getStatus()
    print("Nuevo estado:", status)
    if status == "optimal" or status == "optimal_inaccurate":
        print("Nueva solución con columna agregada:")
        for i in range(len(columnas_validas)):
            if modelo.getVal(z[i]) > 0.5:
                print(f" - Pasillo {columnas_validas[i][2]}, Órdenes: {columnas_validas[i][1]}")
    else:
        print("No se encontró solución óptima tras agregar columna.")
else:
    print("No se encontró ninguna columna factible para agregar.")

# === Guardar resultados en archivo .out ===

nombre_dataset = os.path.basename(os.path.dirname(archivo_input))  # A o B
nombre_instancia = os.path.splitext(os.path.basename(archivo_input))[0]  # instance_uvxy

# Crear carpeta de salida
output_dir = os.path.join("parte3", "OUTPUT", nombre_dataset)
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, f"{nombre_instancia}.out")

# Guardar resultados
with open(output_path, "w") as f:
    f.write(f"{status}\n")
    f.write(f"{int(modelo.getObjVal())}\n")
    
    ordenes_totales = set()
    for i in range(len(columnas_validas)):
        if modelo.getVal(z[i]) > 0.5:
            ordenes_totales.update(columnas_validas[i][1])
    
    ordenes_ordenadas = sorted(ordenes_totales)
    f.write(" ".join(map(str, ordenes_ordenadas)) + "\n")