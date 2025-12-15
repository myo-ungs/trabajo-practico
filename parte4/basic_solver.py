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

        # Reconstruir el modelo para cada K (más compatible que copyOrig)
        modelo = Model(f"Modelo_k_{K}")
        modelo.setPresolve(SCIP_PARAMSETTING.OFF)
        modelo.setParam("display/verblevel", 0)

        x = {a: modelo.addVar(vtype="B", name=f"x_{a}") for a in range(self.n_pasillos)}
        y = {o: modelo.addVar(vtype="B", name=f"y_{o}") for o in range(self.n_ordenes)}

        for i in range(self.n_elementos):
            if timeout_check(umbral, start_time_ref):
                print("[TIMEOUT] Tiempo excedido durante la construccion del modelo.")
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
        start_time = time.time()
        
        def tiempo_consumido():
            return time.time() - start_time
            
        # 1. Chequeo de tiempo antes de construir el modelo
        if umbral is not None and tiempo_consumido() >= umbral:
            return None
            
        # Pasar el umbral y el tiempo de inicio para que la construcción del modelo
        # también respete el límite.
        modelo = self.modelo_para_k(k, umbral, start_time)
        if modelo is None:
            return None

        # 2. Chequeo de tiempo después de la construcción
        if umbral is not None and tiempo_consumido() >= umbral:
            return None

        # === Warm start ===
        if self.mejor_solucion and len(self.mejor_solucion["pasillos_seleccionados"]) == k:
            sol = modelo.createSol()
            
            pasillos = self.mejor_solucion["pasillos_seleccionados"]
            ordenes = self.mejor_solucion["ordenes_seleccionadas"]

            for var in modelo.getVars():
                if umbral is not None and tiempo_consumido() >= umbral:
                    # Cortar si el Warm Start consume demasiado tiempo
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

        # 3. Asignación estricta del tiempo restante a SCIP
        if umbral is not None:
            tiempo_restante_solver = max(1.0, umbral - tiempo_consumido()) # Minimo 1 segundo
            modelo.setParam("limits/time", tiempo_restante_solver)

        modelo.optimize()
        self.ultima_cota_dual = modelo.getDualbound()
        if self.ultima_cota_dual > self.mejor_cota_dual:
            self.mejor_cota_dual = self.ultima_cota_dual

        if modelo.getStatus() == "optimal" or modelo.getStatus() == "feasible":
            # Si el estado es optimo o factible, la solución es válida.
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
            
        # 1. Chequeo de tiempo antes de construir el modelo
        if umbral is not None and tiempo_consumido() >= umbral:
            return None
            
        k = len(self.mejores_pasillos)
        modelo = self.modelo_para_k(k, umbral, start_time)
        if modelo is None:
            return None
        
        # 2. Chequeo de tiempo después de la construcción
        if umbral is not None and tiempo_consumido() >= umbral:
            return None

        # Fijar variables de pasillos
        for var in modelo.getVars():
            if umbral is not None and tiempo_consumido() >= umbral:
                # Cortar si la fijación consume demasiado tiempo
                return None
                
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

        # 3. Asignación estricta del tiempo restante a SCIP
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
        
        # Estrategia de exploración simplificada
        k_list = self.Rankear()
        
        # Asignación de tiempo (ejemplo: 90% para exploración, 10% para Opt_PasillosFijos)
        tiempo_exploracion_max = umbral_total * 0.9 
        
        # Asignar tiempo por cada K
        tiempo_por_k = tiempo_exploracion_max / len(k_list) if k_list else 0
        
        for k in k_list:
            tiempo_transcurrido = time.time() - start
            tiempo_restante_total = umbral_total - tiempo_transcurrido
            
            # Chequeo estricto del tiempo restante antes de intentar una optimización
            if tiempo_restante_total <= 5: # Dejar al menos 5 segundos para la parte final
                print(f"[TIMEOUT] Tiempo limite alcanzado. Tiempo restante: {tiempo_restante_total:.2f}s")
                break

            # Usar el mínimo entre tiempo_por_k y el tiempo restante disponible 
            # (dejando un pequeño margen)
            tiempo_para_este_k = max(1.0, min(tiempo_por_k, tiempo_restante_total - 5))
            
            solucion = self.Opt_cantidadPasillosFija(k, tiempo_para_este_k)
            if solucion and solucion["valor_objetivo"] > mejor_valor:
                mejor_valor = solucion["valor_objetivo"]
                mejor_sol = solucion

        if mejor_sol:
            self.mejores_pasillos = mejor_sol["pasillos_seleccionados"]
            tiempo_restante_final = umbral_total - (time.time() - start)
            
            # Solo ejecutar Opt_PasillosFijos si queda suficiente tiempo (e.g., más de 5 segundos)
            if tiempo_restante_final > 5:
                # Asignar el tiempo restante menos un pequeño margen de seguridad
                tiempo_para_fijos = max(1.0, tiempo_restante_final - 2)
                
                solucion_para_k_fijo = self.Opt_PasillosFijos(tiempo_para_fijos)
                if solucion_para_k_fijo and solucion_para_k_fijo["valor_objetivo"] > mejor_valor:
                    mejor_sol = solucion_para_k_fijo

        self.mejor_solucion = mejor_sol
        return mejor_sol