import sys
import os
import time
try:
    from parte5.columns_solver import Columns as ColumnsBase
except ImportError:
    # Añade '../parte5/' al sys.path si no se encuentra el módulo
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from parte5.columns_solver import Columns as ColumnsBase

class Columns(ColumnsBase):
    def __init__(self, W, S, LB, UB):
        super().__init__(W, S, LB, UB)  # Llama al init de ColumnsBase
        self.modelos = {}  # Inicializo el dict para guardar modelos por k

    def Opt_cantidadPasillosFija(self, k, umbral):
        """
        Variante que elimina columnas no usadas en las últimas 5 iteraciones.
        """

        start = time.time()
        self.inicializar_columnas_para_k(k, umbral)  # Asegura columnas iniciales

        historial_no_usadas = {}
        iteraciones = 0

        while time.time() - start < umbral:
            modelo, lambdas_list, restr_k, restr_o, restr_u, restr_cov = self.construir_modelo_maestro(k,umbral)
            lambdas = {j: var for j, var in enumerate(lambdas_list)}

            modelo.optimize()

            status = modelo.getStatus()
            if status != "optimal":
                print(f"⚠️ Modelo infactible o sin solución válida en iteración {iteraciones} para k={k}")
                break

            usados = []

            for j, var in lambdas.items():
                val = modelo.getVal(var)
                if val > 0.5:
                    historial_no_usadas[j] = 0
                    usados.append(j)
                else:
                    historial_no_usadas[j] = historial_no_usadas.get(j, 0) + 1

            # Eliminar columnas no usadas en últimas 5 iteraciones
            eliminar = [j for j, n in historial_no_usadas.items() if n >= 5]
            for j in eliminar:
                if j in lambdas:
                    modelo.freeTransform()
                    modelo.delVar(lambdas[j])  # Elimina la variable del modelo
                    self.columnas[k][j] = None  # Marca como eliminada

            iteraciones += 1
            if not eliminar:
                break  # Si no se eliminaron columnas, termina antes

        # Resolver modelo final
        modelo, lambdas_list, _ , _ , _ , _ = self.construir_modelo_maestro(k, umbral)
        modelo.optimize()

        lambdas = {j: var for j, var in enumerate(lambdas_list)}

        ordenes_seleccionadas = set()
        pasillos_seleccionados = set()

        status = modelo.getStatus()
        valor_objetivo = 0
        if status == "optimal":
            valor_objetivo = int(modelo.getObjVal())
            for j, var in lambdas.items():
                if self.columnas[k][j] is not None:
                    val = modelo.getVal(var)
                    if val > 0.5:
                        pasillos_seleccionados.add(self.columnas[k][j]["pasillo"])
                        for o, v in enumerate(self.columnas[k][j]["ordenes"]):
                            if v:
                                ordenes_seleccionadas.add(o)
        else:
            print(f"⚠️ Modelo infactible o sin solución válida para k={k}")

        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": pasillos_seleccionados,
            "variables": len(self.columnas[k]),
            "variables_final": len([c for c in self.columnas[k] if c is not None]),
            "cota_dual": valor_objetivo
        }