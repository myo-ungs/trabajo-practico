import time
import random
from pyscipopt import Model, quicksum, SCIP_PARAMSETTING

def construir_mejor_solucion(modelo_relajado, columnas_k, obj_val, cant_var_inicio):
    pasillos_seleccionados = set()
    ordenes_seleccionadas = set()

    for idx, x in enumerate(modelo_relajado.getVars()):
        if x.getLPSol() and x.getLPSol() > 1e-5:
            pasillos_seleccionados.add(columnas_k[idx]['pasillo'])
            for o, val in enumerate(columnas_k[idx]['ordenes']):
                if val:
                    ordenes_seleccionadas.add(o)

    mejor_sol = {
        "valor_objetivo": int(obj_val),
        "pasillos_seleccionados": pasillos_seleccionados,
        "ordenes_seleccionadas": ordenes_seleccionadas,
        "variables": cant_var_inicio,
        "variables_final": modelo_relajado.getNVars(),
        "cota_dual": modelo_relajado.getDualbound()
    }

    return mejor_sol

class Columns:
    def __init__(self, W, S, LB, UB):
        self.W = W
        self.S = S
        self.LB = LB
        self.UB = UB
        self.O = len(W)
        self.I = len(W[0])
        self.A = len(S)
        self.columnas = {}
        self.pasillos_fijos = []
        self.cant_var_inicio = 0

    def inicializar_columnas_para_k(self, k, umbral=None, limite_columnas=None):
        import time
        tiempo_ini = time.time()

        if not hasattr(self, 'columnas'):
            self.columnas = {}

        self.columnas[k] = []
        unidades_o = [sum(self.W[o]) for o in range(self.O)]
        columnas_creadas = 0

        for a in range(self.A):
            if umbral and (time.time() - tiempo_ini) > umbral:
                print("⏱️ Tiempo agotado durante inicialización de columnas")
                break

            if limite_columnas is not None and columnas_creadas >= limite_columnas:
                print(f"🛑 Límite de {limite_columnas} columnas alcanzado")
                break

            cap_restante = list(self.S[a])
            sel = [0] * self.O
            total_unidades = 0

            # Agregar órdenes greedy mientras entren
            for o in range(self.O):
                if all(self.W[o][i] <= cap_restante[i] for i in range(self.I)) and \
                (total_unidades + unidades_o[o] <= self.UB):
                    sel[o] = 1
                    total_unidades += unidades_o[o]
                    for i in range(self.I):
                        cap_restante[i] -= self.W[o][i]

            # Solo agregar columna si es factible (al menos una orden)
            if total_unidades > 0:
                self.columnas[k].append({
                    'pasillo': a,
                    'ordenes': sel,
                    'unidades': total_unidades
                })
                columnas_creadas += 1

        print(f"✅ {len(self.columnas[k])} columnas iniciales creadas (una por pasillo) para k = {k}")


        tiempo_ini = time.time()
        if k not in self.columnas:
            columnas_iniciales = []
            unidades_o = [sum(self.W[o]) for o in range(self.O)]

            for o in range(self.O):
                # print("coluumna", (time.time() - tiempo_ini), umbral)
                
                if umbral and (time.time() - tiempo_ini) > umbral:
                    print("⏱️ Tiempo agotado durante inicialización de columnas")
                    break

                for a in range(self.A):
                    if umbral and (time.time() - tiempo_ini) > umbral:
                        print("⏱️ Tiempo agotado durante inicialización de columnas (interior)")
                        break

                    cap = self.S[a][:]
                    if all(self.W[o][i] <= cap[i] for i in range(self.I)) and unidades_o[o] <= self.UB:
                        sel = [0] * self.O
                        sel[o] = 1
                        columnas_iniciales.append({'pasillo': a, 'ordenes': sel, 'unidades': unidades_o[o]})
                        break  # No sigue buscando pasillos para esta orden

            self.columnas[k] = columnas_iniciales
    def construir_modelo_maestro(self, k, umbral):
        modelo = Model(f"RMP_k_{k}")
        modelo.setParam('display/verblevel', 0)
        x_vars = []
        
        # Agregar variables x_j
        for idx, col in enumerate(self.columnas[k]):
            x = modelo.addVar(vtype="B", name=f"x_{col['pasillo']}_{idx}")
            x_vars.append(x)

        # Restricción de cardinalidad
        restr_card_k = modelo.addCons(quicksum(x_vars) == k, name="card_k")

        # Restricciones por orden
        restr_ordenes = {}
        for o in range(self.O):
            cons = modelo.addCons(
                quicksum(x_vars[j] * self.columnas[k][j]['ordenes'][o] for j in range(len(x_vars))) <= 1,
                name=f"orden_{o}"
            )
            restr_ordenes[o] = cons

        # Restricción de unidades totales
        restr_ub = modelo.addCons(
            quicksum(x_vars[j] * self.columnas[k][j]['unidades'] for j in range(len(x_vars))) <= self.UB,
            name="restr_total_ub"
        )

        # restr_lb = modelo.addCons(
        #     quicksum(x_vars[j] * self.columnas[k][j]['unidades'] for j in range(len(x_vars))) >= self.UB,
        #     name="restr_total_lb"
        # )

        # Restricciones de cobertura por ítem
        restr_cov = {}
        for i in range(self.I):
            cons = modelo.addCons(
                quicksum(
                    x_vars[j] * sum(self.W[o][i] for o in range(self.O) if self.columnas[k][j]['ordenes'][o])
                    for j in range(len(x_vars))
                ) <= quicksum(
                    x_vars[j] * self.S[self.columnas[k][j]['pasillo']][i]
                    for j in range(len(x_vars))
                )
            )
            restr_cov[i] = cons

        # Función objetivo: maximizar unidades totales
        modelo.setObjective(
            quicksum(
                x_vars[j] * sum(
                    self.W[o][i]
                    for o in range(self.O) if self.columnas[k][j]['ordenes'][o]
                    for i in range(self.I)
                )
                for j in range(len(x_vars))
            ),
            sense="maximize"
        )

        return modelo, x_vars, restr_card_k, restr_ordenes, restr_ub, restr_cov

    def resolver_subproblema(self, W, S, pi, UB, k, umbral=None):
        import time
        tiempo_ini = time.time()

        O = len(W)
        I = len(W[0])
        A = len(S)

        units_o = [sum(W[o]) for o in range(O)]

        # Obtener duales
        pi_card_k = pi[0]                           # Yk
        pi_ordenes = pi[1:1 + O]                    # αo
        pi_ub = pi[1 + O]                           # λ
        pi_cov = pi[2 + O : 2 + O + I]              # πi

        for a in range(A):
            if umbral and (time.time() - tiempo_ini) > umbral:
                print("⏱️ Tiempo agotado durante subproblema")
                break

            supply = S[a]

            # Calcular costo reducido de cada orden
            price_o = []
            for o in range(O):
                rc_part = units_o[o]                                   # uo
                rc_part -= sum(W[o][i] * pi_cov[i] for i in range(I))  # - ∑ πi * W[o][i]
                rc_part -= pi_ub * units_o[o]                          # - λ * uo
                rc_part -= pi_ordenes[o]                               # - αo
                price_o.append(rc_part)

            modelo = Model(f"Subproblema_Pasillo_{a}")
            modelo.setParam("display/verblevel", 0)

            z = {o: modelo.addVar(vtype="B", obj=price_o[o], name=f"z_{o}") for o in range(O)}

            for i in range(I):
                modelo.addCons(
                    quicksum(W[o][i] * z[o] for o in range(O)) <= supply[i]
                )

            modelo.addCons(quicksum(units_o[o] * z[o] for o in range(O)) <= UB)
            modelo.addCons(quicksum(z[o] for o in range(O)) >= 1)

            # Evitar columnas exactamente iguales ya generadas
            for c in self.columnas[k]:
                if c['pasillo'] != a:
                    continue  # Solo columnas del mismo pasillo

                mismos = [o for o in range(O) if c['ordenes'][o] == 1]
                if mismos:
                    modelo.addCons(
                        quicksum(z[o] for o in mismos) <= len(mismos) - 1
                    )

            # Objetivo: maximizar costo reducido
            modelo.setObjective(
                quicksum(price_o[o] * z[o] for o in range(O)) - pi_card_k,
                sense="maximize"
            )

            modelo.optimize()

            if modelo.getStatus() != "optimal":
                continue

            reduced_cost = modelo.getObjVal()
            print(f"[Pasillo {a}] → Costo reducido: {reduced_cost}")

            if reduced_cost <= 1e-6:
                continue

            ordenes = [int(modelo.getVal(z[o]) + 0.5) for o in range(O)]
            unidades = sum(units_o[o] for o in range(O) if ordenes[o])
            columna = {'pasillo': a, 'ordenes': ordenes, 'unidades': unidades}

            if columna in self.columnas[k]:
                print("Genere pero es repe⚠️", columna)
                continue

            self.columnas[k].append(columna)
            return columna

        return None


    def agregar_columna(self, maestro, nueva_col, x_vars, restr_card_k, restr_ordenes, restr_ub, restr_cov, k):
        idx = len(self.columnas[k])  # índice para nombrar la nueva variable
        x = maestro.addVar(vtype="B", name=f"x_{nueva_col['pasillo']}_{idx}", obj=nueva_col['unidades'])
        x_vars.append(x)

        # Restricción de cardinalidad
        maestro.addConsCoeff(restr_card_k, x, 1)

        # Restricciones por orden
        for o in range(self.O):
            maestro.addConsCoeff(restr_ordenes[o], x, nueva_col['ordenes'][o])

        # Restricción de unidades totales
        maestro.addConsCoeff(restr_ub, x, nueva_col['unidades'])

        # Restricciones de cobertura por ítem
        for i in range(self.I):
            contribucion_i = sum(self.W[o][i] * nueva_col['ordenes'][o] for o in range(self.O))
            if contribucion_i > 0:
                maestro.addConsCoeff(restr_cov[i], x, contribucion_i)


    def Opt_cantidadPasillosFija(self, k, umbral):
        tiempo_ini = time.time()
        
        # Reservar 30% del tiempo para inicialización
        tiempo_inicializacion = 0.3 * umbral

        self.inicializar_columnas_para_k(k, umbral=tiempo_inicializacion)
        
        mejor_sol = None
        primera_iteracion = True
            
        while True:
            tiempo_actual = time.time()
            tiempo_transcurrido = tiempo_actual - tiempo_ini
            tiempo_restante_total = umbral - tiempo_transcurrido

            if tiempo_restante_total <= 0:
                print("⏳ Tiempo agotado en Opt_cantidadPasillosFija → Fin del bucle.")
                break

            print(f"⌛ Iteración con {len(self.columnas[k])} columnas")

            # Construyo el modelo maestro
            maestro, x_vars, restr_card_k, restr_ordenes, restr_ub, restr_cov = self.construir_modelo_maestro(k, tiempo_restante_total)

            # Copia del modelo maestro
            maestro_relajado = Model(sourceModel=maestro)

            # Desctivo para obtener los duales y restricciones correctamente
            maestro_relajado.setPresolve(SCIP_PARAMSETTING.OFF)
            maestro_relajado.setHeuristics(SCIP_PARAMSETTING.OFF)
            maestro_relajado.disablePropagation()

            # Relajo el modelo maestro
            maestro_relajado.relax()
            maestro_relajado.optimize()

            # Obtener la cant de variables del 1er modelo maestro
            if primera_iteracion:
                self.cant_var_inicio = maestro_relajado.getNVars()
                primera_iteracion = False

            # Obtener los duales
            if maestro_relajado.getStatus() == "optimal":
                pi = [maestro_relajado.getDualsolLinear(c) for c in maestro_relajado.getConss()]
            else:
                print("⚠️ No se encontró solución. Estado del modelo:", maestro_relajado.getStatus())
                return None

            if maestro_relajado.getStatus() in ["optimal", "feasible"]:
                valor_objetivo = maestro_relajado.getObjVal()
                print("Valor objetivo", valor_objetivo)
            else:
                print("⚠️ Modelo no óptimo ni factible.")
                return None

            # Guardo la mejor solucion hasta el momento
            mejor_sol = construir_mejor_solucion(maestro_relajado, self.columnas[k], valor_objetivo, self.cant_var_inicio)

            print("❤️ Cantidad de columnas antes de agregar:", len(self.columnas[k]))

            # Subproblema que busca una columna mejoradora
            nueva_col = self.resolver_subproblema(self.W, self.S, pi, self.UB, k, tiempo_restante_total)

            if nueva_col is None:
                print("No se generó una columna mejoradora o era repetida → Fin del bucle.")
                break

            print("Nueva columna: ", nueva_col)
            print("➕ Columna nueva encontrada, se agrega.")
            self.agregar_columna(maestro, nueva_col, x_vars, restr_card_k, restr_ordenes, restr_ub, restr_cov, k)
            print("💙 Cantidad de columnas después de agregar:", len(self.columnas[k]))

        return mejor_sol


    def Opt_PasillosFijos(self, umbral):
        k = len(self.pasillos_fijos)
        tiempo_restante_final = umbral - (time.time() - umbral)

        vacia = {"valor_objetivo": 0,"pasillos_seleccionados": [],"ordenes_seleccionadas": [],"restricciones": 0,"variables": 0,"variables_final": 0,"cota_dual": 0}
        
        if k not in self.columnas or not self.columnas[k]:
            print(f"❌ No hay columnas generadas para k = {k}")
            return vacia


        modelo, x_vars, _, _, _, _ = self.construir_modelo_maestro(k, tiempo_restante_final)

        # Desactivo para restricciones correctamente
        modelo.setPresolve(SCIP_PARAMSETTING.OFF)
        modelo.setHeuristics(SCIP_PARAMSETTING.OFF)
        modelo.disablePropagation() 
        modelo.optimize()
        if modelo:
            obj_val = modelo.getObjVal()
            pasillos_seleccionados, ordenes_seleccionadas = set(), set()
            for idx, x in enumerate(x_vars):
                if x.getLPSol() and x.getLPSol() > 1e-5:
                    pasillos_seleccionados.add(self.columnas[k][idx]['pasillo'])
                    for o, val in enumerate(self.columnas[k][idx]['ordenes']):
                        if val:
                            ordenes_seleccionadas.add(o)

            mejor_sol = {
                    "valor_objetivo": obj_val,
                    "pasillos_seleccionados": pasillos_seleccionados,
                    "ordenes_seleccionadas": ordenes_seleccionadas,
                    "restricciones": modelo.getNConss(),
                    "variables": self.cant_var_inicio,
                    "variables_final": modelo.getNVars(),
                    "cota_dual": modelo.getDualbound()
                }
        else:
            mejor_sol = vacia
    
        return mejor_sol

    def Opt_ExplorarCantidadPasillos(self, umbral):
        self.columnas = {}
        best_sol = None
        tiempo_ini = time.time()

        # Nueva forma de llamar a Rankear
        lista_k, lista_umbrales = self.Rankear(umbral)

        for k, tiempo_k in zip(lista_k, lista_umbrales):
            tiempo_restante = umbral - (time.time() - tiempo_ini)
            if tiempo_restante <= 0:
                print("⏳ Sin tiempo restante para seguir evaluando k.")
                break

            print(f"Evaluando k={k} con tiempo asignado {tiempo_k:.2f} segundos")

            sol = self.Opt_cantidadPasillosFija(k, tiempo_k)

            if sol is not None:
                print("✅ Se encontró solución")
            else:
                print("❌ No se encontró una solución dentro del tiempo límite.")

            if sol:
                sol_obj = sol["valor_objetivo"]
                best_obj = best_sol["valor_objetivo"] if best_sol else -float('inf')
                if sol_obj > best_obj:
                    best_sol = sol

        if best_sol:
            tiempo_usado = time.time() - tiempo_ini
            tiempo_final = max(1.0, umbral - tiempo_usado)
            print("✅ Resultado final realajado:", best_sol)
            print(f"⏳ Tiempo restante para Opt_PasillosFijos: {tiempo_final:.2f}s")

            self.pasillos_fijos = best_sol["pasillos_seleccionados"]
            resultado_final = self.Opt_PasillosFijos(tiempo_final)

            if resultado_final is None:
                print("⚠️ Opt_PasillosFijos no devolvió una solución válida.")
                return {
                    "valor_objetivo": 0,
                    "ordenes_seleccionadas": set(),
                    "pasillos_seleccionados": set(),
                    "variables": best_sol.get("variables", 0),
                    "variables_final": best_sol.get("variables_final", 0),
                    "cota_dual": best_sol.get("cota_dual", 0)
                }

            print("✅ Resultado final con pasillos fijos:", resultado_final)
            print("✅ Cantidad de variables:", resultado_final["variables"])
            print("✅ Cantidad de variables finales:", resultado_final["variables_final"])


            return resultado_final

    def Rankear(self, umbral):
        # Calcular la capacidad total por pasillo
        capacidades = [sum(self.S[a]) for a in range(self.A)]
        # Ordenar los pasillos por capacidad de mayor a menor
        sorted(range(self.A), key=lambda a: capacidades[a], reverse=True)
        
        # Priorizar los valores de k de 1 a A (cantidad de pasillos)
        # El orden ya es natural: más capacidad total acumulada para los primeros k
        lista_k = list(range(1, self.A + 1))

        # Tiempo asignado por k, equitativamente
        tiempo_por_k = umbral / len(lista_k)
        lista_umbrales = [tiempo_por_k] * len(lista_k)

        return lista_k, lista_umbrales


# OTRA ALTERNATIVA DE PASILLOS FIJOS, COMO EN PARTE 2

    # def Opt_PasillosFijos(self, umbral):
    #     if not self.pasillos_fijos:
    #         print("No hay pasillos fijos definidos para Opt_PasillosFijos")
    #         return None

    #     start = time.time()
    #     model = Model("Opt_PasillosFijos")
    #     model.setParam('display/verblevel', 0)  # silenciar logs
    #     model.setParam('limits/nodes', 5000)  # limitar nodos
    #     model.setParam("limits/time", umbral)

    #     x = {}
    #     for o in range(self.O):
    #         x[o] = model.addVar(vtype="B", name=f"x_{o}")

    #     model.setObjective(
    #         quicksum(self.W[o][i] * x[o] for o in range(self.O) for i in range(self.I)),
    #         "maximize"
    #     )

    #     total = quicksum(self.W[o][i] * x[o] for o in range(self.O) for i in range(self.I))
    #     model.addCons(total >= self.LB)
    #     model.addCons(total <= self.UB)

    #     for i in range(self.I):
    #         disponibilidad_total = sum(self.S[a][i] for a in self.pasillos_fijos)
    #         model.addCons(quicksum(self.W[o][i] * x[o] for o in range(self.O)) <= disponibilidad_total)

    #     cantidad_restricciones = model.getNConss()
    #     model.optimize()

    #     if model.getStatus() != "optimal":
    #         print(f"Modelo no óptimo: {model.getStatus()}")
    #         return None

    #     ordenes_seleccionadas = [o for o in range(self.O) if model.getVal(x[o]) > 0.5]
    #     valor_objetivo = model.getObjVal()

    #     return {
    #         "valor_objetivo": valor_objetivo,
    #         "ordenes_seleccionadas": ordenes_seleccionadas,
    #         "pasillos_seleccionados": self.pasillos_fijos,
    #         "restricciones": cantidad_restricciones,
    #         "variables": len(x),
    #         "variables_final": len(x),
    #         "cota_dual": model.getDualbound()
    #     }




