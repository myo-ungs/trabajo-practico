from cargar_input import leer_input
from column_solver import Column

# Cargar datos W, S, LB, UB como hacías antes
W, S, LB, UB = leer_input("datos_de_entrada/input_0001.txt")

# Ejecutar parte 5
column = Column(W, S, LB, UB)
resultado = column.Opt_ExplorarCantidadPasillos(60)
print("Mejor valor objetivo:", resultado["valor_objetivo"])
print("Órdenes seleccionadas:", resultado["ordenes_seleccionadas"])
print("Pasillos seleccionados:", resultado["pasillos_seleccionados"])