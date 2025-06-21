import time
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpBinary, LpStatus, value


class Columns:
    def __init__(self, W, S, LB, UB):
        self.W = W
        self.S = S
        self.LB = LB
        self.UB = UB
        self.n_ordenes = len(W)
        self.n_elementos = len(W[0])
        self.n_pasillos = len(S)

        # Diccionario para guardar modelos por k
        # Cada entrada: {"modelo": LpProblem, "lambda": dict, "columnas": list de columnas}
        self.modelos = {}

        # Pasillos fijos para Opt_PasillosFijos
        self.pasillos_fijos = []

    def construir_columnas_iniciales(self):
        columnas = []
        for a in range(self.n_pasillos):
            # Tomamos órdenes máximas factibles para pasillo a
            ordenes = self.ordenes_maximas_para_pasillo(a)
            columnas.append({"pasillo": a, "ordenes": ordenes})
        return columnas

    def ordenes_maximas_para_pasillo(self, a):
        # Retorna lista de órdenes factibles y maximizadas para pasillo a
        ordenes_factibles = []
        for o in range(self.n_ordenes):
            factible = True
            for i in range(self.n_elementos):
                if self.W[o][i] > self.S[a][i]:
                    factible = False
                    break
            if factible:
                ordenes_factibles.append(o)
        return ordenes_factibles

    def construir_modelo(self, k):
        # Construye modelo maestro para k pasillos con columnas iniciales
        modelo = LpProblem(f"Maestro_k_{k}", LpMaximize)

        columnas = self.construir_columnas_iniciales()
        n_col = len(columnas)

        # Variables lambda para cada columna (patrón)
        lambdas = {
            j: LpVariable(f"lambda_{j}", cat=LpBinary)
            for j in range(n_col)
        }

        # Función objetivo: max suma beneficios de órdenes seleccionadas por columnas
        modelo += lpSum(
            lambdas[j] * sum(
                self.W[o][i] for o in columnas[j]["ordenes"] for i in range(self.n_elementos)
            )
            for j in range(n_col)
        ), "TotalBeneficio"

        # Restricción: cada orden aparece a lo sumo una vez
        for o in range(self.n_ordenes):
            modelo += lpSum(
                lambdas[j] for j in range(n_col) if o in columnas[j]["ordenes"]
            ) <= 1, f"Orden_{o}_una_vez"

        # Restricción: se eligen exactamente k pasillos (una por columna)
        modelo += lpSum(
            lambdas[j] for j in range(n_col)
        ) == k, "CantidadPasillos"

        return modelo, columnas, lambdas

    def agregar_columna(self, k, columna_nueva):
        modelo_data = self.modelos[k]
        modelo = modelo_data["modelo"]
        columnas = modelo_data["columnas"]
        lambdas = modelo_data["lambda"]

        j = len(columnas)
        columnas.append(columna_nueva)
        # Crear nueva variable lambda
        lambda_j = LpVariable(f"lambda_{j}", cat=LpBinary)
        lambdas[j] = lambda_j

        # Coeficiente en la función objetivo
        beneficio = sum(
            self.W[o][i] for o in columna_nueva["ordenes"] for i in range(self.n_elementos)
        )
        modelo.objective += beneficio * lambda_j

        # Restricción para cada orden en la nueva columna
        for o in columna_nueva["ordenes"]:
            restriccion_nombre = f"Orden_{o}_una_vez"
            if restriccion_nombre in modelo.constraints:
                modelo.constraints[restriccion_nombre].addterm(lambda_j, 1)
            else:
                modelo += lambda_j <= 1, restriccion_nombre

        # Restricción de cantidad de pasillos: actualizar para incluir nueva lambda
        restriccion_pasillos = modelo.constraints["CantidadPasillos"]
        restriccion_pasillos.addterm(lambda_j, 1)

    def Opt_cantidadPasillosFija(self, k, umbral):
        start = time.time()

        # Si no hay modelo para k, construirlo
        if k not in self.modelos:
            modelo, columnas, lambdas = self.construir_modelo(k)
            self.modelos[k] = {
                "modelo": modelo,
                "columnas": columnas,
                "lambda": lambdas
            }
        else:
            modelo = self.modelos[k]["modelo"]
            columnas = self.modelos[k]["columnas"]
            lambdas = self.modelos[k]["lambda"]

        # Resolver modelo
        modelo.solve()

        if LpStatus[modelo.status] != "Optimal":
            return {"valor_objetivo": -float('inf'), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        # Extraer solución
        seleccionadas = [j for j, var in lambdas.items() if var.varValue >= 0.99]

        pasillos_seleccionados = set()
        ordenes_seleccionadas = set()
        for idx in seleccionadas:
            col = columnas[idx]
            pasillos_seleccionados.add(col["pasillo"])
            ordenes_seleccionadas.update(col["ordenes"])

        valor_objetivo = value(modelo.objective)

        # Guardar pasillos fijos para Opt_PasillosFijos
        self.pasillos_fijos = list(pasillos_seleccionados)

        # Guardar modelo para poder buscar columnas mejoradoras
        self.modelos[k]["modelo"] = modelo
        self.modelos[k]["columnas"] = columnas
        self.modelos[k]["lambda"] = lambdas

        # Intentar generar columna mejoradora si queda tiempo
        tiempo_restante = umbral - (time.time() - start)
        if tiempo_restante > 0:
            nueva_columna = self.BuscarColumnaMejoradora(k)
            if nueva_columna:
                print(f"Columna mejoradora encontrada para k={k}, agregando al modelo.")
                self.agregar_columna(k, nueva_columna)
                modelo.solve()
                print("Modelo resuelto con la nueva columna.")

                # Actualizar solución luego de agregar columna
                lambdas = self.modelos[k]["lambda"]
                seleccionadas = [j for j, var in lambdas.items() if var.varValue >= 0.99]
                pasillos_seleccionados = set()
                ordenes_seleccionadas = set()
                for idx in seleccionadas:
                    col = columnas[idx]
                    pasillos_seleccionados.add(col["pasillo"])
                    ordenes_seleccionadas.update(col["ordenes"])
                valor_objetivo = value(modelo.objective)
                self.pasillos_fijos = list(pasillos_seleccionados)

        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": list(ordenes_seleccionadas),
            "pasillos_seleccionados": list(pasillos_seleccionados)
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

        ranking = self.Rankear()

        for k in ranking:
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
            print(f"Reoptimizando con los pasillos seleccionados por k = {len(mejor_sol['pasillos_seleccionados'])}")
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

        lista_k = []
        for k in range(1, self.n_pasillos + 1):
            suma_capacidad_k = sum(capacidades[a] for a in pasillos_ordenados[:k])
            lista_k.append((k, suma_capacidad_k))

        lista_k.sort(key=lambda x: x[1], reverse=True)
        return [k for k, _ in lista_k]

    def BuscarColumnaMejoradora(self, k):
        modelo_data = self.modelos[k]
        modelo = modelo_data["modelo"]
        columnas = modelo_data["columnas"]

        # Obtener duales de restricciones
        duales = {}
        for nombre, restriccion in modelo.constraints.items():
            try:
                duales[nombre] = restriccion.pi
            except AttributeError:
                duales[nombre] = 0.0

        # Buscar columna mejoradora
        for a in range(self.n_pasillos):
            ordenes_factibles = self.ordenes_maximas_para_pasillo(a)

            # Costo reducido simplificado: beneficio - suma de duales
            beneficio = sum(
                sum(self.W[o][i] for i in range(self.n_elementos))
                for o in ordenes_factibles
            )
            suma_duales = sum(duales.get(f"Orden_{o}_una_vez", 0.0) for o in ordenes_factibles)
            costo_reducido = beneficio - suma_duales

            if costo_reducido < -1e-5:
                return {"pasillo": a, "ordenes": ordenes_factibles}

        return None
