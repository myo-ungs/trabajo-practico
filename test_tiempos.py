import time
import sys
sys.path.insert(0, 'parte4')
sys.path.insert(0, 'parte5')

from basic_solver import Basic
from columns_solver import Columns
from cargar_input import leer_input

instancias_a = [
    'datos_de_entrada/a/instance_0001.txt',
    'datos_de_entrada/a/instance_0002.txt',
    'datos_de_entrada/a/instance_0003.txt',
]

TIMEOUT = 120  # 2 minutos por instancia para prueba rápida

print("=" * 60)
print("PARTE 4 - Basic Solver")
print("=" * 60)
for archivo in instancias_a:
    W, S, LB, UB = leer_input(archivo)
    nombre = archivo.split('/')[-1]
    
    start = time.time()
    basic = Basic(W, S, LB, UB)
    resultado = basic.Opt_ExplorarCantidadPasillos(TIMEOUT)
    elapsed = time.time() - start
    
    obj = resultado['valor_objetivo'] if resultado else 'None'
    print(f"  {nombre}: objetivo={obj}, tiempo={elapsed:.2f}s")

print()
print("=" * 60)
print("PARTE 5 - Columns Solver")
print("=" * 60)
for archivo in instancias_a:
    W, S, LB, UB = leer_input(archivo)
    nombre = archivo.split('/')[-1]
    
    start = time.time()
    solver = Columns(W, S, LB, UB)
    resultado = solver.Opt_ExplorarCantidadPasillos(TIMEOUT)
    elapsed = time.time() - start
    
    obj = resultado['valor_objetivo'] if resultado else 'None'
    print(f"  {nombre}: objetivo={obj}, tiempo={elapsed:.2f}s")

print()
print("Nota: Para tiempos de Parte 6 y 7, ejecutar los scripts correspondientes.")
