from pyscipopt import Model, quicksum, Conshdlr, SCIP_PARAMSETTING
import time

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
        self.modelos_previos = {}

    def Rankear(self):
        capacidades = [sum(self.S[a]) for a in range(self.n_pasillos)]
        return sorted(range(self.n_pasillos), key=lambda a: capacidades[a], reverse=True)

    def Opt_cantidadPasillosFija(self, k, umbral):
        start = time.time()
        pasillos_base = self.Rankear()[:k]
        modelo = Model("Opt_cantidadPasillosFija")
        modelo.setPresolve(SCIP_PARAMSETTING.OFF)
        modelo.setParam('display/verblevel', 0)

        x = {o: modelo.addVar(vtype="B", name=f"x_{o}") for o in range(self.n_ordenes)}
        y = {a: modelo.addVar(vtype="B", name=f"y_{a}") for a in pasillos_base}

        total = quicksum(x[o] * sum(self.W[o][i] for i in range(self.n_elementos)) for o in range(self.n_ordenes))
        modelo.setObjective(total, "maximize")

        modelo.addCons(total >= self.LB, name="LB")
        modelo.addCons(total <= self.UB, name="UB")

        for i in range(self.n_elementos):
            demanda_i = quicksum(self.W[o][i] * x[o] for o in range(self.n_ordenes))
            capacidad_i = quicksum(self.S[a][i] * y[a] for a in pasillos_base)
            modelo.addCons(demanda_i <= capacidad_i, name=f"capacidad_{i}")

        modelo.addCons(quicksum(y[a] for a in pasillos_base) == k, name="pasillos_exactos")

        if time.time() - start > umbral:
            return {"valor_objetivo": -float("inf"), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        modelo.optimize()
        if modelo.getStatus() != "optimal":
            return {"valor_objetivo": -float("inf"), "ordenes_seleccionadas": [], "pasillos_seleccionados": []}

        ordenes_seleccionadas = [o for o in range(self.n_ordenes) if modelo.getVal(x[o]) > 0.5]
        pasillos_seleccionados = [a for a in pasillos_base if modelo.getVal(y[a]) > 0.5]
        valor_objetivo = modelo.getObjVal()

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

        modelo = Model("Opt_PasillosFijos")
        modelo.setPresolve(SCIP_PARAMSETTING.OFF)
        modelo.setParam('display/verblevel', 0)
        
        x = {o: modelo.addVar(vtype="B", name=f"x_{o}") for o in range(self.n_ordenes)}

        total = quicksum(x[o] * sum(self.W[o][i] for i in range(self.n_elementos)) for o in range(self.n_ordenes))
        modelo.setObjective(total, "maximize")

        modelo.addCons(total >= self.LB, name="LB")
        modelo.addCons(total <= self.UB, name="UB")

        for i in range(self.n_elementos):
            capacidad = sum(self.S[a][i] for a in self.pasillos_fijos)
            modelo.addCons(quicksum(self.W[o][i] * x[o] for o in range(self.n_ordenes)) <= capacidad, name=f"cap_{i}")

        if time.time() - start > umbral:
            return None

        modelo.optimize()
        if modelo.getStatus() != "optimal":
            return None

        ordenes = [o for o in range(self.n_ordenes) if modelo.getVal(x[o]) > 0.5]
        valor = modelo.getObjVal()

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
