import pulp
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum, LpBinary
import os 
# Importar funciones de carga de datos desde leer_archivo.py
from leer_archivo import cargar_datos_instancia_desafio, transformar_datos_dispersos_a_densos

# --- Parámetros de Entrada y Carga de Datos ---

# Especifica la ruta al archivo de instancia del desafío.
# Se asume que existe una carpeta "datos_desafio" en el mismo directorio que este script,
# y que dentro de ella está el archivo "instance_0001.txt".

# Obtener el directorio actual del script
directorio_actual_script = os.path.dirname(os.path.abspath(__file__))
# Construir la ruta al archivo de instancia
nombre_archivo_instancia = os.path.join(directorio_actual_script, "datos_desafio", "instance_0001.txt")

# Verificar si el archivo de instancia existe
if not os.path.exists(nombre_archivo_instancia):
    print(f"Error: El archivo de instancia no se encuentra en '{nombre_archivo_instancia}'")
    print("Por favor, asegúrate de que el archivo exista en la ruta especificada o crea datos de ejemplo.")
    # Fallback a datos hardcodeados si el archivo no existe, para que el script pueda correr y ser probado.
    # Estos datos son solo para demostración y pueden no ser representativos.
    print("Usando datos harcodeados de ejemplo para demostración.")
    matriz_W_ejemplo = [
        [1, 3, 0, 1, 1], [1, 1, 0, 0, 0], [2, 0, 0, 0, 0],
        [0, 0, 0, 2, 4], [3, 4, 1, 0, 0]
    ]
    matriz_S_ejemplo = [
        [2, 1, 2, 0, 1], [1, 3, 0, 2, 0], [2, 2, 0, 2, 3],
        [1, 1, 2, 3, 1], [0, 1, 2, 1, 1]
    ]
    K_ordenes = len(matriz_W_ejemplo)
    I_items = len(matriz_W_ejemplo[0]) if K_ordenes > 0 else 0
    J_pasillos = len(matriz_S_ejemplo)
    LB_lim_inf_ola = 5  # Límite inferior para el tamaño de la ola (wave)
    UB_lim_sup_ola = 12 # Límite superior para el tamaño de la ola (wave)
    matriz_W = matriz_W_ejemplo
    matriz_S = matriz_S_ejemplo
    # Coordenadas de pasillo no son cruciales para esta parte con objetivo simplificado, se pueden omitir o poner por defecto.
    # pasillos_coordenadas = [(0,0)] * J_pasillos 
else:
    print(f"Cargando datos desde: {nombre_archivo_instancia}")
    # Cargar datos usando las funciones de leer_archivo.py
    # MODIFICADO: Ajustar al retorno de 5 valores de cargar_datos_instancia_desafio
    K_ordenes, I_items, J_pasillos, ordenes_datos_dispersos, pasillos_datos_dispersos = \
        cargar_datos_instancia_desafio(nombre_archivo_instancia)
    
    # Definir L_w y U_w externamente o con valores de ejemplo
    # Estos valores podrían pasarse como argumentos al script o a una función principal si se refactoriza.
    LB_lim_inf_ola = 1  # Ejemplo de Límite inferior para el tamaño de la ola (wave)
    UB_lim_sup_ola = 150 # Ejemplo de Límite superior para el tamaño de la ola (wave)
    
    # Transformar datos a formato denso (matrices)
    matriz_W, matriz_S = transformar_datos_dispersos_a_densos(
        K_ordenes, I_items, J_pasillos,
        ordenes_datos_dispersos, pasillos_datos_dispersos
    )

# A': Conjunto de pasillos CONOCIDOS a visitar (ejemplo para "Primera parte" del desafío)
# Este es un parámetro clave para esta parte del problema.
# Debe ser una lista de índices de pasillos (base 0).
# Puedes modificar esta lógica para tomar A' como entrada o configurarlo según necesites.

if J_pasillos > 1:
    # Ejemplo: seleccionar el primer pasillo y el pasillo del medio.
    pasillos_conocidos_A_prima = [0, J_pasillos // 2] 
    # Evitar duplicados si J_pasillos es 2 (ya que 0 // 2 = 0, J_pasillos // 2 sería 1)
    if J_pasillos == 2: # Simplificado para J_pasillos = 2
         pasillos_conocidos_A_prima = [0,1]
elif J_pasillos == 1:
    # Si solo hay un pasillo, ese es el único que se puede conocer.
    pasillos_conocidos_A_prima = [0]
else: 
    # Si no hay pasillos definidos en la instancia.
    pasillos_conocidos_A_prima = [] 
    print("Advertencia: No hay pasillos en la instancia cargada o J_pasillos es 0. A' (pasillos conocidos) estará vacío.")

# Validar que los índices de los pasillos conocidos estén dentro de los límites (si hay pasillos)
if J_pasillos > 0:
    pasillos_validos = []
    for p_idx in pasillos_conocidos_A_prima:
        if 0 <= p_idx < J_pasillos:
            pasillos_validos.append(p_idx)
        else:
            # Esto podría ocurrir si la lógica para definir pasillos_conocidos_A_prima es incorrecta
            # o si J_pasillos es positivo pero pasillos_conocidos_A_prima contiene índices inválidos.
            print(f"Advertencia: Índice de pasillo {p_idx} en pasillos_conocidos_A_prima está fuera de rango (0 a {J_pasillos-1}). Será omitido.")
    pasillos_conocidos_A_prima = pasillos_validos
elif pasillos_conocidos_A_prima: # Si J_pasillos es 0 pero pasillos_conocidos_A_prima no está vacío (no debería ocurrir con la lógica actual)
    print("Advertencia: J_pasillos es 0, pero pasillos_conocidos_A_prima no está vacío. Forzando A' a vacío.")
    pasillos_conocidos_A_prima = []


print(f"\nResolviendo Desafío - Primera Parte (A' fijo, seleccionar O')")
print(f"Pasillos conocidos (A'): {pasillos_conocidos_A_prima}")
print(f"Parámetros de la instancia: Órdenes (K)={K_ordenes}, Items (I)={I_items}, Pasillos (J)={J_pasillos}, Límite Inf. Wave (Lw)={LB_lim_inf_ola}, Límite Sup. Wave (Uw)={UB_lim_sup_ola}")

# --- Modelo de Programación Lineal con PuLP ---

# Crear el problema de maximización
modelo = LpProblem("Desafio_Parte1_A_prima_fijo", LpMaximize)

# Variables de decisión:
# x_k = 1 si la orden k (de K_ordenes) se incluye en la ola (O'), 0 en caso contrario.
x_vars = LpVariable.dicts("x", range(K_ordenes), cat=LpBinary) # LpBinary para variables binarias

# Función Objetivo:
# Maximizar la cantidad total de ítems recolectados de las órdenes seleccionadas O'.
# (Este es el objetivo para la "Primera parte" del desafío donde A' es fijo)
# total_items_recolectados = lpSum(matriz_W[k][i] * x_vars[k] for k in range(K_ordenes) for i in range(I_items))
# Simplificación: si un ítem no está en una orden, matriz_W[k][i] es 0, por lo que no suma.
# El objetivo es la suma de todos los items de las ordenes seleccionadas.
# Cada W[k][i] es la cantidad del item i en la orden k.
# Sumar W[k][i] para todos los i de una orden k da el total de items en esa orden.
# Luego, multiplicar por x_vars[k] y sumar sobre k.

expresion_objetivo = lpSum(
    matriz_W[k][i] * x_vars[k] 
    for k in range(K_ordenes) 
    for i in range(I_items)
)
modelo += expresion_objetivo, "MaximizarTotalItemsRecolectados"

# Restricciones:

# R1: El total de unidades (ítems) recolectadas en la ola debe ser al menos LB_lim_inf_ola.
modelo += expresion_objetivo >= LB_lim_inf_ola, "LimiteInferiorUnidadesOla"

# R2: El total de unidades (ítems) recolectadas en la ola debe ser como máximo UB_lim_sup_ola.
modelo += expresion_objetivo <= UB_lim_sup_ola, "LimiteSuperiorUnidadesOla"

# R3: Restricción de disponibilidad de ítems en los pasillos conocidos A'.
# Para cada tipo de ítem i, la cantidad total requerida por las órdenes seleccionadas O'
# no debe exceder la suma de lo disponible de ese ítem en los pasillos de A'.

if not pasillos_conocidos_A_prima and K_ordenes > 0 : # Si A' está vacío (no hay pasillos conocidos) pero hay órdenes
    # Si A' está vacío, no se puede tomar ningún ítem de ningún pasillo.
    # Si LB_lim_inf_ola > 0, el problema será infactible si alguna orden tiene items y es seleccionada.
    # Si LB_lim_inf_ola = 0, se podría seleccionar ninguna orden (si eso satisface el objetivo y otras restricciones).
    # Forzamos a que no se pueda tomar nada si A' es vacío y se intenta seleccionar una orden con items.
    for i_idx in range(I_items):
        cantidad_requerida_item_i = lpSum(matriz_W[k][i_idx] * x_vars[k] for k in range(K_ordenes))
        # Si no hay pasillos en A', la disponibilidad es 0.
        modelo += cantidad_requerida_item_i <= 0, f"DisponibilidadItem_{i_idx}_SinPasillosEnAPrima"
elif pasillos_conocidos_A_prima: # Solo agregar esta restricción si hay pasillos en A'
    for i_idx in range(I_items):
        # Cantidad total del ítem i_idx requerida por las órdenes seleccionadas
        cantidad_requerida_item_i = lpSum(matriz_W[k][i_idx] * x_vars[k] for k in range(K_ordenes))
        
        # Disponibilidad total del ítem i_idx en los pasillos de A'
        # Asegurarse de que los índices p_idx e i_idx son válidos para matriz_S
        disponibilidad_item_i_en_A_prima = sum(
            matriz_S[p_idx][i_idx] 
            for p_idx in pasillos_conocidos_A_prima 
            if 0 <= p_idx < J_pasillos and 0 <= i_idx < I_items # Doble chequeo por seguridad
        )
        modelo += cantidad_requerida_item_i <= disponibilidad_item_i_en_A_prima, f"DisponibilidadItem_{i_idx}"

# Resolver el modelo
# Se puede especificar un solver, ej: pulp.PULP_CBC_CMD(). Si no, PuLP usará el default.
# msg=0 para suprimir la salida detallada del solver en la consola.
solver_cbc = pulp.PULP_CBC_CMD(msg=0) 
modelo.solve(solver_cbc)


# --- Función de Verificación de Factibilidad de una Solución ---
def verificar_factibilidad_solucion(
    indices_ordenes_seleccionadas_O_prima, 
    indices_pasillos_dados_A_prima, 
    datos_W, # Matriz de items por orden
    datos_S, # Matriz de stock de items por pasillo
    lim_inf_ola, lim_sup_ola, 
    total_items_catalogo, total_ordenes_disponibles, total_pasillos_disponibles
    ):
    """
    Verifica si una solución dada (un conjunto de órdenes O') es factible
    para un conjunto conocido de pasillos A', según las reglas del desafío.

    Retorna: (es_factible, mensaje_detalle)
    """
    # Caso base: no hay órdenes seleccionadas en O'
    if not indices_ordenes_seleccionadas_O_prima:
        if lim_inf_ola > 0:
            return False, f"No se seleccionaron órdenes (O' vacío), pero el límite inferior de la ola (Lw={lim_inf_ola}) es mayor a 0."
        return True, "Solución factible (O' vacío y Lw=0)."

    # Validar que los índices de las órdenes seleccionadas sean válidos
    for o_idx in indices_ordenes_seleccionadas_O_prima:
        if not (0 <= o_idx < total_ordenes_disponibles):
            return False, f"Índice de orden {o_idx} en O' está fuera de rango (0 a {total_ordenes_disponibles-1})."

    # Calcular el total de unidades (ítems) recolectadas en la ola
    total_unidades_recolectadas_en_ola = 0
    for o_idx in indices_ordenes_seleccionadas_O_prima:
        for item_idx in range(total_items_catalogo):
            # Asegurar acceso seguro a datos_W
            if 0 <= o_idx < len(datos_W) and 0 <= item_idx < len(datos_W[o_idx]):
                 total_unidades_recolectadas_en_ola += datos_W[o_idx][item_idx]
            else:
                # Esto indicaría un problema con las dimensiones de los datos o los índices
                return False, f"Error interno: Acceso fuera de rango en datos_W para orden {o_idx}, ítem {item_idx}."

    # Verificar R1 y R2 (límites inferior LB y superior UB de la ola)
    if not (lim_inf_ola <= total_unidades_recolectadas_en_ola <= lim_sup_ola):
        return False, f"Incumplimiento de límites de tamaño de ola: Recolectado={total_unidades_recolectadas_en_ola}, Lw={lim_inf_ola}, Uw={lim_sup_ola}"

    # Verificar R3 (Disponibilidad de ítems en los pasillos A')
    if not indices_pasillos_dados_A_prima: # Si A' (pasillos conocidos) es vacío
        if total_unidades_recolectadas_en_ola > 0 : # y se recolectaron ítems
             return False, f"Se recolectaron {total_unidades_recolectadas_en_ola} ítems, pero A' (pasillos conocidos) está vacío. No se pueden obtener ítems."
        # Si no se recolectó nada (total_unidades_recolectadas_en_ola == 0) y A' es vacío, es factible respecto a disponibilidad.
    else: # Si hay pasillos en A'
        for item_idx in range(total_items_catalogo):
            # Calcular cuánto se requiere del ítem item_idx por las órdenes en O'
            cantidad_requerida_item_idx = 0
            for o_idx in indices_ordenes_seleccionadas_O_prima:
                 if 0 <= o_idx < len(datos_W) and 0 <= item_idx < len(datos_W[o_idx]):
                    cantidad_requerida_item_idx += datos_W[o_idx][item_idx]
                 # No es necesario un else aquí, el acceso ya se validó antes para total_unidades_recolectadas_en_ola
            
            if cantidad_requerida_item_idx == 0: # Si este ítem no es requerido por ninguna orden en O', continuar.
                continue

            # Calcular disponibilidad del ítem item_idx en los pasillos de A'
            disponibilidad_item_idx_en_A_prima = 0
            for p_idx in indices_pasillos_dados_A_prima:
                # Validar índice de pasillo
                if not (0 <= p_idx < total_pasillos_disponibles):
                    return False, f"Índice de pasillo {p_idx} en A' está fuera de rango (0 a {total_pasillos_disponibles-1})."
                # Validar índice de ítem para el pasillo (aunque I_items debería ser consistente)
                if not (0 <= item_idx < total_items_catalogo):
                    return False, f"Índice de ítem {item_idx} fuera de rango para datos_S (0 a {total_items_catalogo-1})."
                # Asegurar acceso seguro a datos_S
                if 0 <= p_idx < len(datos_S) and 0 <= item_idx < len(datos_S[p_idx]):
                     disponibilidad_item_idx_en_A_prima += datos_S[p_idx][item_idx]
                else:
                    return False, f"Error interno: Acceso fuera de rango en datos_S para pasillo {p_idx}, ítem {item_idx}."

            # Comparar requerido vs disponible para el ítem actual
            if cantidad_requerida_item_idx > disponibilidad_item_idx_en_A_prima:
                return False, f"Insuficientes ítems del tipo {item_idx}: Requerido={cantidad_requerida_item_idx}, Disponible en A'={disponibilidad_item_idx_en_A_prima}"

    # Si todas las verificaciones pasan
    return True, "La solución es factible."

# --- Resultados y Salida del Modelo ---
print("\n--- Resultados del Modelo de Optimización ---")
print(f"Estado de la solución: {LpStatus[modelo.status]}")

ordenes_seleccionadas_final_indices = []
valor_funcion_objetivo = 0

if LpStatus[modelo.status] == "Optimal":
    # Obtener las órdenes seleccionadas (aquellas donde x_k = 1)
    ordenes_seleccionadas_final_indices = [o_idx for o_idx in range(K_ordenes) if x_vars[o_idx].varValue == 1]
    valor_funcion_objetivo = pulp.value(modelo.objective)
    
    print(f"Valor de la función objetivo (Total de ítems recolectados): {valor_funcion_objetivo}")

    # Verificar la factibilidad de la solución encontrada por el modelo
    es_factible_solucion_modelo, mensaje_factibilidad_sol_modelo = verificar_factibilidad_solucion(
        ordenes_seleccionadas_final_indices,
        pasillos_conocidos_A_prima, # A' es fijo en esta parte
        matriz_W, matriz_S, 
        LB_lim_inf_ola, UB_lim_sup_ola, 
        I_items, K_ordenes, J_pasillos
    )
    print(f"Verificación de factibilidad de la solución del modelo: {'Sí, es factible' if es_factible_solucion_modelo else 'No, no es factible'}")
    if not es_factible_solucion_modelo:
        print(f"Detalle de la no factibilidad: {mensaje_factibilidad_sol_modelo}")
    
elif LpStatus[modelo.status] == "Infeasible":
    print(f"El problema es infactible con los parámetros dados y el conjunto A' = {pasillos_conocidos_A_prima}.")
    print("Esto significa que no existe un conjunto de órdenes O' que satisfaga todas las restricciones.")
    # Se podría verificar si una solución vacía (ninguna orden) es factible, útil si Lw=0.
    es_factible_sol_vacia, msg_sol_vacia = verificar_factibilidad_solucion(
        [], pasillos_conocidos_A_prima, matriz_W, matriz_S, LB_lim_inf_ola, UB_lim_sup_ola, I_items, K_ordenes, J_pasillos
    )
    print(f"Verificación de factibilidad para una solución vacía (O'=[]): {'Sí' if es_factible_sol_vacia else 'No'}. Mensaje: {msg_sol_vacia}")
elif LpStatus[modelo.status] == "Unbounded":
    print("El problema es no acotado. Esto no debería ocurrir si los límites de la ola (Lw, Uw) están definidos y son finitos.")
else: # Otros estados como "Not Solved" o "Undefined"
    print(f"No se encontró una solución óptima o el estado es: {LpStatus[modelo.status]}.".strip())

# --- Salida en el Formato Requerido por el Desafío (Adaptado para "Primera Parte") ---
# Para la "Primera Parte" del desafío (Desafío(A'|O)), se espera:
# Línea 1: Índices de las órdenes seleccionadas O' (separados por espacio)
# Línea 2: Índices de los pasillos A' (que fueron dados como entrada, separados por espacio)

print("\n--- Salida Formato Desafío (Primera Parte: A' fijo, O' seleccionado) ---")
# Línea 1: Órdenes seleccionadas (O')
# Los índices deben ser los originales (base 0)
print(" ".join(map(str, ordenes_seleccionadas_final_indices)))

# Línea 2: Pasillos seleccionados (A' - que fueron dados como entrada)
# Los índices deben ser los originales (base 0)
print(" ".join(map(str, pasillos_conocidos_A_prima)))


# --- Ejemplo Adicional: Uso de la función de verificación con una solución hipotética ---
# (Esto es para tu prueba y depuración, no forma parte de la salida estándar del desafío)
if K_ordenes > 0 and J_pasillos > 0 : # Solo si hay suficientes datos para un ejemplo
    print("\n--- Ejemplo de Verificación de Factibilidad Manual (para depuración) ---")
    # Definir una solución hipotética O' (lista de índices de órdenes)
    ordenes_hipoteticas_O_prima = [0, 1] if K_ordenes >=2 else ([0] if K_ordenes ==1 else [])
    
    # Usar los mismos pasillos conocidos A' que se usaron para el modelo
    pasillos_fijos_A_prima_ejemplo = pasillos_conocidos_A_prima 

    if ordenes_hipoteticas_O_prima : # Solo probar si hay órdenes hipotéticas
        print(f"Probando factibilidad para O'={ordenes_hipoteticas_O_prima} y A'={pasillos_fijos_A_prima_ejemplo}")
        es_factible_hipotetico, msg_hipotetico = verificar_factibilidad_solucion(
            ordenes_hipoteticas_O_prima,
            pasillos_fijos_A_prima_ejemplo, 
            matriz_W, matriz_S, 
            LB_lim_inf_ola, UB_lim_sup_ola, 
            I_items, K_ordenes, J_pasillos
        )
        print(f"¿Es factible la selección hipotética? {'Sí' if es_factible_hipotetico else 'No'}")
        print(f"Mensaje de factibilidad: {msg_hipotetico}")
    else:
        print("No hay suficientes órdenes o pasillos para ejecutar el ejemplo de verificación manual.")
