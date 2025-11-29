from pyscipopt import Model, quicksum, SCIP_PARAMSETTING
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
        self.mejores_pasillos = set()
        self.mejor_solucion = None
        self.ultima_cota_dual = -float("inf")
        self.mejor_cota_dual = -float("inf")
        self.modelo_maestro = None
        self.restriccion_k = None

    def construir_maestro(self, umbral=None):
        start_time = time.time()
        maestro = Model("Modelo maestro") 
        maestro.setPresolve(SCIP_PARAMSETTING.OFF)
        maestro.setParam("display/verblevel", 0)

        x = {a: maestro.addVar(vtype="B", name=f"x_{a}") for a in range(self.n_pasillos)}
        y = {o: maestro.addVar(vtype="B", name=f"y_{o}") for o in range(self.n_ordenes)}

        for i in range(self.n_elementos):
            if umbral and (time.time() - start_time > umbral):
                print("⏱️ Tiempo excedido durante la construcción del maestro.")
                return None, None
            maestro.addCons( quicksum(self.W[o][i] * y[o] for o in y) <= quicksum(self.S[a][i] * x[a] for a in x),
                name=f"cap_{i}"
            )

        restriccion_k = maestro.addCons(quicksum(x.values()) == 1, name="cons_k")
        total = quicksum(self.W[o][i] * y[o] for o in y for i in range(self.n_elementos))

        maestro.addCons(total >= self.LB, name="LB")
        maestro.addCons(total <= self.UB, name="UB")
        maestro.setObjective(total, "maximize")

        return maestro, restriccion_k

    def modelo_para_k(self, K, umbral=None):
        # Reconstruir el modelo para cada K (más compatible que copyOrig)
        start_time = time.time()
        modelo = Model(f"Modelo_k_{K}")
        modelo.setPresolve(SCIP_PARAMSETTING.OFF)
        modelo.setParam("display/verblevel", 0)

        x = {a: modelo.addVar(vtype="B", name=f"x_{a}") for a in range(self.n_pasillos)}
        y = {o: modelo.addVar(vtype="B", name=f"y_{o}") for o in range(self.n_ordenes)}

        for i in range(self.n_elementos):
            if umbral and (time.time() - start_time > umbral):
                print("⏱️ Tiempo excedido durante la construcción del modelo.")
                return None
            modelo.addCons(
                quicksum(self.W[o][i] * y[o] for o in y) <= quicksum(self.S[a][i] * x[a] for a in x),
                name=f"cap_{i}"
            )

        # Restricción de cantidad de pasillos = K
        modelo.addCons(quicksum(x.values()) == K, name="cons_k")
        
        total = quicksum(self.W[o][i] * y[o] for o in y for i in range(self.n_elementos))
        modelo.addCons(total >= self.LB, name="LB")
        modelo.addCons(total <= self.UB, name="UB")
        modelo.setObjective(total, "maximize")

        return modelo

    def Rankear(self):
        return list(range(1, self.n_pasillos + 1))

    def Opt_cantidadPasillosFija(self, k, umbral):
        modelo = self.modelo_para_k(k, umbral)
        if modelo is None:
            return None

        if self.mejor_solucion and len(self.mejor_solucion["pasillos_seleccionados"]) == k:
            sol = modelo.createSol()
            
            pasillos = self.mejor_solucion["pasillos_seleccionados"]
            ordenes = self.mejor_solucion["ordenes_seleccionadas"]

            for var in modelo.getVars():
                nombre, indice = var.name.split("_")
                indice = int(indice)
                if nombre == "x":
                    valor = 1.0 if indice in pasillos else 0.0
                elif nombre == "y":
                    valor = 1.0 if indice in ordenes else 0.0
                else:
                    continue  
                modelo.setSolVal(sol, var, valor)
            modelo.addSol(sol, False)

        if umbral:
            modelo.setParam("limits/time", umbral)

        modelo.optimize()
        self.ultima_cota_dual = modelo.getDualbound()
        if self.ultima_cota_dual > self.mejor_cota_dual:
            self.mejor_cota_dual = self.ultima_cota_dual

        if modelo.getStatus() == "optimal" or modelo.getStatus() == "feasible":
            pasillos = {int(v.name.split("_")[1]) for v in modelo.getVars()if v.name.startswith("x_") and modelo.getVal(v) > 0.5}
            ordenes = {int(v.name.split("_")[1]) for v in modelo.getVars()if v.name.startswith("y_") and modelo.getVal(v) > 0.5}
            total = sum(sum(self.W[o][i] for i in range(self.n_elementos)) for o in ordenes)
            sol = { "valor_objetivo": total / len(pasillos) if pasillos else 0, "ordenes_seleccionadas": ordenes, "pasillos_seleccionados": pasillos}
            self.mejor_solucion = sol
            return sol
        else:
            return None

    def Opt_PasillosFijos(self, umbral):
        k = len(self.mejores_pasillos)
        modelo = self.modelo_para_k(k, umbral)
        if modelo is None:
            return None

        for var in modelo.getVars():
            if var.name.startswith("x_"):
                idx = int(var.name.split("_")[1])
                if idx in self.mejores_pasillos:
                    modelo.chgVarLb(var, 1.0)
                    modelo.chgVarUb(var, 1.0)
                else:
                    modelo.chgVarUb(var, 0.0)

        # Agregar restricción para asegurar que las unidades >= LB
        y_vars = [var for var in modelo.getVars() if var.name.startswith("y_")]
        total_unidades = quicksum(
            sum(self.W[int(var.name.split("_")[1])][i] for i in range(self.n_elementos)) * var
            for var in y_vars
        )
        modelo.addCons(total_unidades >= self.LB, name="restr_total_lb")

        if umbral:
            modelo.setParam("limits/time", umbral)

        modelo.optimize()

        if modelo.getStatus() == "optimal" or modelo.getStatus() == "feasible":
            pasillos = {int(v.name.split("_")[1]) for v in modelo.getVars() if v.name.startswith("x_") and modelo.getVal(v) > 0.5}
            ordenes = {int(v.name.split("_")[1]) for v in modelo.getVars() if v.name.startswith("y_") and modelo.getVal(v) > 0.5}
            total = sum(sum(self.W[o][i] for i in range(self.n_elementos)) for o in ordenes)
            sol = { "valor_objetivo": total / len(pasillos) if pasillos else 0, "ordenes_seleccionadas": ordenes, "pasillos_seleccionados": pasillos}
            self.mejor_solucion = sol
            return sol
        else:
            return None
        

    def Opt_ExplorarCantidadPasillos(self, umbral_total):
        start = time.time()
        mejor_sol = None
        mejor_valor = -float("inf")
        k_list = self.Rankear()

        for k in k_list:
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante <= 0:
                break

            solucion = self.Opt_cantidadPasillosFija(k, tiempo_restante)
            if solucion and solucion["valor_objetivo"] > mejor_valor:
                mejor_valor = solucion["valor_objetivo"]
                mejor_sol = solucion

        if mejor_sol:
            self.mejores_pasillos = mejor_sol["pasillos_seleccionados"]
            tiempo_restante = umbral_total - (time.time() - start)
            if tiempo_restante > 0:
                solucion_para_k_fijo = self.Opt_PasillosFijos(tiempo_restante)
                if solucion_para_k_fijo and solucion_para_k_fijo["valor_objetivo"] > mejor_valor:
                    mejor_sol = solucion_para_k_fijo

        self.mejor_solucion = mejor_sol
        return mejor_sol