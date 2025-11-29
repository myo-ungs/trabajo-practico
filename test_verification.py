
import time
import sys
import os
sys.path.append(os.getcwd())
from cargar_input import leer_input
from parte4.basic_solver import Basic
from parte5.columns_solver import Columns as ColumnsP5
from parte7.modelos.columns_solver_enhanced import Columns as ColumnsP7

def test_solver(name, solver_class, W, S, LB, UB, timeout):
    print(f"\nTesting {name} on a/instance_0003.txt with timeout {timeout}s...")
    start = time.time()
    solver = solver_class(W, S, LB, UB)
    res = solver.Opt_ExplorarCantidadPasillos(timeout)
    elapsed = time.time() - start
    
    print(f"{name} finished in {elapsed:.2f}s")
    if res:
        ordenes = res.get("ordenes_seleccionadas", [])
        total_units = sum(sum(W[o]) for o in ordenes)
        obj = res.get("valor_objetivo", 0)
        
        print(f"Result: Objective={obj}, Total Units={total_units}, LB={LB}")
        
        if total_units < LB - 1e-5 and total_units > 1e-5:
            print(f"❌ FAILURE: Total Units {total_units} < LB {LB}")
        elif total_units == 0:
             print(f"⚠️ No solution found (Total Units=0)")
        else:
            print(f"✅ SUCCESS: Total Units {total_units} >= LB {LB}")
    else:
        print("⚠️ No result returned")

def main():
    input_file = "datos_de_entrada/b/instance_0001.txt"
    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found")
        return

    W, S, LB, UB = leer_input(input_file)
    print(f"Loaded {input_file}: LB={LB}, UB={UB}")

    # Test Part 4
    test_solver("Part 4 (Basic)", Basic, W, S, LB, UB, 15)

    # Test Part 5
    test_solver("Part 5 (Columns)", ColumnsP5, W, S, LB, UB, 15)

    # Test Part 7
    test_solver("Part 7 (Enhanced)", ColumnsP7, W, S, LB, UB, 15)

if __name__ == "__main__":
    main()
