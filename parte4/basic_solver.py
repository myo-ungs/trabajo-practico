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

    def modelo_para_k(self, K, umbral=None, start_time_ref=None):
        if start_time_ref is None:
            start_time_ref = time.time()
            
        def timeout_check(umbral, start_time):
            return umbral is not None and (time.time() - start_time > umbral)

        modelo = Model(f"Modelo_k_{K}")
        modelo.setPresolve(SCIP_PARAMSETTING.OFF)
        modelo.setParam("display/verblevel", 0)

        x = {a: modelo.addVar(vtype="B", name=f"x_{a}") for a in range(self.n_pasillos)}
        y = {o: modelo.addVar(vtype="B", name=f"y_{o}") for o in range(self.n_ordenes)}

        for i in range(self.n_elementos):
            if timeout_check(umbral, start_time_ref):
                return None
            modelo.addCons(
                quicksum(self.W[o][i] * y[o] for o in y) <= quicksum(self.S[a][i] * x[a] for a in x),
                name=f"cap_{i}"
            )

        modelo.addCons(quicksum(x.values()) == K, name="cons_k")
        
        total = quicksum(self.W[o][i] * y[o] for o in y for i in range(self.n_elementos))
        modelo.addCons(total >= self.LB, name="LB")
        modelo.addCons(total <= self.UB, name="UB")
        modelo.setObjective(total, "maximize")

        return modelo

    def Rankear(self):
        return list(range(1, self.n_pasillos + 1))

    def Opt_cantidadPasillosFija(self, k, umbral):
        start_time = time.time()
        
        def tiempo_consumido():
            return time.time() - start_time
            
        if umbral is not None and tiempo_consumido() >= umbral:
            return None
            
        modelo = self.modelo_para_k(k, umbral, start_time)
        if modelo is None:
            return None

        if umbral is not None and tiempo_consumido() >= umbral:
            return None

        if self.mejor_solucion and len(self.mejor_solucion["pasillos_seleccionados"]) == k:
            sol = modelo.createSol()
            
            pasillos = self.mejor_solucion["pasillos_seleccionados"]
            ordenes = self.mejor_solucion["ordenes_seleccionadas"]

            for var in modelo.getVars():
                if umbral is not None and tiempo_consumido() >= umbral:
                    return None
                    
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

        if umbral is not None:
            tiempo_restante_solver = max(1.0, umbral - tiempo_consumido()) # Minimo 1 segundo
            modelo.setParam("limits/time", tiempo_restante_solver)

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
        start_time = time.time()
        
        def tiempo_consumido():
            return time.time() - start_time
            
        if umbral is not None and tiempo_consumido() >= umbral:
            return None
            
        k = len(self.mejores_pasillos)
        modelo = self.modelo_para_k(k, umbral, start_time)
        if modelo is None:
            return None
        
        if umbral is not None and tiempo_consumido() >= umbral:
            return None

        for var in modelo.getVars():
            if umbral is not None and tiempo_consumido() >= umbral:
                return None
                
            if var.name.startswith("x_"):
                idx = int(var.name.split("_")[1])
                if idx in self.mejores_pasillos:
                    modelo.chgVarLb(var, 1.0)
                    modelo.chgVarUb(var, 1.0)
                else:
                    modelo.chgVarUb(var, 0.0)

        y_vars = [var for var in modelo.getVars() if var.name.startswith("y_")]
        total_unidades = quicksum(
            sum(self.W[int(var.name.split("_")[1])][i] for i in range(self.n_elementos)) * var
            for var in y_vars
        )
        modelo.addCons(total_unidades >= self.LB, name="restr_total_lb")

        if umbral is not None:
            tiempo_restante_solver = max(1.0, umbral - tiempo_consumido()) # Minimo 1 segundo
            modelo.setParam("limits/time", tiempo_restante_solver)

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
        
        tiempo_exploracion_max = umbral_total * 0.9 
        
        tiempo_por_k = tiempo_exploracion_max / len(k_list) if k_list else 0
        
        for k in k_list:
            tiempo_transcurrido = time.time() - start
            tiempo_restante_total = umbral_total - tiempo_transcurrido
            
            if tiempo_restante_total <= 5: 
                print(f"[TIMEOUT] Tiempo limite alcanzado. Tiempo restante: {tiempo_restante_total:.2f}s")
                break

            tiempo_para_este_k = max(1.0, min(tiempo_por_k, tiempo_restante_total - 5))
            
            solucion = self.Opt_cantidadPasillosFija(k, tiempo_para_este_k)
            if solucion and solucion["valor_objetivo"] > mejor_valor:
                mejor_valor = solucion["valor_objetivo"]
                mejor_sol = solucion

        if mejor_sol:
            self.mejores_pasillos = mejor_sol["pasillos_seleccionados"]
            tiempo_restante_final = umbral_total - (time.time() - start)
            
            if tiempo_restante_final > 5:
                tiempo_para_fijos = max(1.0, tiempo_restante_final - 2)
                
                solucion_para_k_fijo = self.Opt_PasillosFijos(tiempo_para_fijos)
                if solucion_para_k_fijo and solucion_para_k_fijo["valor_objetivo"] > mejor_valor:
                    mejor_sol = solucion_para_k_fijo

        self.mejor_solucion = mejor_sol
        return mejor_sol