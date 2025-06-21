import sys
import os
try:
    from desafio.columns_solver import Columns as ColumnsBase
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from columns_solver import Columns as ColumnsBase

class Columns(ColumnsBase):
    def Opt_cantidadPasillosFija(self, k, umbral):
        # Igual que base, pero elimina columnas no usadas en últimas 5 iteraciones
        import time
        from pulp import value
        start = time.time()
        if k not in self.modelos:
            modelo, columnas, lambdas = self.construir_modelo(k)
            self.modelos[k] = {"modelo": modelo, "columnas": columnas, "lambda": lambdas}
        else:
            modelo = self.modelos[k]["modelo"]
            columnas = self.modelos[k]["columnas"]
            lambdas = self.modelos[k]["lambda"]
        historial_no_usadas = {j: 0 for j in lambdas}
        iteraciones = 0
        while time.time() - start < umbral:
            modelo.solve()
            usados = []
            for j, var in lambdas.items():
                if var.varValue and var.varValue > 0.5:
                    historial_no_usadas[j] = 0
                    usados.append(j)
                else:
                    historial_no_usadas[j] += 1
            # Eliminar columnas no usadas en últimas 5 iteraciones
            eliminar = [j for j, n in historial_no_usadas.items() if n >= 5]
            for j in eliminar:
                if j in lambdas:
                    modelo -= lambdas[j]
                    del lambdas[j]
                    columnas[j] = None  # Marca como eliminada
            # (Puedes agregar lógica de generación de columnas aquí si quieres)
            iteraciones += 1
            if not eliminar:
                break  # Si no hay nada para eliminar, termina
        # Prepara el resultado como en el base
        ordenes_seleccionadas = []
        for j, var in lambdas.items():
            if var.varValue and var.varValue > 0.5 and columnas[j] is not None:
                ordenes_seleccionadas.extend(columnas[j]["ordenes"])
        valor_objetivo = value(modelo.objective)
        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": [columnas[j]["pasillo"] for j in lambdas if columnas[j] is not None]
        }
