import numpy as np
from sklearn.cluster import KMeans
import sys
import os
try:
    from parte5.columns_solver import Columns as ColumnsBase
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from parte5.columns_solver import Columns as ColumnsBase

class Columns(ColumnsBase):

    def __init__(self, W, S, LB, UB):
        super().__init__(W, S, LB, UB)
        self.n_pasillos = self.A  
    
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