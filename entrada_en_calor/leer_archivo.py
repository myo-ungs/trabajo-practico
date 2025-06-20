from modelos import Item, Bolsita, Contenedor, Parametros

# Formato del archivo de entrada:
# - Primera línea: o (bolsitas), i (tipos de ítems), a (contenedores)

# - Siguientes o líneas: cada una indica una bolsita:
#     k seguido de k pares (tipo_item, cantidad)

# - Siguientes a líneas: cada una indica un contenedor:
#     l seguido de l pares (tipo_item, cantidad)

# - Última línea: LB y UB

# Se asume beneficio = 1 para todos los ítems y contenedores por ahora (b_o=1, b_a=1)


def cargar_parametros_desde_archivo(path: str) -> Parametros:
    with open(path, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    o, i, a = map(int, lines[0].split())

    bolsitas = []
    for idx, line in enumerate(lines[1:1 + o]):
        parts = list(map(int, line.split()))
        k = parts[0]
        # Asumiendo beneficio = 1 para cada item en la bolsita
        items = [Item(tipo=parts[j], cantidad=parts[j + 1], beneficio=1) for j in range(1, 2 * k + 1, 2)]
        bolsitas.append(Bolsita(indice=idx, items=items))

    contenedores = []
    for idx, line in enumerate(lines[1 + o:1 + o + a]):
        parts = list(map(int, line.split()))
        l = parts[0]
        # Asumiendo beneficio = 1 para cada item en el contenedor (para w_ia)
        # y beneficio del contenedor b_a = 1
        items_contenedor = [Item(tipo=parts[j], cantidad=parts[j + 1], beneficio=1) for j in range(1, 2 * l + 1, 2)]
        contenedores.append(Contenedor(indice=idx, items=items_contenedor, beneficio=1))
    
    # Leer LB y UB de la última línea si existe
    LB, UB = 0, 0 # Valores por defecto si no están
    if len(lines) > 1 + o + a:
        try:
            LB, UB = map(int, lines[1 + o + a].split())
        except ValueError:
            print(f"Advertencia: No se pudo parsear LB y UB de la línea: {lines[1 + o + a]}")
            # Mantener valores por defecto si hay error

    return Parametros(
        total_bolsitas=o,
        total_items=i,
        total_contenedores=a,
        bolsitas=bolsitas,
        contenedores=contenedores,
        LB=LB, # Añadido LB
        UB=UB  # Añadido UB
    )

def imprimir_parametros(parametros):
    print(f"Total Bolsitas: {parametros.total_bolsitas}, Total Ítems: {parametros.total_items}, Total Contenedores: {parametros.total_contenedores}")
    print(f"LB: {parametros.LB}, UB: {parametros.UB}")
    print("================== BOLSITAS ==================")
    for b in parametros.bolsitas:
        print(f"  Bolsita {b.indice}:")
        for item in b.items:
            print(f"    Item tipo {item.tipo}, cantidad {item.cantidad}, beneficio {item.beneficio}")

    print("\\n================== CONTENEDORES ==================")
    for c in parametros.contenedores:
        print(f"  Contenedor {c.indice}, beneficio {c.beneficio}:")
        for item in c.items:
            print(f"    Item tipo {item.tipo}, cantidad {item.cantidad}, beneficio {item.beneficio}")


# Funciones para cargar datos en el formato del desafío
def cargar_datos_instancia_desafio(filepath):
    """
    Carga los datos desde un archivo de instancia en el formato del desafío original.
    Formato esperado:
    Línea 1: K I J (N_ordenes, N_items, N_pasillos)
    Siguientes K líneas: Órdenes (num_tipos_item item_idx_1 qty_1 ...)
    Siguientes J líneas: Pasillos (num_tipos_item item_idx_1 qty_1 ...)
    L_w y U_w no se leen de este archivo, deben ser manejados externamente si son necesarios.
    Las coordenadas de pasillos no se leen de este archivo.
    Retorna: K_ordenes, I_items, J_pasillos, ordenes_datos_dispersos, pasillos_datos_dispersos
    """
    ordenes_datos_dispersos = []
    pasillos_datos_dispersos = []
    # pasillos_coordenadas ya no se usa aquí

    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith("//")]

    # Línea 1: K, I, J
    try:
        K_ordenes, I_items, J_pasillos = map(int, lines[0].split())
    except ValueError:
        print(f"Error: La primera línea del archivo de instancia no tiene el formato esperado (K I J). Línea: {lines[0]}")
        raise
    except IndexError:
        print(f"Error: El archivo de instancia está vacío o la primera línea no existe.")
        raise


    linea_actual_idx = 1

    # Siguientes K líneas: Órdenes
    # Formato: num_tipos_item_en_orden item_idx_1 item_qty_1 item_idx_2 item_qty_2 ...
    for num_orden in range(K_ordenes):
        if linea_actual_idx >= len(lines):
            print(f"Error: Se esperaban {K_ordenes} líneas de órdenes, pero el archivo terminó antes en la orden {num_orden + 1}.")
            raise ValueError(f"Datos de órdenes incompletos. Faltan datos para la orden {num_orden + 1}.")
        
        parts = list(map(int, lines[linea_actual_idx].split()))
        num_tipos_item_en_orden = parts[0]
        orden_items = {} 
        if len(parts) != 1 + 2 * num_tipos_item_en_orden:
            print(f"Advertencia: La línea de la orden {num_orden} (índice 0) tiene un formato inesperado. Línea: {lines[linea_actual_idx]}. Se esperaban {1 + 2 * num_tipos_item_en_orden} partes, se obtuvieron {len(parts)}. Se omitirá esta orden.")
            linea_actual_idx += 1
            ordenes_datos_dispersos.append({}) # Añadir orden vacía para mantener la cuenta y evitar errores de índice
            continue

        for i in range(num_tipos_item_en_orden):
            item_idx = parts[1 + 2 * i]
            item_qty = parts[1 + 2 * i + 1]
            # Validar item_idx si es necesario (ej. 0 <= item_idx < I_items)
            if not (0 <= item_idx < I_items):
                print(f"Advertencia: En orden {num_orden}, ítem_idx {item_idx} está fuera de rango [0, {I_items-1}). Se omitirá este ítem.")
                continue
            orden_items[item_idx] = item_qty
        ordenes_datos_dispersos.append(orden_items)
        linea_actual_idx += 1

    # Siguientes J líneas: Pasillos
    # Formato: num_tipos_item_en_pasillo item_idx_1 item_qty_1 ... (sin coordenadas)
    for num_pasillo in range(J_pasillos):
        if linea_actual_idx >= len(lines):
            print(f"Error: Se esperaban {J_pasillos} líneas de pasillos, pero el archivo terminó antes en el pasillo {num_pasillo + 1}.")
            raise ValueError(f"Datos de pasillos incompletos. Faltan datos para el pasillo {num_pasillo + 1}.")

        parts = list(map(int, lines[linea_actual_idx].split()))
        num_tipos_item_en_pasillo = parts[0]
        pasillo_items = {}
        
        if len(parts) != 1 + 2 * num_tipos_item_en_pasillo:
            print(f"Advertencia: La línea del pasillo {num_pasillo} (índice 0) tiene un formato inesperado. Línea: {lines[linea_actual_idx]}. Se esperaban {1 + 2 * num_tipos_item_en_pasillo} partes, se obtuvieron {len(parts)}. Se omitirá este pasillo.")
            linea_actual_idx += 1
            pasillos_datos_dispersos.append({}) # Añadir pasillo vacío
            continue
            
        for i in range(num_tipos_item_en_pasillo):
            item_idx = parts[1 + 2 * i]
            item_qty = parts[1 + 2 * i + 1]
            # Validar item_idx si es necesario
            if not (0 <= item_idx < I_items):
                print(f"Advertencia: En pasillo {num_pasillo}, ítem_idx {item_idx} está fuera de rango [0, {I_items-1}). Se omitirá este ítem.")
                continue
            pasillo_items[item_idx] = item_qty
        pasillos_datos_dispersos.append(pasillo_items)
        linea_actual_idx += 1
            
    # L_w, U_w y pasillos_coordenadas no se leen/retornan desde esta función según el formato original.
    return K_ordenes, I_items, J_pasillos, ordenes_datos_dispersos, pasillos_datos_dispersos

def transformar_datos_dispersos_a_densos(K_ordenes, I_items, J_pasillos, ordenes_dispersos, pasillos_dispersos):
    """
    Transforma los datos dispersos de órdenes y pasillos a matrices densas W (órdenes x ítems) y S (pasillos x ítems).
    """
    # Matriz W: W[k][i] = cantidad del ítem i en la orden k
    W_matriz = [[0 for _ in range(I_items)] for _ in range(K_ordenes)]
    # Matriz S: S[j][i] = cantidad del ítem i en el pasillo j
    S_matriz = [[0 for _ in range(I_items)] for _ in range(J_pasillos)]

    for idx_orden, items_orden in enumerate(ordenes_dispersos):
        for idx_item, cantidad in items_orden.items():
            if 0 <= idx_item < I_items: # Validar que el índice del ítem esté en rango
                W_matriz[idx_orden][idx_item] = cantidad
            else:
                print(f"Advertencia: Índice de ítem {idx_item} en orden {idx_orden} fuera de rango (0 a {I_items-1}). Se omitirá.")

    for idx_pasillo, items_pasillo in enumerate(pasillos_dispersos):
        for idx_item, cantidad in items_pasillo.items():
            if 0 <= idx_item < I_items: # Validar que el índice del ítem esté en rango
                S_matriz[idx_pasillo][idx_item] = cantidad
            else:
                print(f"Advertencia: Índice de ítem {idx_item} en pasillo {idx_pasillo} fuera de rango (0 a {I_items-1}). Se omitirá.")
                
    return W_matriz, S_matriz

# Ejemplo de uso
if __name__ == "__main__":
    # Crear una carpeta 'datos_desafio' en el mismo directorio que este script
    # y colocar allí 'instance_0001.txt' con el formato del desafío.
    # Ejemplo de ruta al archivo de instancia del desafío:
    # path_desafio = "datos_desafio/instance_0001.txt" 
    # K, I, J, Lw, Uw, ordenes_sp, pasillos_sp, coords = cargar_datos_instancia_desafio(path_desafio)
    # W, S = transformar_datos_dispersos_a_densos(K, I, J, ordenes_sp, pasillos_sp)
    # print(f"K={K}, I={I}, J={J}, Lw={Lw}, Uw={Uw}")
    # print("Matriz W (primeras 5 órdenes, primeros 10 ítems):")
    # for k_idx in range(min(K, 5)):
    #     print(W[k_idx][:min(I,10)])
    # print("Matriz S (primeros 5 pasillos, primeros 10 ítems):")
    # for j_idx in range(min(J, 5)):
    #     print(S[j_idx][:min(I,10)])

    # Prueba con el formato original del TP
    parametros_tp = cargar_parametros_desde_archivo("entrada_test.txt")
    imprimir_parametros(parametros_tp)