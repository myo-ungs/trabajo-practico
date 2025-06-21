import sys
import os
try:
    from parte5.columns_solver import Columns as ColumnsBase
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from parte5.columns_solver import Columns as ColumnsBase

class Columns(ColumnsBase):
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
