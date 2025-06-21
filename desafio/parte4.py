from cargar_input import leer_input
from basic_solver import Basic

# Cargar datos W, S, LB, UB como hacías antes
W, S, LB, UB = leer_input("datos_de_entrada/input_0001.txt")

# Ejecutar problema 1
# opt = Basic(W, S, LB, UB)
# opt.Opt_cantidadPasillosFija(2,30)

# Ejecutar problema 2, hay que poner en basic_solver self.pasillos_fijos = [1,3]
# opt = Basic(W, S, LB, UB)
# opt.Opt_PasillosFijos(30)

# Ejecutar parte 4
# Buscar mejor solución explorando distintas cantidades de pasillos en 60 segundos
basic = Basic(W, S, LB, UB)
resultado = basic.Opt_ExplorarCantidadPasillos(60)
print("Mejor valor objetivo:", resultado["valor_objetivo"])
print("Órdenes seleccionadas:", resultado["ordenes_seleccionadas"])
print("Pasillos seleccionados:", resultado["pasillos_seleccionados"])


#corroborar cantidad de ordenes y pasillos elegidos
print(f"{len(resultado['ordenes_seleccionadas'])} órdenes seleccionadas.")
print(f"{len(resultado['pasillos_seleccionados'])} pasillos seleccionados.")
