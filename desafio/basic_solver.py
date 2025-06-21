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

        #para guardar modelos anteriores por valor de k 
        self.modelos_previos = {}


    def Opt_cantidadPasillosFija(self, k, umbral):
        start = time.time()

        # Ver si hay un modelo anterior que podamos reutilizar
        if k - 1 in self.modelos_previos:
            print(f"Reutilizando modelo con k={k-1} para construir modelo con k={k}")

            # No podemos copiar directamente el modelo, pero sí reusar la selección de pasillos
            modelo_previo = self.modelos_previos[k - 1]
            pasillos_previos = modelo_previo["pasillos_seleccionados"]

            # Usamos esos mismos pasillos como base, y agregamos uno nuevo
            posibles_pasillos = set(range(self.n_pasillos)) - set(pasillos_previos)
            if not posibles_pasillos:
                return {"valor_objetivo": -float('inf'), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

            nuevo_pasillo = posibles_pasillos.pop()
            pasillos_base = pasillos_previos + [nuevo_pasillo]

        else:
            # Si no hay modelo previo, seleccionamos aleatoriamente k pasillos
            pasillos_base = list(range(k))

        # Construimos el modelo desde cero, pero usando pasillos_base como conjunto permitido
        modelo = LpProblem("Opt_cantidadPasillosFija", LpMaximize)
        x = LpVariable.dicts("x", range(self.n_ordenes), cat=LpBinary)
        y = {a: LpVariable(f"y_{a}", cat=LpBinary) for a in pasillos_base}

        # Objetivo: maximizar la cantidad total recolectada
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos)), "Obj"

        # Restricciones de LB y UB
        total_recolectado = lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes) for i in range(self.n_elementos))
        modelo += total_recolectado >= self.LB
        modelo += total_recolectado <= self.UB

        # Restricción de disponibilidad de elementos por pasillos seleccionados
        for i in range(self.n_elementos):
            modelo += lpSum(self.W[o][i] * x[o] for o in range(self.n_ordenes)) <= lpSum(
                self.S[a][i] * y[a] for a in pasillos_base)

        # Solo se pueden usar k pasillos
        modelo += lpSum(y[a] for a in pasillos_base) == k

        # Control de tiempo
        if time.time() - start > umbral:
            return {"valor_objetivo": -float('inf'), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        modelo.solve()

        if LpStatus[modelo.status] != "Optimal":
            return {"valor_objetivo": -float('inf'), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        # Resultado
        ordenes_seleccionadas = [o for o in range(self.n_ordenes) if x[o].varValue == 1]
        pasillos_seleccionados = [a for a in pasillos_base if y[a].varValue == 1]
        valor_objetivo = value(modelo.objective)

        self.pasillos_fijos = pasillos_seleccionados

        # Guardar modelo para reutilizar en k+1
        self.modelos_previos[k] = {
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": pasillos_seleccionados,
            "valor_objetivo": valor_objetivo
        }

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

        mejor_sol = None
        mejor_valor = -float('inf')

        # Ranking de valores de k (cantidad de pasillos)
        ranking = self.Rankear()

        for k in ranking:
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante <= 0:
                print("Se acabó el tiempo total")
                break

            # Intentamos resolver el problema con k pasillos
            print(f"Probando con k = {k} (tiempo restante: {round(tiempo_restante, 2)} seg)")
            sol = self.Opt_cantidadPasillosFija(k, tiempo_restante)

            if sol and sol["valor_objetivo"] > mejor_valor:
                mejor_valor = sol["valor_objetivo"]
                mejor_sol = sol

        # Reoptimizar con los mejores pasillos encontrados
        if mejor_sol:
            print(f"Reoptimizando con los pasillos seleccionados por k = {len(mejor_sol['pasillos_seleccionados'])}")
            self.pasillos_fijos = mejor_sol["pasillos_seleccionados"]
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante > 0:
                sol_refinada = self.Opt_PasillosFijos(tiempo_restante)
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