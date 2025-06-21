import time
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpBinary, LpStatus, value

class Basic:
    def __init__(self, W, S, LB, UB):
        self.W = W
        self.S = S
        self.LB = LB
        self.UB = UB
        self.n_ordenes = len(W)
        self.n_elementos = len(W[0])
        self.n_pasillos = len(S)
        self.pasillos_fijos = []

        # Para guardar modelos previos por k
        self.modelos_previos = {}

    def Opt_cantidadPasillosFija(self, k, umbral):
        start = time.time()

        # Si existe modelo previo para k-1, intentar reutilizar pasillos y agregar uno nuevo
        if k - 1 in self.modelos_previos:
            pasillos_previos = self.modelos_previos[k - 1]["pasillos_seleccionados"]
            pasillos_ordenados = self.Rankear()
            candidatos = [p for p in pasillos_ordenados if p not in pasillos_previos]
            if candidatos:
                pasillos_base = pasillos_previos + [candidatos[0]]
            else:
                pasillos_base = pasillos_previos
            pasillos_base = pasillos_base[:k]  # Asegurarse que la lista tenga tamaño k
        else:
            pasillos_base = self.Rankear()[:k]

        modelo = LpProblem("Opt_cantidadPasillosFija", LpMaximize)
        x = LpVariable.dicts("x", range(self.n_ordenes), cat=LpBinary)
        y = LpVariable.dicts("y", pasillos_base, cat=LpBinary)

        # Función objetivo: maximizar total recolectado
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)), "Obj"

        # Restricciones LB y UB
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) >= self.LB
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) <= self.UB

        # Restricción de disponibilidad por pasillos seleccionados
        for i in range(self.n_elementos):
            modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes)) <= lpSum(self.S[a][i] * y[a] for a in pasillos_base)

        # Exactamente k pasillos seleccionados
        modelo += lpSum(y[a] for a in pasillos_base) == k

        if time.time() - start > umbral:
            return {"valor_objetivo": -float('inf'), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        modelo.solve()

        if LpStatus[modelo.status] != "Optimal":
            return {"valor_objetivo": -float('inf'), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        ordenes_seleccionadas = [o for o in range(self.n_ordenes) if x[o].varValue == 1]
        pasillos_seleccionados = [a for a in pasillos_base if y[a].varValue == 1]
        valor_objetivo = value(modelo.objective)

        # Guardar para reutilizar
        self.modelos_previos[k] = {
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": pasillos_seleccionados,
            "valor_objetivo": valor_objetivo
        }

        self.pasillos_fijos = pasillos_seleccionados

        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": pasillos_seleccionados
        }

    def Opt_PasillosFijos(self, umbral):
        start = time.time()

        if not self.pasillos_fijos:
            print("No hay pasillos fijos definidos para Opt_PasillosFijos")
            return None

        modelo = LpProblem("Opt_PasillosFijos", LpMaximize)
        x = LpVariable.dicts("x", range(self.n_ordenes), cat=LpBinary)

        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)), "TotalRecolectado"
        
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) >= self.LB
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) <= self.UB

        for i in range(self.n_elementos):
            disponibilidad_total = sum(self.S[a][i] for a in self.pasillos_fijos)
            modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes)) <= disponibilidad_total

        tiempo_restante = umbral - (time.time() - start)
        if tiempo_restante <= 0:
            print("Tiempo agotado antes de resolver el modelo en Opt_PasillosFijos")
            return None

        modelo.solve()

        if LpStatus[modelo.status] != "Optimal":
            print(f"Modelo no óptimo: {LpStatus[modelo.status]}")
            return None

        ordenes_seleccionadas = [o for o in range(self.n_ordenes) if x[o].varValue == 1]
        valor_objetivo = value(modelo.objective)

        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": self.pasillos_fijos
        }

    def Opt_ExplorarCantidadPasillos(self, umbral_total):
        start = time.time()
        mejor_sol = None
        mejor_valor = -float('inf')

        ranking_k = list(range(1, self.n_pasillos + 1))

        for k in ranking_k:
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante <= 0:
                print("Se acabó el tiempo total")
                break

            print(f"Probando con k = {k} (tiempo restante: {round(tiempo_restante, 2)} seg)")
            sol = self.Opt_cantidadPasillosFija(k, tiempo_restante)

            if sol and sol["valor_objetivo"] > mejor_valor:
                mejor_valor = sol["valor_objetivo"]
                mejor_sol = sol

        if mejor_sol:
            self.pasillos_fijos = mejor_sol["pasillos_seleccionados"]
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante > 0:
                sol_refinada = self.Opt_PasillosFijos(tiempo_restante)
                if sol_refinada and sol_refinada["valor_objetivo"] > mejor_valor:
                    mejor_sol = sol_refinada

        return mejor_sol

    def Rankear(self):
        capacidades = [sum(self.S[a]) for a in range(self.n_pasillos)]
        pasillos_ordenados = sorted(range(self.n_pasillos), key=lambda a: capacidades[a], reverse=True)
        return pasillos_ordenados
