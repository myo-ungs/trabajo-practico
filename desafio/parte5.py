from cargar_input import leer_input
from columns_solver import Columns  # Suponé que guardaste la clase en "columns_solver.py"

# Cargar datos desde archivo
W, S, LB, UB = leer_input("datos_de_entrada/input_0001.txt")

# Instanciar y ejecutar
solver = Columns(W, S, LB, UB)

resultado = solver.Opt_ExplorarCantidadPasillos(60)

print("\n=== RESULTADO FINAL ===")
print("Valor objetivo:", resultado["valor_objetivo"])
print("Pasillos seleccionados:", resultado["pasillos_seleccionados"])
print("Órdenes seleccionadas:", resultado["ordenes_seleccionadas"])
