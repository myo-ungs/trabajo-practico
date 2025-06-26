import os
import sys
import csv
import numpy as np
from columns_solver_enhanced import Columns
from fast_solver import FastSolver
from parte6.modelo_3 import Columns as Model3Columns

# Agregar directorio padre para importar cargar_input
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cargar_input import leer_input

def leer_config(cfg_path):
    config = {}
    with open(cfg_path, 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                config[k.strip()] = v.strip()
    return config

def escribir_csv(metrica_dict, csv_path, modelos):
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Instancia", "Métrica", "Parte 6", "Parte 7"])
        metricas = [
            ("Restricciones", 'restricciones'),
            ("# variables inicial", 'variables'),
            ("# variables en últ. maestro", 'variables_final'),
            ("Cota dual", 'cota_dual'),
            ("Mejor objetivo", 'mejor_objetivo'),
        ]
        modelo_a_columna = {
            'modelo0': 2,  # parte 6
            'modelo7': 3,  # parte 7 mejorado
        }
        for instancia, modelos_metricas in sorted(metrica_dict.items()):
            first = True
            for nombre_metrica, clave in metricas:
                row = [instancia if first else '', nombre_metrica] + [''] * 4
                for modelo in modelos:
                    m = modelos_metricas.get(modelo, {})
                    valor = m.get(clave, '')
                    col_idx = modelo_a_columna.get(modelo, None)
                    if col_idx is not None:
                        row[col_idx] = valor
                writer.writerow(row)
                first = False

def optimizar_instancia_grande(W, S, LB, UB, max_ordenes=2000, max_pasillos=50):
    print(f"🔧 Optimizando instancia: {len(W)} órdenes → {min(len(W), max_ordenes)}")
    print(f"🔧 Optimizando pasillos: {len(S)} pasillos → {min(len(S), max_pasillos)}")
    
    original_W_len = len(W)
    
    if len(W) > max_ordenes:
        beneficios_orden = [sum(orden) for orden in W]
        indices_mejores = sorted(range(len(beneficios_orden)), key=lambda i: beneficios_orden[i], reverse=True)[:max_ordenes]
        W = [W[i] for i in sorted(indices_mejores)]
        print(f"✅ Reducido a {len(W)} órdenes más prometedoras")
    
    if len(S) > max_pasillos:
        capacidades_pasillo = [sum(pasillo) for pasillo in S]
        indices_mejores = sorted(range(len(capacidades_pasillo)), key=lambda i: capacidades_pasillo[i], reverse=True)[:max_pasillos]
        S = [S[i] for i in sorted(indices_mejores)]
        print(f"✅ Reducido a {len(S)} pasillos de mayor capacidad")
    
    if original_W_len > max_ordenes:
        factor_reduccion = len(W) / original_W_len
        nuevo_LB = max(1, int(LB * factor_reduccion))
        nuevo_UB = int(UB * factor_reduccion)
        print(f"✅ Ajustados límites: LB={LB}→{nuevo_LB}, UB={UB}→{nuevo_UB}")
        return W, S, nuevo_LB, nuevo_UB
    else:
        print(f"✅ Límites mantenidos: LB={LB}, UB={UB}")
        return W, S, LB, UB

def optimizar_instancia(W, S, LB, UB, UMBRAL):
    instancia_muy_grande = len(W) > 5000
    usar_fast_solver = len(W) >= 800

    if instancia_muy_grande:
        print("⚠️ Instancia muy grande detectada. Aplicando optimizaciones...")
        W, S, LB, UB = optimizar_instancia_grande(W, S, LB, UB, max_ordenes=1000, max_pasillos=30)

    if usar_fast_solver:
        print("🚀 Usando FastSolver para instancia grande...")
        solver = FastSolver(W, S, LB, UB)
        resultado = solver.Opt_ExplorarCantidadPasillos(UMBRAL)
    else:
        print("🔧 Usando Columns (solver normal) para instancia pequeña...")
        solver = Columns(W, S, LB, UB)
        resultado = solver.Opt_ExplorarCantidadPasillos(UMBRAL)
    return resultado

def main():
    DATASETS = ['A','B']
    INSTANCIAS = ['instance_0001.txt', 'instance_0002.txt', 'instance_0003.txt']
    UMBRAL = 100

    base_dir = os.path.dirname(os.path.abspath(__file__))
    metrica_dict = {}

    for dataset in DATASETS:
        for instancia in INSTANCIAS:
            archivo_input = os.path.join(base_dir, "..", "datos_de_entrada", dataset, instancia)
            archivo_input = os.path.normpath(archivo_input)
            if not os.path.exists(archivo_input):
                print(f"⚠️ No se encontró el archivo {archivo_input}, se salta.")
                continue

            print(f"\n Procesando {archivo_input} ...")
            W, S, LB, UB = leer_input(archivo_input)

            nombre_instancia = f"{dataset}_{os.path.splitext(instancia)[0]}"
            metrica_dict[nombre_instancia] = {}

            # Parte 6
            print("Ejecutando modelo Parte 6...")
            model6 = Model3Columns(W, S, LB, UB)
            resultado6 = model6.Opt_ExplorarCantidadPasillos(UMBRAL)
            if resultado6:
                metrica_dict[nombre_instancia]['modelo0'] = {
                    'mejor_objetivo': resultado6.get('valor_objetivo', ''),
                    'pasillos_seleccionados': resultado6.get('pasillos_seleccionados', ''),
                    'ordenes_seleccionadas': resultado6.get('ordenes_seleccionadas', ''),
                    'cota_dual': resultado6.get('cota_dual', ''),
                    'restricciones': resultado6.get('restricciones', 0),
                    'variables': resultado6.get('variables', 0),
                    'variables_final': resultado6.get('variables_final', 0),
                }

            # Parte 7
            print("Ejecutando modelo Parte 7...")
            resultado7 = optimizar_instancia(W, S, LB, UB, UMBRAL)
            if resultado7:
                metrica_dict[nombre_instancia]['modelo7'] = {
                    'mejor_objetivo': resultado7.get('valor_objetivo', ''),
                    'pasillos_seleccionados': resultado7.get('pasillos_seleccionados', ''),
                    'ordenes_seleccionadas': resultado7.get('ordenes_seleccionadas', ''),
                    'cota_dual': resultado7.get('cota_dual', ''),
                    'restricciones': resultado7.get('restricciones', 0),
                    'variables': resultado7.get('variables', 0),
                    'variables_final': resultado7.get('variables_final', 0),
                }

    # Escribir resultados
    output_dir = os.path.join(base_dir, "OUTPUT")
    os.makedirs(output_dir, exist_ok=True)
    csv_output_path = os.path.join(output_dir, "resumen_metricas_parte7_vs_parte6.csv")
    escribir_csv(metrica_dict, csv_output_path, modelos=['modelo0', 'modelo7'])

    print(f"\n✅ Tabla comparativa guardada en: {csv_output_path}")

if __name__ == "__main__":
    main()
