import time
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpBinary, LpStatus, value

class Basic:
    def __init__(self, W, S, LB, UB):
        self.W = W  # demanda: lista de listas [orden][item]
        self.S = S  # oferta: lista de listas [pasillo][item]
        self.LB = LB
        self.UB = UB
        self.n_ordenes = len(W)
        self.n_elementos = len(W[0])
        self.n_pasillos = len(S)
        self.pasillos_fijos = []
        self.modelos_previos = {}

    def Rankear(self):
        capacidades = [sum(self.S[a]) for a in range(self.n_pasillos)]
        return sorted(range(self.n_pasillos), key=lambda a: capacidades[a], reverse=True)

    def Opt_cantidadPasillosFija(self, k, umbral):
        start = time.time()
        pasillos_base = self.Rankear()[:k]

        modelo = LpProblem("Opt_cantidadPasillosFija", LpMaximize)

        x = LpVariable.dicts("x", range(self.n_ordenes), cat=LpBinary)
        y = LpVariable.dicts("y", pasillos_base, cat=LpBinary)

        # Objetivo
        modelo += lpSum(x[o] * sum(self.W[o][i] for i in range(self.n_elementos)) for o in range(self.n_ordenes)), "TotalRecolectado"

        # Restricciones
        total = lpSum(x[o] * sum(self.W[o][i] for i in range(self.n_elementos)) for o in range(self.n_ordenes))
        modelo += total >= self.LB
        modelo += total <= self.UB

        for i in range(self.n_elementos):
            demanda_i = lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes))
            capacidad_i = lpSum(self.S[a][i] * y[a] for a in pasillos_base)
            modelo += demanda_i <= capacidad_i

        modelo += lpSum(y[a] for a in pasillos_base) == k

        if time.time() - start > umbral:
            return {"valor_objetivo": -float("inf"), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        modelo.solve()

        if LpStatus[modelo.status] != "Optimal":
            return {"valor_objetivo": -float("inf"), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        ordenes_seleccionadas = [o for o in range(self.n_ordenes) if x[o].varValue == 1]
        pasillos_seleccionados = [a for a in pasillos_base if y[a].varValue == 1]
        valor_objetivo = value(modelo.objective)

        self.pasillos_fijos = pasillos_seleccionados
        self.modelos_previos[k] = {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": pasillos_seleccionados
        }

        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": pasillos_seleccionados
        }

    def Opt_PasillosFijos(self, umbral):
        start = time.time()
        if not self.pasillos_fijos:
            raise RuntimeError("Primero ejecuta Opt_ExplorarCantidadPasillos o fija los pasillos.")

        modelo = LpProblem("Opt_PasillosFijos", LpMaximize)
        x = LpVariable.dicts("x", range(self.n_ordenes), cat=LpBinary)

        total = lpSum(x[o] * sum(self.W[o][i] for i in range(self.n_elementos)) for o in range(self.n_ordenes))
        modelo += total, "TotalRecolectado"
        modelo += total >= self.LB
        modelo += total <= self.UB

        for i in range(self.n_elementos):
            capacidad = sum(self.S[a][i] for a in self.pasillos_fijos)
            modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes)) <= capacidad

        if time.time() - start > umbral:
            return None

        modelo.solve()

        if LpStatus[modelo.status] != "Optimal":
            return None

        ordenes = [o for o in range(self.n_ordenes) if x[o].varValue == 1]
        valor = value(modelo.objective)

        return {
            "valor_objetivo": valor,
            "ordenes_seleccionadas": ordenes,
            "pasillos_seleccionados": self.pasillos_fijos
        }

    def Opt_ExplorarCantidadPasillos(self, umbral_total):
        start = time.time()
        mejor_sol = None
        mejor_valor = -float("inf")

        for k in range(1, self.n_pasillos + 1):
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante <= 0:
                break

            sol = self.Opt_cantidadPasillosFija(k, tiempo_restante)
            if sol and sol["valor_objetivo"] > mejor_valor:
                mejor_valor = sol["valor_objetivo"]
                mejor_sol = sol

        if mejor_sol:
            self.pasillos_fijos = mejor_sol["pasillos_seleccionados"]
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante > 0:
                refinada = self.Opt_PasillosFijos(tiempo_restante)
                if refinada and refinada["valor_objetivo"] > mejor_valor:
                    mejor_sol = refinada

        return mejor_sol
