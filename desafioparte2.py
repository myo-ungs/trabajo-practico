import pulp
# Asegúrate de que leer_archivo.py esté en el mismo directorio o en el PYTHONPATH
from leer_archivo import cargar_datos_instancia_desafio, transformar_datos_dispersos_a_densos

# Definición de constantes y parámetros
RUTA_INSTANCIA = "datos_desafio/instance_0001.txt"

# O' FIJO: Conjunto de índices de órdenes que se consideran fijas y dadas.
# Estas órdenes DEBEN ser procesadas.
# Ejemplo: las primeras 3 órdenes (índices 0, 1, 2) de la instancia.
# Para la instancia instance_0001.txt (K=61), los índices válidos son 0-60.
ORDENES_FIJAS_INDICES_EJEMPLO = [0, 1, 2] # Esto debería ser un parámetro del problema.

def verificar_validez_ordenes_fijas(ordenes_fijas_idx, ordenes_matriz_W, num_items_total, num_ordenes_total, L_w, U_w, nombre_param_ordenes="ORDENES_FIJAS_INDICES"):
    """
    Verifica si el conjunto de órdenes fijas O' cumple con los límites de wave (L_w, U_w).
    Imprime una advertencia si no se cumplen.
    Retorna True si O' es válido respecto a Lw, U_w, False en caso contrario.
    """
    total_items_en_O_prima = 0
    ordenes_validas_para_calculo = []

    for k_idx in ordenes_fijas_idx:
        if 0 <= k_idx < num_ordenes_total:
            ordenes_validas_para_calculo.append(k_idx)
            for i_idx in range(num_items_total):
                total_items_en_O_prima += ordenes_matriz_W[k_idx][i_idx]
        else:
            print(f"Advertencia: Índice de orden {k_idx} en '{nombre_param_ordenes}' está fuera de rango (0-{num_ordenes_total-1}) y será ignorado para el cálculo de Lw/Uw.")

    print(f"Total de ítems en las órdenes fijas O' (considerando solo índices válidos {ordenes_validas_para_calculo}): {total_items_en_O_prima}")
    
    if not (L_w <= total_items_en_O_prima <= U_w):
        print(f"ADVERTENCIA: El total de ítems en O' ({total_items_en_O_prima}) NO cumple con los límites de wave Lw={L_w}, Uw={U_w}.")
        print("El modelo intentará encontrar pasillos, pero la O' original podría no ser válida para el problema general del desafío.")
        return False
    else:
        print(f"El total de ítems en O' ({total_items_en_O_prima}) CUMPLE con los límites de wave Lw={L_w}, Uw={U_w}.")
        return True

def verificar_factibilidad_seleccion_pasillos(ordenes_fijas_idx, pasillos_seleccionados_idx, ordenes_matriz_W, pasillos_matriz_S, num_items_total, num_ordenes_total, num_pasillos_total):
    """
    Verifica si los pasillos seleccionados A' pueden satisfacer la demanda de ítems de las órdenes fijas O'.
    """
    print("\\n--- Verificación de Factibilidad de la Selección de Pasillos ---")
    
    items_requeridos_O_prima = [0] * num_items_total
    for k_idx in ordenes_fijas_idx:
        if 0 <= k_idx < num_ordenes_total: # Solo procesar índices de orden válidos
            for i_idx in range(num_items_total):
                items_requeridos_O_prima[i_idx] += ordenes_matriz_W[k_idx][i_idx]

    items_disponibles_A_prima = [0] * num_items_total
    for j_idx in pasillos_seleccionados_idx:
        if 0 <= j_idx < num_pasillos_total: # Solo procesar índices de pasillo válidos
            for i_idx in range(num_items_total):
                items_disponibles_A_prima[i_idx] += pasillos_matriz_S[j_idx][i_idx]

    factible = True
    for i_idx in range(num_items_total):
        if items_requeridos_O_prima[i_idx] > 0: # Solo verificar si el ítem es necesitado
            if items_disponibles_A_prima[i_idx] < items_requeridos_O_prima[i_idx]:
                print(f"ERROR de Factibilidad: Ítem {i_idx}: Requerido={items_requeridos_O_prima[i_idx]}, Disponible en A'={items_disponibles_A_prima[i_idx]}")
                factible = False
    
    if factible:
        print("Factibilidad Confirmada: Todos los ítems requeridos por O' (válidas) pueden ser cubiertos por los pasillos seleccionados A'.")
    else:
        print("Factibilidad Fallida: No todos los ítems requeridos por O' (válidas) pueden ser cubiertos por los pasillos seleccionados A'. Esto NO debería ocurrir si el solver encontró una solución óptima/factible para las órdenes procesadas.")
    
    return factible

def resolver_desafio_parte2(ruta_instancia, ordenes_fijas_indices_param):
    """
    Resuelve la Parte 2 del desafío: Dado un conjunto de órdenes O' fijo,
    seleccionar un conjunto mínimo de pasillos A' para satisfacer la demanda de O'.
    """
    print(f"Iniciando Desafío Parte 2: Selección de Pasillos para Órdenes Fijas O'")
    print(f"Ruta de instancia: {ruta_instancia}")
    print(f"Órdenes fijas (O') para esta ejecución (índices 0-based): {ordenes_fijas_indices_param}")
    print("----------------------------------------------------")

    # Cargar datos de la instancia
    try:
        datos_brutos = cargar_datos_instancia_desafio(ruta_instancia)
        # MODIFICADO: Ajustar al retorno de 5 valores de cargar_datos_instancia_desafio
        K_ordenes, I_items, J_pasillos, ordenes_dispersos, pasillos_dispersos = datos_brutos
        
        # Definir L_w y U_w externamente o con valores de ejemplo
        # Estos valores podrían pasarse como argumentos al script o a una función principal.
        L_w = 1  # Ejemplo de Límite inferior para el tamaño de la ola (wave)
        U_w = 150 # Ejemplo de Límite superior para el tamaño de la ola (wave)

        ordenes_matriz_W, pasillos_matriz_S = transformar_datos_dispersos_a_densos(
            K_ordenes, I_items, J_pasillos, ordenes_dispersos, pasillos_dispersos
        )
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de instancia en {ruta_instancia}")
        return
    except Exception as e:
        print(f"Error al cargar o procesar los datos de la instancia: {e}")
        return

    # Traducir nombres a español para claridad interna del modelo
    num_ordenes_total_instancia = K_ordenes
    num_items_total_instancia = I_items
    num_pasillos_total_instancia = J_pasillos
    lim_inf_wave = L_w
    lim_sup_wave = U_w

    print(f"Instancia cargada: {num_ordenes_total_instancia} órdenes, {num_items_total_instancia} ítems, {num_pasillos_total_instancia} pasillos.")
    print(f"Límites de wave (tamaño total de ítems en O'): Lw={lim_inf_wave}, Uw={lim_sup_wave}")
    print("----------------------------------------------------")

    # Verificar validez de O' (órdenes fijas) respecto a Lw y Uw
    verificar_validez_ordenes_fijas(
        ordenes_fijas_indices_param, ordenes_matriz_W, 
        num_items_total_instancia, num_ordenes_total_instancia, 
        lim_inf_wave, lim_sup_wave
    )
    print("----------------------------------------------------")
    
    # Filtrar órdenes fijas para asegurar que los índices son válidos
    ordenes_fijas_procesar = [k_idx for k_idx in ordenes_fijas_indices_param if 0 <= k_idx < num_ordenes_total_instancia]
    if len(ordenes_fijas_procesar) != len(ordenes_fijas_indices_param):
        print(f"Advertencia: Algunas órdenes en ORDENES_FIJAS_INDICES estaban fuera de rango y fueron excluidas. Órdenes a procesar: {ordenes_fijas_procesar}")
    
    if not ordenes_fijas_procesar:
        print("Error: No hay órdenes fijas válidas para procesar. Terminando.")
        print("\\n--- SALIDA ---")
        print("NO_ORDERS_TO_PROCESS") # O un valor que indique esto
        print("")
        return

    # Calcular la demanda total de cada ítem para las órdenes fijas O' (solo válidas)
    items_requeridos_O_prima = [0] * num_items_total_instancia
    for k_idx in ordenes_fijas_procesar:
        for i_idx in range(num_items_total_instancia):
            items_requeridos_O_prima[i_idx] += ordenes_matriz_W[k_idx][i_idx]

    # Modelo PuLP: Seleccionar un conjunto mínimo de pasillos A' para satisfacer la demanda de O'
    modelo = pulp.LpProblem("Desafio_Parte2_Seleccionar_Pasillos", pulp.LpMinimize)

    # Variables de decisión: y_pasillo[j] = 1 si se selecciona el pasillo j, 0 caso contrario
    y_pasillo = pulp.LpVariable.dicts("y_pasillo", range(num_pasillos_total_instancia), cat=pulp.LpBinary)

    # Función Objetivo: Minimizar el número de pasillos seleccionados
    modelo += pulp.lpSum(y_pasillo[j] for j in range(num_pasillos_total_instancia)), "Minimizar_Pasillos_Seleccionados"

    # Restricciones:
    # Para cada ítem i, la cantidad disponible en los pasillos seleccionados A' debe ser >= a la cantidad requerida por O'
    for i in range(num_items_total_instancia):
        if items_requeridos_O_prima[i] > 0: # Solo añadir restricción si el ítem es realmente necesitado por O'
            modelo += pulp.lpSum(pasillos_matriz_S[j][i] * y_pasillo[j] for j in range(num_pasillos_total_instancia)) >= items_requeridos_O_prima[i], f"Req_Item_{i}"

    # Resolver el modelo
    print("\\nResolviendo el modelo PuLP...")
    modelo.solve()

    # Mostrar resultados
    print("----------------------------------------------------")
    # Usar modelo.status (código entero) para comparaciones, y pulp.LpStatus[modelo.status] para mostrar el string.
    print(f"Estado de la solución: {pulp.LpStatus[modelo.status]}")

    if modelo.status == pulp.LpStatusOptimal: # Comparar el código de estado directamente
        valor_objetivo = pulp.value(modelo.objective)
        # Asegurarse que y_pasillo y num_pasillos_total_instancia están definidos en este alcance
        pasillos_seleccionados_indices = [j for j in range(num_pasillos_total_instancia) if y_pasillo[j].varValue == 1]
        
        print(f"Valor objetivo (mínimo número de pasillos seleccionados): {int(valor_objetivo)}")
        print(f"Pasillos seleccionados (A') (índices 0-based): {pasillos_seleccionados_indices}")
        
        print("\\\\n--- SALIDA ---") # Doble barra para newline en f-string dentro de triple comilla
        print(int(valor_objetivo)) 
        if pasillos_seleccionados_indices:
            print(*(p_idx for p_idx in pasillos_seleccionados_indices))
        else:
            print("") # Línea vacía si no hay pasillos

        # Asegurarse que todas las variables para verificar_factibilidad_seleccion_pasillos están disponibles.
        # Esta función se llama solo si la solución es óptima.
        verificar_factibilidad_seleccion_pasillos(
            ordenes_fijas_procesar, pasillos_seleccionados_indices, 
            ordenes_matriz_W, pasillos_matriz_S, 
            num_items_total_instancia, num_ordenes_total_instancia, num_pasillos_total_instancia
        )
    elif modelo.status == pulp.LpStatusInfeasible: # Comparar el código de estado directamente
        print("El modelo es infactible. No se puede satisfacer la demanda de las órdenes fijas O' (procesadas) con los pasillos disponibles.")
        print("\\\\n--- SALIDA ---") # Doble barra
        print("INFEASIBLE") 
        print("") 
    else: # Otros estados (Undefined, Not Solved, etc.)
        print(f"No se encontró una solución óptima o el solver falló. Estado: {pulp.LpStatus[modelo.status]}")
        print("\\\\n--- SALIDA ---") # Doble barra
        print(f"NO_OPTIMAL_{pulp.LpStatus[modelo.status].replace(' ', '_')}") 
        print("")
    print("----------------------------------------------------")

if __name__ == "__main__":
    # Para ejecutar, puedes cambiar ORDENES_FIJAS_INDICES_EJEMPLO
    # o eventualmente leerlo desde argumentos de línea de comando o un archivo.
    resolver_desafio_parte2(RUTA_INSTANCIA, ORDENES_FIJAS_INDICES_EJEMPLO)

    # Ejemplo con un conjunto de órdenes más grande para probar:
    # ORDENES_TEST_GRANDES = list(range(10)) # Las primeras 10 órdenes
    # print("\\n\\n --- EJECUTANDO CON UN CONJUNTO DE ÓRDENES MÁS GRANDE ---")
    # resolver_desafio_parte2(RUTA_INSTANCIA, ORDENES_TEST_GRANDES)

    # Ejemplo con una orden que podría requerir muchos ítems o ítems raros:
    # ORDEN_ESPECIFICA = [50] # Suponiendo que la orden 50 existe y es interesante
    # print("\\n\\n --- EJECUTANDO CON UNA ORDEN ESPECÍFICA ---")
    # resolver_desafio_parte2(RUTA_INSTANCIA, ORDEN_ESPECIFICA)
