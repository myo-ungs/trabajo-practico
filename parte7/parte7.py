import os
import sys
import csv
import time
import numpy as np
from columns_solver_enhanced import Columns
from fast_solver import FastSolver

# Agregar el directorio padre al path para importar cargar_input
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cargar_input import leer_input

def verificar_solucion_completa(W, S, LB, UB, pasillos_sel, ordenes_sel, valor_obj_reportado, nombre_instancia=""):
    """
    Verifica si una solución es factible y calcula su valor objetivo real
    usando directamente los datos de la instancia (W, S, LB, UB)
    """
    print(f"\n🔍 === VERIFICACIÓN COMPLETA DE LA SOLUCIÓN ===")
    if nombre_instancia:
        print(f"📂 Instancia: {nombre_instancia}")
    print(f"📊 Datos: {len(W)} órdenes, {len(S)} pasillos, LB={LB}, UB={UB}")
    print(f"🎯 Valor objetivo reportado: {valor_obj_reportado}")
    print()
    
    # 1. Verificar que los índices son válidos
    if pasillos_sel and max(pasillos_sel) >= len(S):
        print("❌ ERROR: Índice de pasillo inválido")
        return False
    
    if ordenes_sel and max(ordenes_sel) >= len(W):
        print("❌ ERROR: Índice de orden inválido")
        return False
    
    # 2. Calcular capacidad total disponible
    n_items = len(W[0]) if W else 0
    capacidad_total = [0] * n_items
    
    for p in pasillos_sel:
        for i in range(min(len(S[p]), n_items)):
            capacidad_total[i] += S[p][i]
    
    print(f"📦 Capacidad total disponible (primeros 5 ítems): {capacidad_total[:5]}")
    
    # 3. Calcular demanda total de las órdenes seleccionadas
    demanda_total = [0] * n_items
    valor_objetivo_real = 0
    
    for o in ordenes_sel:
        valor_objetivo_real += sum(W[o])  # Beneficio de la orden
        for i in range(min(len(W[o]), n_items)):
            demanda_total[i] += W[o][i]
    
    print(f"📊 Demanda total (primeros 5 ítems): {demanda_total[:5]}")
    print(f"💰 Valor objetivo calculado: {valor_objetivo_real}")
    
    # 4. Verificar restricciones de capacidad
    factible = True
    violaciones_count = 0
    for i in range(n_items):
        if demanda_total[i] > capacidad_total[i]:
            if violaciones_count < 5:  # Mostrar solo las primeras 5 violaciones
                print(f"❌ VIOLACIÓN en ítem {i}: demanda={demanda_total[i]} > capacidad={capacidad_total[i]}")
            violaciones_count += 1
            factible = False
    
    if violaciones_count > 5:
        print(f"❌ ... y {violaciones_count - 5} violaciones más")
    
    # 5. Verificar límites LB y UB
    if valor_objetivo_real < LB:
        print(f"❌ Viola límite inferior: {valor_objetivo_real} < {LB}")
        factible = False
    
    if valor_objetivo_real > UB:
        print(f"❌ Viola límite superior: {valor_objetivo_real} > {UB}")
        factible = False
    
    # 6. Verificar concordancia con valor reportado
    if valor_objetivo_real != valor_obj_reportado:
        print(f"⚠️ DISCREPANCIA: Calculado={valor_objetivo_real}, Reportado={valor_obj_reportado}")
    
    # Resultado final
    if factible and valor_objetivo_real == valor_obj_reportado:
        print(f"✅ SOLUCIÓN VÁLIDA Y FACTIBLE")
        print(f"📈 Utilización de límite superior: {valor_objetivo_real}/{UB} = {100*valor_objetivo_real/UB:.1f}%")
        if valor_objetivo_real == UB:
            print(f"🎯 ¡SOLUCIÓN ÓPTIMA! (alcanza el límite superior)")
        return True
    else:
        print(f"❌ SOLUCIÓN INVÁLIDA")
        return False

def escribir_csv(metrica_dict, csv_path, modelos):
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Instancia", "Métrica", "Sección 5", "Col. iniciales", "Rankear", "Eliminar col."])
        metricas = [
            ("Restricciones", 'restricciones'),
            ("# variables inicial", 'variables'),
            ("# variables en últ. maestro", 'variables_final'),
            ("Cota dual", 'cota_dual'),
            ("Mejor objetivo", 'mejor_objetivo'),
            ("Tiempo (seg)", 'tiempo_ejecucion'),
            ("Solución válida", 'solucion_valida'),
        ]
        modelo_a_columna = {
            'modelo7': 3,  # Columna "Rankear" para modelo7
        }
        for instancia, modelos_metricas in metrica_dict.items():
            first = True
            for nombre_metrica, clave in metricas:
                row = [instancia if first else '', nombre_metrica, '', '', '', '']
                for modelo in modelos:
                    m = modelos_metricas.get(modelo, {})
                    valor = m.get(clave, '')
                    col_idx = modelo_a_columna.get(modelo, None)
                    if col_idx is not None:
                        row[col_idx] = valor
                writer.writerow(row)
                first = False

def optimizar_instancia_grande(W, S, LB, UB, max_ordenes=2000, max_pasillos=50):
    """
    Reduce el tamaño de instancias grandes para hacerlas manejables
    """
    print(f"🔧 Optimizando instancia: {len(W)} órdenes → {min(len(W), max_ordenes)}")
    print(f"🔧 Optimizando pasillos: {len(S)} pasillos → {min(len(S), max_pasillos)}")
    
    original_W_len = len(W)
    
    # 1. Limitar número de órdenes (tomar las más prometedoras)
    if len(W) > max_ordenes:
        # Calcular beneficio total por orden
        beneficios_orden = [sum(orden) for orden in W]
        indices_mejores = sorted(range(len(beneficios_orden)), 
                               key=lambda i: beneficios_orden[i], reverse=True)[:max_ordenes]
        W = [W[i] for i in sorted(indices_mejores)]
        print(f"✅ Reducido a {len(W)} órdenes más prometedoras")
    
    # 2. Limitar número de pasillos (tomar los de mayor capacidad)
    if len(S) > max_pasillos:
        capacidades_pasillo = [sum(pasillo) for pasillo in S]
        indices_mejores = sorted(range(len(capacidades_pasillo)), 
                                key=lambda i: capacidades_pasillo[i], reverse=True)[:max_pasillos]
        S = [S[i] for i in sorted(indices_mejores)]
        print(f"✅ Reducido a {len(S)} pasillos de mayor capacidad")
    
    # 3. Ajustar LB y UB proporcionalmente SOLO si hubo reducción significativa
    if original_W_len > max_ordenes:
        factor_reduccion = len(W) / original_W_len
        nuevo_LB = max(1, int(LB * factor_reduccion))
        nuevo_UB = int(UB * factor_reduccion)
        print(f"✅ Ajustados límites: LB={LB}→{nuevo_LB}, UB={UB}→{nuevo_UB}")
        return W, S, nuevo_LB, nuevo_UB
    else:
        print(f"✅ Límites mantenidos: LB={LB}, UB={UB}")
        return W, S, LB, UB

# =========================
#   MAIN SCRIPT
# =========================

# Cargar datos desde archivo
archivo_input = "../datos_de_entrada/B/instance_0014.txt"
W, S, LB, UB = leer_input(archivo_input)

print(f"📊 Instancia cargada: {len(W)} órdenes, {len(S)} pasillos, LB={LB}, UB={UB}")

# Decidir qué solver usar basado en el tamaño ORIGINAL
instancia_muy_grande = len(W) > 5000  # Solo basado en órdenes para dataset B
usar_fast_solver = True  # FORZAR FastSolver para probar en instancia pequeña

# Optimizar instancia SOLO si es realmente grande (dataset B)
if instancia_muy_grande:
    print("⚠️ Instancia muy grande detectada. Aplicando optimizaciones...")
    W, S, LB, UB = optimizar_instancia_grande(W, S, LB, UB, max_ordenes=1000, max_pasillos=30)

# Elegir solver según la decisión previa
print(f"⏱️ Iniciando resolución...")
inicio_tiempo = time.time()

if usar_fast_solver:
    print("🚀 Usando FastSolver para instancia grande...")
    solver = FastSolver(W, S, LB, UB)
    resultado = solver.Opt_ExplorarCantidadPasillos(300)
    
    # Verificar factibilidad de la solución
    if resultado:
        verificacion = solver.verificar_factibilidad(resultado)
        print(f"📋 Verificación: factible={verificacion['factible']}, violaciones={verificacion['violaciones']}")
        print(f"💰 Valor real={verificacion['valor_real']}, reportado={verificacion['valor_reportado']}")
        
        if not verificacion['factible']:
            print("⚠️ La solución del FastSolver no es factible. Intentando con solver completo...")
            print("🔧 Usando solver completo sin reducción adicional...")
            # NO reducir más - usar la instancia original para el fallback
            solver = Columns(W, S, LB, UB)
            resultado = solver.Opt_ExplorarCantidadPasillos(600)  # Más tiempo para el fallback
            print("✅ Solución obtenida con solver completo")
        else:
            print("✅ Solución del FastSolver es factible")
else:
    # Instanciar y ejecutar con solver normal para instancias pequeñas
    print("🔧 Usando Columns (solver normal) para instancia pequeña...")
    solver = Columns(W, S, LB, UB)
    resultado = solver.Opt_ExplorarCantidadPasillos(600)  # Más tiempo para instancias pequeñas

fin_tiempo = time.time()
tiempo_total = fin_tiempo - inicio_tiempo

if resultado:
    print("=== RESULTADO FINAL ===")
    print("Valor objetivo:", resultado["valor_objetivo"])
    print("Pasillos seleccionados:", resultado["pasillos_seleccionados"])
    print("Órdenes seleccionadas:", resultado["ordenes_seleccionadas"])
    print(f"⏱️ Tiempo total de ejecución: {tiempo_total:.2f} segundos")
    
    # ========== VERIFICACIÓN AUTOMÁTICA DE LA SOLUCIÓN ==========
    print("\n" + "="*60)
    print("🔬 INICIANDO VERIFICACIÓN AUTOMÁTICA DE LA SOLUCIÓN")
    print("="*60)
    
    # Convertir a listas si es necesario
    pasillos_lista = list(resultado["pasillos_seleccionados"]) if not isinstance(resultado["pasillos_seleccionados"], list) else resultado["pasillos_seleccionados"]
    ordenes_lista = list(resultado["ordenes_seleccionadas"]) if not isinstance(resultado["ordenes_seleccionadas"], list) else resultado["ordenes_seleccionadas"]
    
    # Ejecutar verificación completa usando los datos de la instancia que realmente se resolvió
    nombre_instancia_verificacion = os.path.basename(archivo_input)
    solucion_valida = verificar_solucion_completa(
        W, S, LB, UB,  # Usar los datos de la instancia que se resolvió (posiblemente reducida)
        pasillos_lista, 
        ordenes_lista, 
        resultado["valor_objetivo"],
        nombre_instancia_verificacion
    )
    
    if solucion_valida:
        print("\n🎉 ¡VERIFICACIÓN EXITOSA! La solución es válida y factible.")
    else:
        print("\n⚠️ VERIFICACIÓN FALLÓ. La solución tiene problemas de factibilidad.")
    
    print("="*60)
    # ============================================================
    
    # Obtener nombre de instancia y dataset
    nombre_dataset = os.path.basename(os.path.dirname(archivo_input))  # ej: "A"
    nombre_instancia = os.path.splitext(os.path.basename(archivo_input))[0]  # ej: "instance_0001"

    # Crear diccionario con métricas del resultado
    metrica_dict = {
        nombre_instancia: {
            'modelo7': {  # Modelo evaluado
                'mejor_objetivo': resultado.get('valor_objetivo', ''),
                'pasillos_seleccionados': resultado.get('pasillos_seleccionados', ''),
                'ordenes_seleccionadas': resultado.get('ordenes_seleccionadas', ''),
                'cota_dual': resultado.get('cota_dual', ''),
                'restricciones': resultado.get('restricciones', 0),
                'variables': resultado.get('variables', 0),
                'variables_final': resultado.get('variables_final', 0),
                'tiempo_ejecucion': round(tiempo_total, 2),  # Agregar tiempo a las métricas
                'solucion_valida': 'SÍ' if solucion_valida else 'NO',  # Añadir resultado de verificación
            }
        }
    }

    # Crear carpeta de salida si no existe
    output_dir = os.path.join("OUTPUT", nombre_dataset)
    os.makedirs(output_dir, exist_ok=True)

    # Guardar archivo .out con resultados
    output_path = os.path.join(output_dir, f"{nombre_instancia}.out")
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(f"Mejor valor objetivo: {resultado['valor_objetivo']}\n")
        f.write("Órdenes seleccionadas:\n")
        ordenes = resultado["ordenes_seleccionadas"]
        if isinstance(ordenes, list):
            f.write(" ".join(map(str, ordenes)) + "\n")
        else:
            f.write(" ".join(map(str, list(ordenes))) + "\n")
        f.write("Pasillos seleccionados:\n")
        pasillos = resultado["pasillos_seleccionados"]
        if isinstance(pasillos, list):
            f.write(" ".join(map(str, pasillos)) + "\n")
        else:
            f.write(" ".join(map(str, list(pasillos))) + "\n")

    # Guardar archivo .csv con métricas
    csv_output_path = os.path.join(output_dir, "resumen_metricas.csv")
    escribir_csv(metrica_dict, csv_output_path, modelos=['modelo7'])

    print(f"\n✅ Resultados guardados en:\n- {output_path}\n- {csv_output_path}")
else:
    print(f"❌ No se encontró solución con el umbral de tiempo dado.")
    print(f"⏱️ Tiempo total intentado: {tiempo_total:.2f} segundos")
