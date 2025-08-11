import os
import sys
import glob
import time
import importlib.util
import csv

from cargar_input import leer_input

def leer_config(cfg_path):
    config = {}
    with open(cfg_path, 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                config[k.strip()] = v.strip()
    return config

def cargar_modulo(path):
    spec = importlib.util.spec_from_file_location("modulo_modelo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def ejecutar_modelo(modulo, W, S, LB, UB, umbral):
    # Detecta si tiene clase Columns o función resolver
    if hasattr(modulo, "Columns"):
        ColumnsClass = getattr(modulo, "Columns")
        solver = ColumnsClass(W, S, LB, UB)
        return solver.Opt_ExplorarCantidadPasillos(umbral)
    elif hasattr(modulo, "resolver"):
        return modulo.resolver(W, S, LB, UB, umbral)
    else:
        print("❌ Módulo sin interfaz conocida (Columns o resolver)")
        return None

def ejecutar_todos_modelos(config):
    raw_inpath = config['inPath']
    # Si es relativa, resolver respecto al directorio base del proyecto (donde está este script)
    base_dir = os.path.dirname(__file__)
    if not os.path.isabs(raw_inpath):
        input_base_path = os.path.abspath(os.path.join(base_dir, raw_inpath))
    else:
        input_base_path = raw_inpath
    print(f"[DEBUG] input_base_path resuelto: {input_base_path}")
    threshold = int(config.get('threshold', 600))

    datasets = config.get('datasets', 'A').split(',')
    max_files_per_dataset = int(config.get('max_files_per_dataset', 4))

    modelos = []
    model_paths = {}
    out_paths = {}

    for k, v in config.items():
        if k.startswith('model'):
            idx = k[5:]
            modelo_name = f"modelo{idx}"
            modelos.append(modelo_name)
            model_paths[modelo_name] = os.path.join(base_dir, v)
        elif k.startswith('outPath'):
            idx = k[7:]
            out_paths[f"modelo{idx}"] = os.path.join(base_dir, v)

    metrica_dict = {}

    print(f"Modelos detectados: {modelos}")
    print(f"Datasets a procesar: {datasets}")
    print(f"Máximo archivos por dataset: {max_files_per_dataset}")

    for dataset in datasets:
        dataset_path = os.path.join(input_base_path, dataset)
        if not os.path.isdir(dataset_path):
            print(f"⚠️ No existe el dataset {dataset} en {dataset_path}, se salta.")
            continue

        input_files = sorted(glob.glob(os.path.join(dataset_path, '*.txt')))[:max_files_per_dataset]
        print(f"\nProcesando dataset {dataset}, archivos: {[os.path.basename(f) for f in input_files]}")

        for modelo in modelos:
            print(f"\n➡️ Ejecutando {modelo} ...")
            modulo = cargar_modulo(model_paths[modelo])
            out_dir = out_paths.get(modelo, os.path.join(base_dir, "output", modelo))
            os.makedirs(out_dir, exist_ok=True)

            for input_file in input_files:
                nombre_archivo = f"{dataset}_{os.path.basename(input_file)}"
                print(f"  Procesando {nombre_archivo} ...")
                W, S, LB, UB = leer_input(input_file)

                start_time = time.time()
                resultado = ejecutar_modelo(modulo, W, S, LB, UB, threshold / len(modelos))
                elapsed = time.time() - start_time

                if not resultado or 'valor_objetivo' not in resultado:
                    print(f"⚠️ Resultado None o incompleto para {modelo} - {nombre_archivo}, asignando valores por defecto")
                    resultado = {
                        'valor_objetivo': 0,
                        'ordenes_seleccionadas': set(),
                        'pasillos_seleccionados': set(),
                        'restricciones': 0,
                        'variables': 0,
                        'variables_final': 0,
                        'cota_dual': 0
                    }

                resultado['tiempo_total'] = round(elapsed, 2)

                if nombre_archivo not in metrica_dict:
                    metrica_dict[nombre_archivo] = {}
                metrica_dict[nombre_archivo][modelo] = resultado

                # Guardar output
                nombre_archivo = nombre_archivo.split('.')[0]
                out_file = os.path.join(out_dir, f"{nombre_archivo}.out")

                with open(out_file, 'w') as f:
                    f.write(f"Mejor valor objetivo: {resultado.get('valor_objetivo', 0)}\n")

                    f.write("Ordenes seleccionadas:\n")
                    ordenes = " ".join(str(o) for o in sorted(resultado.get('ordenes_seleccionadas', [])))
                    f.write(f"{ordenes}\n")

                    f.write("Pasillos seleccionados:\n")
                    pasillos = " ".join(str(p) for p in sorted(resultado.get('pasillos_seleccionados', [])))
                    f.write(f"{pasillos}\n")

    return metrica_dict, modelos

def escribir_csv(metrica_dict, csv_path, modelos):
    # Formato requerido por enunciado (imagen): cuatro variantes
    # Renombrar columnas visibles
    display_names_map = {
        'modelo0': 'Sección 5',
        'modelo1': 'Col. iniciales',
        'modelo2': 'Rankear',
        'modelo3': 'Eliminar col.'
    }
    display_headers = [display_names_map.get(m, m) for m in modelos]

    metricas = [
        ("Restricciones", 'restricciones'),
        ("# variables", 'variables'),
        ("# variables en últ. maestro", 'variables_final'),
        ("Cota dual", 'cota_dual'),
        ("Mejor objetivo", 'valor_objetivo'),
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        header = ["Instancia", "Métrica"] + display_headers
        writer.writerow(header)
        for instancia, modelos_metricas in sorted(metrica_dict.items()):
            first = True
            for nombre_metrica, clave in metricas:
                row = [instancia if first else '', nombre_metrica] + [''] * len(modelos)
                for i, modelo in enumerate(modelos):
                    row[2 + i] = modelos_metricas.get(modelo, {}).get(clave, '')
                writer.writerow(row)
                first = False
