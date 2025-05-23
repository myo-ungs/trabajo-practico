import pulp
import os
from leer_archivo import cargar_datos_instancia_desafio, transformar_datos_dispersos_a_densos

# --- Parámetros Globales y Constantes ---
EPSILON = 1e-6  # Pequeño valor para comparar costos reducidos
MAX_ITERACIONES_CG = 100 # Límite de iteraciones para la generación de columnas

# --- Funciones Auxiliares ---
def valor_total_items_en_ordenes(ordenes_indices, ordenes_matriz_W, num_items_total):
    """Calcula el valor total (cantidad) de ítems en un conjunto de órdenes."""
    total_items = 0
    if not ordenes_indices:
        return 0
    for orden_idx in ordenes_indices:
        if 0 <= orden_idx < len(ordenes_matriz_W):
            for item_idx in range(num_items_total):
                total_items += ordenes_matriz_W[orden_idx][item_idx]
    return total_items

# --- Subproblema (Pricing Problem por Pasillo) ---
def resolver_subproblema_por_pasillo(
    pasillo_idx_actual, K_ordenes, I_items, L_w, U_w,
    ordenes_matriz_W, stock_del_pasillo_S_a, duales_pi_k,
    nombre_problema_base="Subproblema_Pasillo"
):
    """
    Resuelve el subproblema de pricing para un pasillo específico 'a' de A_fijo.
    Encuentra un conjunto de órdenes O_a^* que, servidas por el pasillo 'a',
    maximiza (valor_ordenes - sum_k pi_k).
    """
    modelo_sub = pulp.LpProblem(f"{nombre_problema_base}_{pasillo_idx_actual}", pulp.LpMaximize)

    # Variables de decisión: y_k = 1 si la orden k se incluye en el patrón para este pasillo
    y_vars_sub = pulp.LpVariable.dicts(f"y_sub_p{pasillo_idx_actual}", range(K_ordenes), cat=pulp.LpBinary)

    # Coeficientes del objetivo para el subproblema: (valor_orden_k - pi_k)
    # valor_orden_k = sum_i W_ki
    coeficientes_obj_sub = []
    for k in range(K_ordenes):
        valor_orden_k = sum(ordenes_matriz_W[k][i] for i in range(I_items))
        coeficientes_obj_sub.append(valor_orden_k - duales_pi_k[k])

    modelo_sub += pulp.lpSum(coeficientes_obj_sub[k] * y_vars_sub[k] for k in range(K_ordenes)), "Max_Costo_Reducido_Patron"

    # Restricciones del subproblema:
    # 1. Disponibilidad de ítems en el pasillo actual 'a'
    for i in range(I_items):
        modelo_sub += pulp.lpSum(ordenes_matriz_W[k][i] * y_vars_sub[k] for k in range(K_ordenes)) <= stock_del_pasillo_S_a[i], f"Disp_Item_{i}_Pasillo_{pasillo_idx_actual}"

    # 2. Límites de la wave (L_w, U_w) para el conjunto de órdenes seleccionadas
    items_seleccionados_expr = pulp.lpSum(
        ordenes_matriz_W[k][i] * y_vars_sub[k] for k in range(K_ordenes) for i in range(I_items)
    )
    modelo_sub += items_seleccionados_expr >= L_w, f"Limite_Inferior_Wave_Pasillo_{pasillo_idx_actual}"
    modelo_sub += items_seleccionados_expr <= U_w, f"Limite_Superior_Wave_Pasillo_{pasillo_idx_actual}"

    # Resolver el subproblema
    modelo_sub.solve(pulp.PULP_CBC_CMD(msg=0)) # msg=0 para silenciar output del solver

    if pulp.LpStatus[modelo_sub.status] == pulp.LpStatusOptimal:
        costo_reducido = pulp.value(modelo_sub.objective)
        if costo_reducido > EPSILON:
            ordenes_nuevo_patron = [k for k in range(K_ordenes) if y_vars_sub[k].varValue > 0.5]
            if not ordenes_nuevo_patron: # Si es óptimo pero no selecciona órdenes (ej. Lw > 0 y no se cumple)
                return None
            
            valor_original_patron = valor_total_items_en_ordenes(ordenes_nuevo_patron, ordenes_matriz_W, I_items)
            
            return {
                "ordenes_indices": ordenes_nuevo_patron,
                "pasillo_idx": pasillo_idx_actual,
                "valor_original": valor_original_patron,
                "costo_reducido": costo_reducido
            }
    return None

# --- Restricted Master Problem (RMP) ---
def resolver_rmp(lista_patrones, K_ordenes, es_lp_relaxation=True, nombre_problema="RMP"):
    """
    Resuelve el Restricted Master Problem (RMP).
    Si es_lp_relaxation es True, resuelve la relajación lineal y devuelve duales.
    Si es_lp_relaxation es False, resuelve como ILP.
    """
    if not lista_patrones:
        # print("Advertencia: No hay patrones para resolver el RMP.")
        # Para el LP inicial, si no hay patrones, los duales serían 0 o no definidos.
        # Para el ILP final, si no hay patrones, la solución es 0.
        if es_lp_relaxation:
            # Para un RMP vacío, todos los duales son efectivamente cero.
            # Devolver LpStatusOptimal permite que la GC proceda con la fijación de precios del subproblema usando estos duales cero.
            return None, [0.0] * K_ordenes, pulp.LpStatusOptimal # MODIFICADO: estado y comentario -> Traducido
        else: # Resolviendo ILP final y no hay patrones
            return 0, [], [], pulp.LpStatusOptimal


    modelo_rmp = pulp.LpProblem(nombre_problema, pulp.LpMaximize)

    # Variables de decisión: lambda_p = 1 si el patrón p se selecciona
    cat_var = pulp.LpContinuous if es_lp_relaxation else pulp.LpBinary
    lower_bound = 0
    # MODIFICADO: upBound debe ser 1 para la relajación LP de set packing.
    # Original: upper_bound = None if es_lp_relaxation else 1
    upper_bound = 1

    lambda_vars = pulp.LpVariable.dicts("lambda", range(len(lista_patrones)), lowBound=lower_bound, upBound=upper_bound, cat=cat_var)

    # Función Objetivo: Maximizar el valor total de los ítems en los patrones seleccionados
    modelo_rmp += pulp.lpSum(lista_patrones[p_idx]["valor_original"] * lambda_vars[p_idx] for p_idx in range(len(lista_patrones))), "Max_Items_Patrones_Seleccionados"

    # Restricciones:
    # 1. Cada orden k puede ser cubierta por como máximo un patrón seleccionado
    #    sum_{p | k en O_p} lambda_p <= 1   (para cada orden k)
    for k_idx in range(K_ordenes):
        expr_cobertura_orden = pulp.lpSum(
            lambda_vars[p_idx] for p_idx, patron in enumerate(lista_patrones) if k_idx in patron["ordenes_indices"]
        )
        # Solo añadir si hay patrones que cubren esta orden (i.e., si la expresión tiene variables)
        # Si expr_cobertura_orden es 0 (un número), significa que lpSum([]) fue llamado.
        if isinstance(expr_cobertura_orden, pulp.LpAffineExpression):
             modelo_rmp += expr_cobertura_orden <= 1, f"Cobertura_Orden_{k_idx}"
        # else: # Si ninguna columna actual contiene la orden k, expr_cobertura_orden será 0.
             # La restricción 0 <= 1 es trivial. No la añadimos.
             # El dual pi_k para esta orden k_idx permanecerá 0 (su valor inicial), lo cual es correcto.

    # Resolver el RMP
    modelo_rmp.solve(pulp.PULP_CBC_CMD(msg=0))
    
    estado_solver = modelo_rmp.status # Obtener el código de estado entero

    if es_lp_relaxation:
        duales_pi_k = [0.0] * K_ordenes
        if estado_solver == pulp.LpStatusOptimal: # Comparar con la constante entera de PuLP
            for k_idx in range(K_ordenes):
                nombre_restriccion = f"Cobertura_Orden_{k_idx}"
                if nombre_restriccion in modelo_rmp.constraints:
                    # MODIFICADO: El dual pi_k para Max problema, restricción <=, es usualmente >= 0.
                    # El costo reducido es c_j - pi^T A_j. Subproblema maximiza valor_patron - sum(pi_k).
                    # Entonces duales_pi_k[k] debe ser pi_k.
                    # Original: duales_pi_k[k_idx] = -modelo_rmp.constraints[nombre_restriccion].pi
                    duales_pi_k[k_idx] = modelo_rmp.constraints[nombre_restriccion].pi
        return modelo_rmp, duales_pi_k, estado_solver # Devolver estado_solver (entero)
    else: # Resolviendo ILP
        if estado_solver == pulp.LpStatusOptimal: # Comparar con la constante entera de PuLP
            valor_objetivo = pulp.value(modelo_rmp.objective)
            patrones_seleccionados_final = []
            ordenes_seleccionadas_final_set = set()

            for p_idx in range(len(lista_patrones)):
                if lambda_vars[p_idx].varValue > 0.5:
                    patron_sel = lista_patrones[p_idx]
                    patrones_seleccionados_final.append(patron_sel)
                    for orden_idx in patron_sel["ordenes_indices"]:
                        ordenes_seleccionadas_final_set.add(orden_idx)
            
            return valor_objetivo, sorted(list(ordenes_seleccionadas_final_set)), patrones_seleccionados_final, estado_solver
        else:
            return 0, [], [], estado_solver

# --- Generación de Columnas Iniciales ---
def generar_patrones_iniciales(K_ordenes, I_items, pasillos_fijos_A_prima_indices,
                               pasillos_matriz_S, ordenes_matriz_W, L_w, U_w):
    """
    Genera un conjunto básico de patrones iniciales.
    Ej: Para cada pasillo en A_fijo, y para cada orden, si la orden puede ser
    satisfecha por ese pasillo y cumple Lw/Uw, se crea un patrón (orden, pasillo).
    """
    patrones_iniciales = []
    for pasillo_idx in pasillos_fijos_A_prima_indices:
        stock_pasillo_actual = pasillos_matriz_S[pasillo_idx]
        for k_idx in range(K_ordenes):
            orden_actual_indices = [k_idx]
            items_en_orden = valor_total_items_en_ordenes(orden_actual_indices, ordenes_matriz_W, I_items)

            if L_w <= items_en_orden <= U_w:
                factible_stock_pasillo = True
                for i_idx in range(I_items):
                    if ordenes_matriz_W[k_idx][i_idx] > stock_pasillo_actual[i_idx]:
                        factible_stock_pasillo = False
                        break
                
                if factible_stock_pasillo:
                    patrones_iniciales.append({
                        "ordenes_indices": orden_actual_indices,
                        "pasillo_idx": pasillo_idx,
                        "valor_original": items_en_orden,
                        # "costo_reducido" no es necesario para patrones iniciales directos
                    })
    # print(f"Generados {len(patrones_iniciales)} patrones iniciales.")
    return patrones_iniciales

# --- Función Principal de Generación de Columnas (Set-Packing) ---
def resolver_desafio_parte3_cg_setpacking(ruta_instancia, pasillos_fijos_A_prima_indices_param, L_w, U_w): # MODIFICADO: Añadir L_w, U_w
    print(f"Iniciando Desafío Parte 3 (CG Set-Packing para A' fijo: {pasillos_fijos_A_prima_indices_param}, optimizando O')")
    print(f"Ruta de instancia: {ruta_instancia}")
    print(f"Límites de wave (Lw, Uw) proporcionados: ({L_w}, {U_w})") # NUEVO PRINT
    print("----------------------------------------------------")

    # Cargar datos
    try:
        # MODIFICADO: cargar_datos_instancia_desafio ya no devuelve L_w, U_w
        datos_brutos = cargar_datos_instancia_desafio(ruta_instancia)
        # K_ordenes, I_items, J_pasillos_total, L_w, U_w, ordenes_dispersos, pasillos_dispersos, _ = datos_brutos
        K_ordenes, I_items, J_pasillos_total, ordenes_dispersos, pasillos_dispersos = datos_brutos # MODIFICADO (eliminado el underscore al final)
        
        ordenes_matriz_W, pasillos_matriz_S = transformar_datos_dispersos_a_densos(
            K_ordenes, I_items, J_pasillos_total, ordenes_dispersos, pasillos_dispersos
        )
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de instancia en {ruta_instancia}")
        return
    except Exception as e:
        print(f"Error al cargar o procesar los datos de la instancia: {e}")
        return

    print(f"Instancia cargada: {K_ordenes} órdenes, {I_items} ítems, {J_pasillos_total} pasillos en total.")
    # print(f"Límites de wave (Lw, Uw): ({L_w}, {U_w})") # ELIMINADO: L_w, U_w ahora son parámetros
    print(f"Pasillos A' fijos para esta ejecución (índices 0-based): {pasillos_fijos_A_prima_indices_param}")

    if not pasillos_fijos_A_prima_indices_param:
        print("Advertencia: El conjunto A' de pasillos fijos está vacío.")
        # Si A' es vacío, no se pueden formar patrones, el resultado es 0.
        print("\n--- SALIDA ---")
        print(0) # Valor objetivo
        print(0) # Num ordenes seleccionadas
        print("") # Indices ordenes (vacío)
        print(0) # Num pasillos en A'
        print("") # Indices pasillos A' (vacío)
        return

    # Validar que los índices de pasillos_fijos_A_prima_indices_param son válidos
    for p_idx in pasillos_fijos_A_prima_indices_param:
        if not (0 <= p_idx < J_pasillos_total):
            print(f"Error: Índice de pasillo {p_idx} en A' está fuera de rango (0 a {J_pasillos_total-1}).")
            return
    
    # Inicializar lista de patrones
    lista_patrones_global = generar_patrones_iniciales(
        K_ordenes, I_items, pasillos_fijos_A_prima_indices_param,
        pasillos_matriz_S, ordenes_matriz_W, L_w, U_w
    )
    print(f"Se generaron {len(lista_patrones_global)} patrones iniciales.")

    if not lista_patrones_global and L_w > 0 : # Si no hay patrones iniciales y Lw > 0, puede ser infactible
        pass # Continuar, el RMP inicial podría ser infactible y los duales llevar a algo o no.

    # Bucle de Generación de Columnas
    for iteracion_cg in range(MAX_ITERACIONES_CG):
        print(f"\\n--- Iteración CG: {iteracion_cg + 1} ---")
        print(f"Número actual de patrones en RMP: {len(lista_patrones_global)}")

        # Resolver RMP (Relajación Lineal) para obtener duales
        modelo_rmp_lp, duales_pi_k, estado_rmp_lp = resolver_rmp(
            lista_patrones_global, K_ordenes, es_lp_relaxation=True, nombre_problema=f"RMP_LP_Iter_{iteracion_cg}"
        )

        if estado_rmp_lp != pulp.LpStatusOptimal:
            print(f"RMP (LP) no encontró solución óptima (Estado: {pulp.LpStatus[estado_rmp_lp]}). Terminando CG.") # Usar pulp.LpStatus[] para mostrar string
            break
        
        # print(f"Duales pi_k (primeros 10): {[round(d, 2) for d in duales_pi_k[:10]]}")

        # Resolver Subproblemas (uno por cada pasillo en A_fijo)
        nuevos_patrones_encontrados_iter = 0
        for pasillo_idx_en_A_fijo in pasillos_fijos_A_prima_indices_param:
            stock_pasillo_actual = pasillos_matriz_S[pasillo_idx_en_A_fijo]
            
            # print(f"Resolviendo subproblema para pasillo {pasillo_idx_en_A_fijo}...")
            nuevo_patron_info = resolver_subproblema_por_pasillo(
                pasillo_idx_en_A_fijo, K_ordenes, I_items, L_w, U_w,
                ordenes_matriz_W, stock_pasillo_actual, duales_pi_k,
                nombre_problema_base=f"Sub_P{pasillo_idx_en_A_fijo}_Iter{iteracion_cg}"
            )

            if nuevo_patron_info:
                # print(f"  Nuevo patrón encontrado para pasillo {pasillo_idx_en_A_fijo} con costo reducido > epsilon ({nuevo_patron_info['costo_reducido']:.4f}).")
                # print(f"  Órdenes: {nuevo_patron_info['ordenes_indices']}, Valor: {nuevo_patron_info['valor_original']}")
                
                # Evitar añadir duplicados exactos (órdenes y pasillo)
                patron_existente = False
                for p_existente in lista_patrones_global:
                    if (p_existente["ordenes_indices"] == nuevo_patron_info["ordenes_indices"] and
                        p_existente["pasillo_idx"] == nuevo_patron_info["pasillo_idx"]):
                        patron_existente = True
                        break
                if not patron_existente:
                    lista_patrones_global.append(nuevo_patron_info)
                    nuevos_patrones_encontrados_iter += 1
                # else:
                #    print("  El patrón generado ya existe en la lista global. No se añade.")
        
        if nuevos_patrones_encontrados_iter > 0:
            print(f"Se añadieron {nuevos_patrones_encontrados_iter} nuevos patrones al RMP.")
        else:
            print("No se encontraron nuevos patrones con costo reducido positivo en ningún subproblema. CG terminada (óptimo LP alcanzado).")
            break
        
        if iteracion_cg == MAX_ITERACIONES_CG - 1:
            print("Se alcanzó el número máximo de iteraciones de CG.")

    # Fin del bucle de Generación de Columnas
    print("\n--- Fin de Generación de Columnas ---")
    print(f"Total de patrones generados: {len(lista_patrones_global)}")
    
    # Resolver el RMP final como ILP con todos los patrones generados
    print("Resolviendo RMP final como ILP...")
    if not lista_patrones_global:
        print("No hay patrones generados. La solución es vacía.")
        valor_objetivo_final = 0
        ordenes_seleccionadas_final = []
        # patrones_seleccionados_final = [] # No es necesario para el output
        estado_rmp_final = pulp.LpStatusOptimal # Técnicamente, es óptimo en 0.
    else:
        valor_objetivo_final, ordenes_seleccionadas_final, patrones_seleccionados_final_info, estado_rmp_final = resolver_rmp(
            lista_patrones_global, K_ordenes, es_lp_relaxation=False, nombre_problema="RMP_Final_ILP"
        )

    if estado_rmp_final == pulp.LpStatusOptimal:
        print(f"Solución Óptima Encontrada (después de CG y RMP ILP).")
        print(f"Valor Objetivo (total items): {valor_objetivo_final}")
        print(f"Órdenes seleccionadas (O') (índices 0-based, {len(ordenes_seleccionadas_final)} órdenes): {ordenes_seleccionadas_final}")
        # print(f"Número de patrones seleccionados en la solución final: {len(patrones_seleccionados_final_info)}")
        # for i, p_info in enumerate(patrones_seleccionados_final_info):
        #    print(f"  Patrón {i+1}: Órdenes {p_info['ordenes_indices']}, Pasillo {p_info['pasillo_idx']}, Valor {p_info['valor_original']}")

        print("\\n--- SALIDA ---")
        print(int(round(valor_objetivo_final if valor_objetivo_final is not None else 0)))
        print(len(ordenes_seleccionadas_final))
        if ordenes_seleccionadas_final:
            print(*(o_idx for o_idx in ordenes_seleccionadas_final))
        else:
            print("") # Línea vacía si no hay órdenes
        
        print(len(pasillos_fijos_A_prima_indices_param))
        if pasillos_fijos_A_prima_indices_param:
            print(*(p_idx for p_idx in pasillos_fijos_A_prima_indices_param))
        else:
            print("")

    else:
        print(f"RMP Final (ILP) no encontró solución óptima. Estado: {pulp.LpStatus[estado_rmp_final]}") # Usar pulp.LpStatus[] para mostrar string
        print("Esto podría indicar un problema si se esperaba una solución (ej. RMP infactible o no acotado).")
        print("\n--- SALIDA ---")
        print(0) # Valor objetivo
        print(0) # Num ordenes
        print("") # Indices ordenes
        print(len(pasillos_fijos_A_prima_indices_param))
        if pasillos_fijos_A_prima_indices_param:
            print(*(p_idx for p_idx in pasillos_fijos_A_prima_indices_param))
        else:
            print("")

    print("----------------------------------------------------")


if __name__ == "__main__":
    directorio_base = os.path.dirname(os.path.abspath(__file__))
    nombre_archivo_instancia = "instance_0001.txt" # Asegúrate que este archivo exista y sea correcto
    ruta_instancia_defecto = os.path.join(directorio_base, "datos_desafio", nombre_archivo_instancia)

    # Definir L_w y U_w de ejemplo (estos serían parámetros externos en un caso real)
    L_W_EJEMPLO = 1   # Límite inferior de items en una wave
    U_W_EJEMPLO = 150 # Límite superior de items en una wave

    # Determinar J_pasillos_total para definir A' de ejemplo
    J_pasillos_total_ejemplo = 0
    try:
        # Carga mínima solo para obtener J_pasillos_total
        # Asumiendo que la primera línea tiene K I J ... (y no Lw, Uw como antes)
        with open(ruta_instancia_defecto, 'r') as f_temp:
            line1_parts = f_temp.readline().strip().split()
            if len(line1_parts) >= 3: # K, I, J son los primeros
                 J_pasillos_total_ejemplo = int(line1_parts[2])
            else: # Formato inesperado, usar un default
                print(f"Advertencia: Formato de primera línea inesperado en {ruta_instancia_defecto}. Se usará J_pasillos_total=10 por defecto para A'.")
                J_pasillos_total_ejemplo = 10
    except FileNotFoundError:
        print(f"Error: Archivo de instancia {ruta_instancia_defecto} no encontrado. Usando J_pasillos_total=0 para A'.")
        J_pasillos_total_ejemplo = 0 # No se pueden definir pasillos
    except Exception as e:
        print(f"No se pudo leer J_pasillos_total para definir A' de ejemplo desde {ruta_instancia_defecto}: {e}")
        J_pasillos_total_ejemplo = 10 # Un valor por defecto si falla la lectura

    # Definir A' (pasillos fijos) para el Desafío ($A'|O$)
    # Ejemplo: los primeros dos pasillos, o uno en el medio, etc.
    PASILLOS_FIJOS_A_PRIMA_EJEMPLO = []
    if J_pasillos_total_ejemplo >= 2:
        PASILLOS_FIJOS_A_PRIMA_EJEMPLO = [0, J_pasillos_total_ejemplo // 2] 
        # PASILLOS_FIJOS_A_PRIMA_EJEMPLO = list(range(J_pasillos_total_ejemplo)) # Usar todos los pasillos
    elif J_pasillos_total_ejemplo == 1:
        PASILLOS_FIJOS_A_PRIMA_EJEMPLO = [0]
    
    print(f"Ejecutando con A' de ejemplo: {PASILLOS_FIJOS_A_PRIMA_EJEMPLO} (basado en J_pasillos_total={J_pasillos_total_ejemplo})")
    # MODIFICADO: Pasar L_W_EJEMPLO y U_W_EJEMPLO
    resolver_desafio_parte3_cg_setpacking(ruta_instancia_defecto, PASILLOS_FIJOS_A_PRIMA_EJEMPLO, L_W_EJEMPLO, U_W_EJEMPLO)

    # --- Otros ejemplos de ejecución (descomentar para probar) ---
    # print("\\n--- Ejecutando con A' vacío ---")
    # resolver_desafio_parte3_cg_setpacking(ruta_instancia_defecto, [], L_W_EJEMPLO, U_W_EJEMPLO)

    # if J_pasillos_total_ejemplo > 0:
    #    print(f"\\n--- Ejecutando con A' = primer pasillo ([0]) ---")
    #    resolver_desafio_parte3_cg_setpacking(ruta_instancia_defecto, [0], L_W_EJEMPLO, U_W_EJEMPLO)

    # if J_pasillos_total_ejemplo > 2:
    #    print(f"\\n--- Ejecutando con A' = pasillos [0, 1, 2] ---")
    #    resolver_desafio_parte3_cg_setpacking(ruta_instancia_defecto, [0, 1, 2], L_W_EJEMPLO, U_W_EJEMPLO)
    
    # Para probar con todas las instancias del dataset 'a'
    # dir_instancias_a = os.path.join(directorio_base, "challenge-sbpo-2025", "datasets", "a")
    # if os.path.exists(dir_instancias_a):
    #     for i in range(1, 21): # instance_0001.txt a instance_0020.txt
    #         nombre_instancia = f"instance_{i:04d}.txt"
    #         ruta_instancia_actual = os.path.join(dir_instancias_a, nombre_instancia)
    #         if os.path.exists(ruta_instancia_actual):
    #             print(f"\n\n ========== PROCESANDO {nombre_instancia} ==========")
    #             # Aquí necesitarías una lógica para definir A' para cada instancia,
    #             # o usar un A' fijo de ejemplo como arriba.
    #             # Para este ejemplo, usaremos el mismo A' derivado de la primera instancia leída, y los mismos Lw, Uw.
    #             resolver_desafio_parte3_cg_setpacking(ruta_instancia_actual, PASILLOS_FIJOS_A_PRIMA_EJEMPLO, L_W_EJEMPLO, U_W_EJEMPLO)
    #         else:
    #             print(f"Instancia {ruta_instancia_actual} no encontrada.")
    # else:
    #     print(f"Directorio de instancias 'a' no encontrado en {dir_instancias_a}")
