import time
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpBinary, LpStatus, value

class Column:
    def __init__(self, W, S, LB, UB):
        self.W = W
        self.S = S
        self.LB = LB
        self.UB = UB
        self.n_ordenes = len(W)
        self.n_elementos = len(W[0])
        self.n_pasillos = len(S)
        self.pasillos_fijos = []


    def Opt_cantidadPasillosFija(self, k, umbral):
        start = time.time()

        # Modelo de seccion 1
        modelo = LpProblem("Opt_cantidadPasillosFija", LpMaximize)
        x = LpVariable.dicts("x", range(self.n_ordenes), cat=LpBinary)
        y = LpVariable.dicts("y", range(self.n_pasillos), cat=LpBinary)

        # Funcion objetivo
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) / k

        # Restricciones
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) >= self.LB
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) <= self.UB

        for i in range(self.n_elementos):
            modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes)) <= lpSum(self.S[a][i] * y[a] for a in range(self.n_pasillos))

        modelo += lpSum(y[a] for a in range(self.n_pasillos)) == k

        # Validar umbral de tiempo
        tiempo_restante = umbral - (time.time() - start)
        if tiempo_restante <= 0:
            return {"valor_objetivo": -float('inf'), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        modelo.solve()

        if LpStatus[modelo.status] != "Optimal":
            return {"valor_objetivo": -float('inf'), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        # Resultados
        ordenes_seleccionadas = [o for o in range(self.n_ordenes) if x[o].varValue == 1]
        pasillos_seleccionados = [a for a in range(self.n_pasillos) if y[a].varValue == 1]
        valor_objetivo = value(modelo.objective)

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

        # Modelo de seccion 2
        modelo = LpProblem("Opt_PasillosFijos", LpMaximize)
        x = LpVariable.dicts("x", range(self.n_ordenes), cat=LpBinary)

        # Funcion objetivo
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)), "TotalRecolectado"
        
        # Restricciones
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) >= self.LB
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)) <= self.UB

        for i in range(self.n_elementos):
            disponibilidad_total = sum(self.S[a][i] for a in self.pasillos_fijos)
            modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes)) <= disponibilidad_total

        # Validar tiempo
        tiempo_restante = umbral - (time.time() - start)
        if tiempo_restante <= 0:
            print("Tiempo agotado antes de resolver el modelo en Opt_PasillosFijos")
            return None

        modelo.solve()

        if LpStatus[modelo.status] != "Optimal":
            print(f"Modelo no optimo: {LpStatus[modelo.status]}")
            return None

        # Resultados
        ordenes_seleccionadas = [o for o in range(self.n_ordenes) if x[o].varValue == 1]
        valor_objetivo = value(modelo.objective)

        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": self.pasillos_fijos
        }
    
    # HAY QUE IMPLEMENTAR --------------------------------
    # def Opt_ExplorarCantidadPasillos(self, umbral_total):
    # ----------------------------------------------------

    # Devuelve una lista de valores de 'k' (cantidad de pasillos) ordenados según
    # la capacidad total acumulada al elegir los k pasillos más capaces.
    def Rankear(self):
        capacidades = [sum(self.S[a]) for a in range(self.n_pasillos)]
        pasillos_ordenados = sorted(range(self.n_pasillos), key=lambda a: capacidades[a], reverse=True)

        lista_k = []
        for k in range(1, self.n_pasillos + 1):
            suma_capacidad_k = sum(capacidades[a] for a in pasillos_ordenados[:k])
            lista_k.append((k, suma_capacidad_k))

        lista_k.sort(key=lambda x: x[1], reverse=True)
        return [k for k, _ in lista_k]