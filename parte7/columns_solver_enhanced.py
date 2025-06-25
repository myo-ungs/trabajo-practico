import os
import sys
import numpy as np
from sklearn.cluster import KMeans
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
        self.n_pasillos = self.A

    def construir_columnas_iniciales(self):
        """
        Selecciona columnas iniciales de manera eficiente: solo los N pasillos con mayor capacidad.
        """
        N = min(10, self.n_pasillos)  # Puedes ajustar N según el tamaño
        capacidades = [(a, sum(self.S[a])) for a in range(self.n_pasillos)]
        capacidades.sort(key=lambda x: x[1], reverse=True)
        columnas = []
        for a, _ in capacidades[:N]:
            ordenes = self.ordenes_maximas_para_pasillo(a)
            columnas.append({"pasillo": a, "ordenes": ordenes})
        return columnas
    
    def Rankear(self):
        """
        Variante ML: Agrupa los pasillos por similitud de capacidad usando KMeans y prioriza k que representen grupos distintos.
        """
        capacidades = np.array([sum(self.S[a]) for a in range(self.n_pasillos)]).reshape(-1, 1)
        n_clusters = min(4, self.n_pasillos)
        if self.n_pasillos > 1:
            kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(capacidades)
            labels = kmeans.labels_
            pasillos_por_grupo = []
            for g in range(n_clusters):
                indices = [i for i, lbl in enumerate(labels) if lbl == g]
                if indices:
                    mejor = max(indices, key=lambda a: capacidades[a][0])
                    pasillos_por_grupo.append(mejor)
            pasillos_ordenados = sorted(pasillos_por_grupo, key=lambda a: capacidades[a][0], reverse=True)
        else:
            pasillos_ordenados = [0]
        lista_k = []
        for k in range(1, self.n_pasillos + 1):
            suma_capacidad_k = sum(capacidades[a][0] for a in pasillos_ordenados[:min(k, len(pasillos_ordenados))])
            lista_k.append((k, suma_capacidad_k))
        lista_k.sort(key=lambda x: x[1], reverse=True)
        return lista_k
    
    def Opt_cantidadPasillosFija(self, k, umbral):
        """
        Variante con PySCIPOpt que elimina columnas no usadas en las últimas 5 iteraciones.
        """
        import time

        start = time.time()
        self.inicializar_columnas_para_k(k)  # Asegura columnas iniciales

        historial_no_usadas = {}
        iteraciones = 0

        while time.time() - start < umbral:
            modelo, lambdas_list, restr = self.construir_modelo(k)
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
        modelo, lambdas_list, restr = self.construir_modelo(k)
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