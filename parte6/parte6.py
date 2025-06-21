import os
import sys
import time
import csv
import importlib.util
import glob
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cargar_input import leer_input

# ====================
# Utilidades
# ====================
def ejecutar_modelo(model_path, input_path, output_path, threshold):
    """
    Ejecuta un modelo Python (script) para cada archivo de input, guarda el output y retorna métricas.
    """
    # Cargar el módulo dinámicamente
    spec = importlib.util.spec_from_file_location("modelo_mod", model_path)
    modelo_mod = importlib.util.module_from_spec(spec)
    sys.modules["modelo_mod"] = modelo_mod
    spec.loader.exec_module(modelo_mod)

    metricas = []
    archivos_input = [f for f in os.listdir(input_path) if f.endswith('.txt')]
    for archivo in archivos_input:
        entrada = os.path.join(input_path, archivo)
        salida = os.path.join(output_path, archivo.replace('.txt', '.out'))
        start = time.time()
        # Ejecutar el modelo: se espera que tenga una función main(input_file, output_file, threshold)
        resultado = modelo_mod.main(entrada, salida, threshold)
        tiempo = time.time() - start
        # resultado debe ser un dict con las métricas requeridas
        resultado['tiempo'] = tiempo
        resultado['instancia'] = archivo
        metricas.append(resultado)
    return metricas


def leer_config(cfg_path):
    """Lee el archivo de configuración y retorna los paths y parámetros."""
    config = {}
    with open(cfg_path, 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                config[k.strip()] = v.strip()
    return config


def escribir_csv(metrica_dict, csv_path, modelos):
    # Escribe el archivo CSV de resultados comparativos en formato vertical por instancia
    with open(csv_path, 'w', newline='', encoding='cp1252') as f:
        writer = csv.writer(f, delimiter=';')
        # Header: Modelo_Instancia, Métrica, Valor
        ancho = 10
        writer.writerow(["Instancia", "Métrica", "Sección 5", "Col. iniciales", "Rankear", "Eliminar col."])
        metricas = [
            ("Restricciones", 'restricciones'),
            ("# variables inicial", 'variables'),
            ("# variables en últ. maestro", 'variables_final'),
            ("Cota dual", 'cota_dual'),
            ("Mejor objetivo", 'mejor_objetivo'),
        ]
        # Mapeo de modelo a columna
        modelo_a_columna = {
            'modelo0': 2, # Sección 5
            'modelo1': 3, # Col. iniciales
            'modelo2': 4, # Rankear
            'modelo3': 5, # Eliminar col.
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

    # Lee el archivo de configuración y obtiene los paths y parámetros
    config = leer_config(cfg_path)

    # Obtiene el path de los archivos de entrada y el umbral de tiempo
    input_path = config['inPath']
    threshold = int(config['threshold'])

    modelos = []        # Lista de nombres de modelos (ej: modelo1, modelo2...)
    out_paths = {}      # Diccionario: nombre_modelo -> path de salida
    model_paths = {}    # Diccionario: nombre_modelo -> path del script del modelo
    parte6_dir = os.path.dirname(__file__) 

    # Busca en el config las líneas que empiezan con 'model' y 'outPath'
    for k, v in config.items():
        if k.startswith('model'):
            idx = k[5:]
            modelos.append(f"modelo{idx}")
            model_paths[f"modelo{idx}"] = os.path.join(parte6_dir, v)  # ← ruta absoluta al modelo
        if k.startswith('outPath'):
            idx = k[7:]
            out_paths[f"modelo{idx}"] = os.path.join(parte6_dir, v)  # ← idem para salida

    # metrica_dict almacenará los resultados para cada instancia y modelo
    metrica_dict = {}

    # Obtener lista de archivos de entrada
    input_files = sorted(glob.glob(os.path.join(input_path, '*.txt')))
    
    # ----------------------------------------------------------------------------#
    # TODO: BORRAR ESTA LINEAL PARA HACER LA PRUEBA FINAL
    # Solo tomar los primeros dos archivos de entrada (Ahorrar tiempo en el debug)
    input_files = input_files[:2]
    # ----------------------------------------------------------------------------#

    metrica_dict = {}

    for modelo in modelos:
        print(f"Ejecutando {modelo} ...")
        # Cargar clase Columns desde el archivo del modelo
        spec = importlib.util.spec_from_file_location("modulo_modelo", model_paths[modelo])
        modulo_modelo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo_modelo)
        Columns = getattr(modulo_modelo, "Columns")
        out_dir = out_paths[modelo]
        os.makedirs(out_dir, exist_ok=True)
        metricas = []
        for input_file in input_files:
            W, S, LB, UB = leer_input(input_file)
            solver = Columns(W, S, LB, UB)
            resultado = solver.Opt_ExplorarCantidadPasillos(threshold)
            # Guardar resultado JSON
            nombre_salida = os.path.join(out_dir, os.path.basename(input_file).replace('.txt', '.json'))
            with open(nombre_salida, 'w') as f:
                json.dump(resultado, f)
            # Métricas
            metrica = {
                'instancia': os.path.basename(input_file),
                'mejor_objetivo': resultado.get('valor_objetivo'),
                'pasillos_seleccionados': resultado.get('pasillos_seleccionados'),
                'ordenes_seleccionadas': resultado.get('ordenes_seleccionadas'),
                'cota_dual': resultado.get('cota_dual'),
                # Puedes agregar más métricas si quieres
            }
            metricas.append(metrica)
            if os.path.basename(input_file) not in metrica_dict:
                metrica_dict[os.path.basename(input_file)] = {}
            metrica_dict[os.path.basename(input_file)][modelo] = metrica
            
    escribir_csv(metrica_dict, 'resultados_parte6.csv', modelos)
    print("Resultados guardados en resultados_parte6.csv")

if __name__ == "__main__":
    main()
