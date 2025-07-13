import os
import sys
import csv
import importlib.util
import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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
    with open(csv_path, 'w', newline='', encoding='cp1252') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Instancia", "Métrica", "Sección 5", "Col. iniciales", "Rankear", "Eliminar col."])
        metricas = [
            ("Restricciones", 'restricciones'),
            ("# variables inicial", 'variables'),
            ("# variables en últ. maestro", 'variables_final'),
           # ("Cota dual", 'cota_dual'),
            ("Mejor objetivo", 'mejor_objetivo'),
            ("Tiempo", "tiempo_total")
        ]
        modelo_a_columna = {
            'modelo0': 2,
            'modelo1': 3,
            'modelo2': 4,
            'modelo3': 5,
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


def main():
    if len(sys.argv) < 2:
        print("Uso: python parte6.py archivo.cfg")
        sys.exit(1)
    cfg_path = sys.argv[1]

    config = leer_config(cfg_path)

    input_path = config['inPath']
    input_path_abs = os.path.abspath(input_path)
    print("Ruta absoluta carpeta inputs:", input_path_abs)
    print("Archivos en carpeta:", os.listdir(input_path_abs) if os.path.exists(input_path_abs) else "No existe")

    threshold = int(config['threshold'])

    modelos = []
    out_paths = {}
    model_paths = {}
    parte6_dir = os.path.dirname(__file__) 

    for k, v in config.items():
        if k.startswith('model'):
            idx = k[5:]
            modelos.append(f"modelo{idx}")
            model_paths[f"modelo{idx}"] = os.path.join(parte6_dir, v)
        if k.startswith('outPath'):
            idx = k[7:]
            out_paths[f"modelo{idx}"] = os.path.join(parte6_dir, v)

    modelos = [m for m in modelos if m in ('modelo0','modelo1','modelo2', 'modelo3')]

    metrica_dict = {}
    input_files = sorted(glob.glob(os.path.join(input_path, '*.txt')))
    input_files = input_files[:4]  # las primeras 4 del dataset A

    print("Modelos detectados:", modelos)
    print("Archivos de input:", [os.path.basename(f) for f in input_files])

    for modelo in modelos:
        print(f"Ejecutando {modelo} ...")
        spec = importlib.util.spec_from_file_location("modulo_modelo", model_paths[modelo])
        modulo_modelo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo_modelo)
        Columns = getattr(modulo_modelo, "Columns")
        out_dir = out_paths[modelo]
        os.makedirs(out_dir, exist_ok=True)
        for input_file in input_files:
            nombre_archivo = os.path.basename(input_file)
            W, S, LB, UB = leer_input(input_file)
            solver = Columns(W, S, LB, UB)
            resultado = solver.Opt_ExplorarCantidadPasillos(threshold/4)
            if resultado is None:
                print(f"⚠️ Atención: resultado None para {modelo} - {nombre_archivo}, se asignan valores por defecto")
                resultado = {}

            metrica = {
                'instancia': nombre_archivo,
                'mejor_objetivo': resultado.get('valor_objetivo', ''),
                'pasillos_seleccionados': resultado.get('pasillos_seleccionados', ''),
                'ordenes_seleccionadas': resultado.get('ordenes_seleccionadas', ''),
                #'cota_dual': resultado.get('cota_dual', ''),
                'restricciones': resultado.get('restricciones', 0),
                'variables': resultado.get('variables', 0),
                'variables_final': resultado.get('variables_final', 0),
                'tiempo_total' : resultado.get('tiempo_total',0)
            }


            if nombre_archivo not in metrica_dict:
                metrica_dict[nombre_archivo] = {}
            metrica_dict[nombre_archivo][modelo] = metrica


    escribir_csv(metrica_dict, 'parte6/resultados_parte6.csv', modelos)
    print("\n✅ Resultados guardados en resultados_parte6.csv")

if __name__ == "__main__":
    main()
