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

    def Opt_ExplorarCantidadPasillos(self, umbral_total):
        start = time.time()

        # Inicializa la mejor solución y el mejor valor
        mejor_sol = None
        mejor_valor = -float('inf')

        # Obtiene una lista ordenada (ranking)
        ranking = self.Rankear()

        for k in ranking:
            # Calcula el tiempo restante para seguir ejecutando
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante <= 0:
                break

            # Genera una solución usando una cantidad fija de pasillos 'k'
            sol = self.Opt_cantidadPasillosFija(k, tiempo_restante)

            # Actualiza la mejor solución y su valor
            if sol and sol["valor_objetivo"] > mejor_valor:
                mejor_valor = sol["valor_objetivo"]
                mejor_sol = sol

        # Si se encontró una solución inicial válida
        if mejor_sol:
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante > 0:
                # Intenta refinar la solución
                sol_refinada = self.Opt_PasillosFijos(tiempo_restante)
                # Si la solución refinada es mejor, la actualiza como la mejor
                if sol_refinada and sol_refinada["valor_objetivo"] > mejor_valor:
                    mejor_sol = sol_refinada

        return mejor_sol

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