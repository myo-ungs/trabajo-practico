import time
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
        "valor_objetivo": obj_val / len(pasillos_seleccionados) if pasillos_seleccionados else 0,
        "pasillos_seleccionados": pasillos_seleccionados,
        "ordenes_seleccionadas": ordenes_seleccionadas,
        "variables": cant_var_inicio,
        "variables_final": modelo_relajado.getNVars(),
        "cota_dual": modelo_relajado.getDualbound()
    }

    return mejor_sol

class Columns:
    def __init__(self, W, S, LB, UB,
                 verbose=True,
                 max_cols_per_iter=12,
                 max_total_cols_factor=5,
                 rc_abs_tol=1e-6,
                 rc_min_improve_ratio=0.02,
                 penalty_pasillo_base=0.05):
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
        # Conjunto para deduplicar patrones: (k, pasillo, tuple(ordenes))
        self._patrones_vistos = set()
        # Config
        self.verbose = verbose
        self.max_cols_per_iter = max_cols_per_iter
        self.max_total_cols_factor = max_total_cols_factor  # multiplicador sobre A
        self.rc_abs_tol = rc_abs_tol
        self.rc_min_improve_ratio = rc_min_improve_ratio
        self.penalty_pasillo_base = penalty_pasillo_base
        # Uso acumulado de pasillos en columnas aceptadas (para penalización suave)
        self._uso_pasillo = [0]*self.A

    def es_columna_factible(self, columna):
        """Verifica factibilidad básica de una columna (capacidad por ítem y cota UB)."""
        if columna is None:
            return False
        a = columna['pasillo']
        ordenes = columna['ordenes']
        # Chequear capacidad
        for i in range(self.I):
            demanda_i = sum(self.W[o][i] for o in range(self.O) if ordenes[o])
            if demanda_i > self.S[a][i]:
                return False
        # Chequear unidades
        unidades = sum(sum(self.W[o][i] for i in range(self.I)) for o in range(self.O) if ordenes[o])
        if unidades > self.UB:
            return False
        return True

    def es_solucion_factible(self, columnas_indices, k):
        """Chequea factibilidad combinada de un conjunto de columnas (índices dentro de self.columnas[k])."""
        if not columnas_indices:
            return False
        # Cardinalidad
        if len(columnas_indices) > k:
            return False
        # Órdenes no repetidas
        usados_orden = [0]*self.O
        uso_items = [0]*self.I
        pasillos = []
        total_units = 0
        for idx in columnas_indices:
            col = self.columnas[k][idx]
            pasillos.append(col['pasillo'])
            for o,val in enumerate(col['ordenes']):
                if val:
                    if usados_orden[o]:
                        return False
                    usados_orden[o] = 1
                    total_units += sum(self.W[o])
                    for i in range(self.I):
                        uso_items[i] += self.W[o][i]
        # Capacidades agregadas
        cap_total = [sum(self.S[a][i] for a in set(pasillos)) for i in range(self.I)]
        if any(uso_items[i] > cap_total[i] for i in range(self.I)):
            return False
        if total_units > self.UB:
            return False
        return True

    def inicializar_columnas_para_k(self, k, umbral=None, max_variantes=3):
        tiempo_ini = time.time()

        if not hasattr(self, 'columnas'):
            self.columnas = {}

        self.columnas[k] = []
        unidades_o = [sum(self.W[o]) for o in range(self.O)]

        import random
        rng = random.Random(42)

        unidades_por_orden = unidades_o

        for a in range(self.A):  # Recorremos cada pasillo
            variantes_generadas = 0
            # Estrategias de orden de visita de órdenes
            estrategias = []
            estrategias.append(list(range(self.O)))  # orden natural
            estrategias.append(sorted(range(self.O), key=lambda o: unidades_por_orden[o], reverse=True))  # descendente unidades
            if self.O > 1:
                rand_list = list(range(self.O))
                rng.shuffle(rand_list)
                estrategias.append(rand_list)

            for ordenes_visit in estrategias:
                if variantes_generadas >= max_variantes:
                    break
                if umbral and (time.time() - tiempo_ini) > umbral:
                    print("⏱️ Tiempo agotado durante inicialización de columnas")
                    break
                cap_restante = list(self.S[a])
                sel = [0] * self.O
                total_unidades = 0
                for o in ordenes_visit:
                    if all(self.W[o][i] <= cap_restante[i] for i in range(self.I)) and \
                       (total_unidades + unidades_o[o] <= self.UB):
                        sel[o] = 1
                        total_unidades += unidades_o[o]
                        for i in range(self.I):
                            cap_restante[i] -= self.W[o][i]
                col = {
                    'pasillo': a,
                    'ordenes': sel,
                    'unidades': total_unidades
                }
                # Evitar duplicados exactos
                if col not in self.columnas[k]:
                    self.columnas[k].append(col)
                    variantes_generadas += 1
            # Garantizar al menos una columna (aunque sea vacía)
            if variantes_generadas == 0:
                self.columnas[k].append({'pasillo': a, 'ordenes': [0]*self.O, 'unidades': 0})

        print(f"✅ {len(self.columnas[k])} columnas iniciales creadas (una por pasillo) para k = {k}")

    def construir_modelo_maestro(self, k, umbral, estricta_cardinalidad=True):
        modelo = Model(f"RMP_k_{k}")
        modelo.setParam('display/verblevel', 0)
        x_vars = []
        # Pre-cálculo de uso de cada ítem por columna para poder agregar restricciones agregadas de capacidad.
        uso_item_col = []  # lista de dicts {i: uso}
        for col in self.columnas[k]:
            uso_i = {}
            for i in range(self.I):
                uso_i[i] = sum(self.W[o][i] for o in range(self.O) if col['ordenes'][o])
            uso_item_col.append(uso_i)
        
        # variable x_j binaria
        for idx, col in enumerate(self.columnas[k]):
            x = modelo.addVar(vtype="B", name=f"x_{col['pasillo']}_{idx}")
            x_vars.append(x)

        # Restricción de cardinalidad
        if estricta_cardinalidad:
            restr_card_k = modelo.addCons(quicksum(x_vars) == k, name="card_k")
        else:
            restr_card_k = modelo.addCons(quicksum(x_vars) <= k, name="card_k_leq")

        # Restricciones por orden
        restr_ordenes = {}
        for o in range(self.O):
            cons = modelo.addCons(
                quicksum(x_vars[j] * self.columnas[k][j]['ordenes'][o] for j in range(len(x_vars))) <= 1,
                name=f"orden_{o}"
            )
            restr_ordenes[o] = cons

        # Restricciones de unidades totales ≤ UB y ≥ LB
        expr_total_units = quicksum(x_vars[j] * self.columnas[k][j]['unidades'] for j in range(len(x_vars)))
        restr_ub = modelo.addCons(
            expr_total_units <= self.UB,
            name="restr_total_ub"
        )
        restr_lb = modelo.addCons(
            expr_total_units >= self.LB,
            name="restr_total_lb"
        )

        # NUEVO: Restricciones agregadas por ítem (relajación) para recuperar duales π_i.
        restr_items = {}
        for i in range(self.I):
            cons = modelo.addCons(
                quicksum(x_vars[j] * uso_item_col[j][i] for j in range(len(x_vars))) <= sum(self.S[a][i] for a in range(self.A)),
                name=f"item_cap_{i}"
            )
            restr_items[i] = cons

        # Nota: se elimina la restricción de unicidad de pasillo para permitir múltiples patrones del mismo pasillo
        # mientras representen subconjuntos de órdenes distintos.

        # Función objetivo: maximizar suma de unidades + epsilon * (#columnas seleccionadas)
        epsilon = 1e-3  # mayor para romper degeneración y diferenciar columnas
        expr_unidades = quicksum(
            x_vars[j] * sum(
                self.W[o][i]
                for o in range(self.O) if self.columnas[k][j]['ordenes'][o]
                for i in range(self.I)
            ) for j in range(len(x_vars))
        )
        modelo.setObjective(expr_unidades + epsilon * quicksum(x_vars), sense="maximize")

        return modelo, x_vars, restr_card_k, restr_ordenes, restr_ub, restr_lb, restr_items

    def resolver_subproblema(self, W, S, pi, UB, k, umbral=None, excluidos=None, ruido_obj=False):
        """Subproblema (pricing) usando duales estructurados o lista plana.

        Parámetros extra:
        - excluidos: conjunto de pasillos a forzar en 0 (para diversificar en una misma iteración).
        - ruido_obj: si True, se agrega pequeño ruido aleatorio a las unidades para romper empates.
        """
        O = len(W)
        I = len(W[0])
        A = len(S)
        units_o = [sum(W[o]) for o in range(O)]

        # Duales
        if isinstance(pi, dict):
            pi_card_k = pi['gamma']
            pi_ordenes = pi['alpha']
            pi_ub = pi['lamb']
            pi_lb = pi.get('mu', 0.0)
            pi_items = pi['pi_items']
            pi_pasillos = pi['beta']
        else:
            idx = 0
            pi_card_k = pi[idx]; idx += 1
            pi_ordenes = pi[idx: idx + O]; idx += O
            pi_ub = pi[idx]; idx += 1
            pi_lb = pi[idx]; idx += 1
            pi_items = pi[idx: idx + I]; idx += I
            # En algunos modelos (p.ej. modelo_3) ya no existen restricciones por pasillo,
            # por lo que la lista "pi" termina aquí. Entonces rellenamos con ceros.
            if len(pi) - idx >= A:
                pi_pasillos = pi[idx: idx + A]
            else:
                pi_pasillos = [0.0] * A

        modelo = Model("Pricing")
        modelo.setParam('display/verblevel', 0)
        # Opcional: desactivar heurísticas para velocidad/determinismo
        # modelo.setPresolve(SCIP_PARAMSETTING.FAST)
        y = {a: modelo.addVar(vtype="B", name=f"y_{a}") for a in range(A)}
        z = {o: modelo.addVar(vtype="B", name=f"z_{o}") for o in range(O)}

        modelo.addCons(quicksum(y[a] for a in range(A)) == 1, name="unico_pasillo")
        # Excluir pasillos ya usados en esta iteración de búsqueda múltiple
        if excluidos:
            for a in excluidos:
                if 0 <= a < A:
                    modelo.addCons(y[a] == 0, name=f"excluir_{a}")
        for i in range(I):
            modelo.addCons(
                quicksum(W[o][i] * z[o] for o in range(O)) <= quicksum(S[a][i] * y[a] for a in range(A)),
                name=f"capacidad_item_{i}"
            )
        # Construcción explícita de la expresión de costo reducido (signos estándar)
        # Ruido para romper empates (muy pequeño, no altera optimalidad global pero diversifica columnas)
        if ruido_obj:
            import random
            rnd = random.random
            ruido = [1.0 + 0.01 * (rnd()-0.5) for _ in range(O)]  # +/-0.5% aprox
            unidades_coef = [units_o[o] * ruido[o] for o in range(O)]
        else:
            unidades_coef = units_o
        c_units_expr = quicksum(unidades_coef[o] * z[o] for o in range(O))
        uso_items_exprs = {i: quicksum(W[o][i] * z[o] for o in range(O)) for i in range(I)}
        expr = c_units_expr
        expr -= pi_card_k  # gamma
        expr -= pi_ub * c_units_expr  # lambda * units
        expr += pi_lb * c_units_expr  # mu * units (LB)
        expr -= quicksum(pi_ordenes[o] * z[o] for o in range(O))
        expr -= quicksum(pi_items[i] * uso_items_exprs[i] for i in range(I))
        expr -= quicksum(pi_pasillos[a] * y[a] for a in range(A))
        # Penalización suave por reutilizar pasillos muy explotados
        if hasattr(self, '_uso_pasillo'):
            expr -= quicksum(self.penalty_pasillo_base * (1 + 0.1*self._uso_pasillo[a]) * y[a] for a in range(A))
        modelo.setObjective(expr, sense="maximize")

        modelo.optimize()
        if modelo.getStatus() != 'optimal':
            print("⚠️ Subproblema no óptimo. Estado:", modelo.getStatus())
            return None
        reduced_cost = modelo.getObjVal()
        if reduced_cost > 1e-6:
            try:
                pas_a = next(a for a in range(A) if modelo.getVal(y[a]) > 0.5)
                ordenes_sel = [o for o in range(O) if modelo.getVal(z[o]) > 0.5]
                unidades_sel = sum(units_o[o] for o in ordenes_sel)
                uso_items_det = [sum(W[o][i] for o in ordenes_sel) for i in range(I)]
                comp = {
                    'units': unidades_sel,
                    'gamma': pi_card_k,
                    'lambda*units': pi_ub * unidades_sel,
                    'mu*units': pi_lb * unidades_sel,
                    'sum_alpha': sum(pi_ordenes[o] for o in ordenes_sel),
                    'sum_pi_items': sum(pi_items[i]*uso_items_det[i] for i in range(I)),
                    'beta': pi_pasillos[pas_a] if pi_pasillos else 0.0
                }
                print("RC componentes:", comp)
            except Exception:
                pass
        print(f"Costo reducido subproblema: {reduced_cost:.6f}")
        if reduced_cost <= 1e-6:
            return None
        pasillo_seleccionado = next(a for a in range(A) if modelo.getVal(y[a]) > 0.5)
        ordenes = [int(modelo.getVal(z[o]) + 0.5) for o in range(O)]
        unidades = sum(units_o[o] for o in range(O) if ordenes[o])
        columna = {'pasillo': pasillo_seleccionado, 'ordenes': ordenes, 'unidades': unidades}
        clave = (k, pasillo_seleccionado, tuple(ordenes))
        if clave in self._patrones_vistos:
            print("⚠️ Columna repetida generada (descartada).")
            return None
        self._patrones_vistos.add(clave)
        self.columnas.setdefault(k, []).append(columna)
        return columna


    def agregar_columna(self, maestro, nueva_col, x_vars, restr_card_k, restr_ordenes, restr_ub, restr_lb, k, restr_items=None):
        idx = len(self.columnas[k]) - 1  # índice correcto de la nueva columna (ya agregada)
        x = maestro.addVar(vtype="B", name=f"x_{nueva_col['pasillo']}_{idx}", obj=nueva_col['unidades'])
        x_vars.append(x)

        # Actualizar uso de pasillo (para penalización futura)
        if hasattr(self, '_uso_pasillo'):
            self._uso_pasillo[nueva_col['pasillo']] += 1

        # Agregar coeficiente en restricción cardinalidad
        maestro.addConsCoeff(restr_card_k, x, 1)

        # Agregar coeficientes en restricción de órdenes
        for o in range(self.O):
            maestro.addConsCoeff(restr_ordenes[o], x, nueva_col['ordenes'][o])

        # Agregar coeficiente en restricciones de unidades (UB y LB)
        maestro.addConsCoeff(restr_ub, x, nueva_col['unidades'])
        maestro.addConsCoeff(restr_lb, x, nueva_col['unidades'])

        # Agregar coeficientes en restricciones de ítems si existen
        if restr_items is not None:
            for i, cons in restr_items.items():
                uso_i = sum(self.W[o][i] for o in range(self.O) if nueva_col['ordenes'][o])
                maestro.addConsCoeff(cons, x, uso_i)

    def Opt_cantidadPasillosFija(self, k, umbral):
        tiempo_ini = time.time()
        
        # Reservar 30% del tiempo para inicializar columnas iniciales para k
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

            print(f"⌛ Iteración con {len(self.columnas.get(k, []))} columnas")

            # Construcción del modelo maestro con las columnas actuales
            maestro, x_vars, restr_card_k, restr_ordenes, restr_ub, restr_lb, restr_items = self.construir_modelo_maestro(k, tiempo_restante_total, estricta_cardinalidad=False)

            # Crear una copia para relajación y obtención de duales
            maestro_relajado = Model(sourceModel=maestro)

            # Desactivar ciertas heurísticas y preprocesos para obtener duales confiables
            maestro_relajado.setPresolve(SCIP_PARAMSETTING.OFF)
            maestro_relajado.setHeuristics(SCIP_PARAMSETTING.OFF)
            maestro_relajado.disablePropagation()

            # Relajar modelo maestro (variables binarias a continuas)
            maestro_relajado.relax()
            maestro_relajado.optimize()

            if primera_iteracion:
                self.cant_var_inicio = maestro_relajado.getNVars()
                primera_iteracion = False

            # Verificar que la solución es óptima para obtener duales
            if maestro_relajado.getStatus() != "optimal":
                print(f"⚠️ No se encontró solución óptima. Estado: {maestro_relajado.getStatus()}")
                break

            # Obtener valores duales según el orden de agregación de restricciones:
            # 0: cardinalidad
            # 1..O: ordenes
            # O+1: UB
            # O+2: LB
            # O+3 .. O+2+I: items
            # resto: (no hay pasillos ahora porque se eliminó unicidad) → beta se mantiene para compatibilidad (cero)
            conss = maestro_relajado.getConss()
            gamma = maestro_relajado.getDualsolLinear(conss[0]) if conss else 0.0
            alpha = [maestro_relajado.getDualsolLinear(conss[1+o]) for o in range(self.O)] if len(conss) >= 1+self.O else [0.0]*self.O
            lamb = maestro_relajado.getDualsolLinear(conss[1+self.O]) if len(conss) > 1+self.O else 0.0
            mu = maestro_relajado.getDualsolLinear(conss[2+self.O]) if len(conss) > 2+self.O else 0.0
            pi_items = [maestro_relajado.getDualsolLinear(conss[3+self.O + i]) for i in range(self.I)] if len(conss) > 3+self.O else [0.0]*self.I
            beta = [0.0]*self.A  # ya no hay restricciones por pasillo
            # Heurística de inversión de signo si la mayoría son negativos (esperamos no-negativos)
            def flip_block(vs):
                if not vs: return vs, False
                neg = sum(1 for v in vs if v < -1e-9)
                pos = sum(1 for v in vs if v > 1e-9)
                if neg > pos and neg >= 0.7*len(vs):
                    return [-v for v in vs], True
                return vs, False
            alpha, fa = flip_block(alpha)
            pi_items, fi = flip_block(pi_items)
            beta, fb = flip_block(beta)
            fg = False; fl = False
            if gamma < -1e-9: gamma, fg = -gamma, True
            if lamb < -1e-9: lamb, fl = -lamb, True
            duales = {'gamma': gamma, 'alpha': alpha, 'lamb': lamb, 'mu': mu, 'pi_items': pi_items, 'beta': beta}
            print(f"Dual(g={gamma:.3g},l={lamb:.3g},mu={mu:.3g}) a_avg={sum(alpha)/max(1,len(alpha)):.3g} flips g={fg} l={fl} a={fa} i={fi} b={fb}")

            # Guardar valor objetivo actual
            valor_objetivo = maestro_relajado.getObjVal()
            # print("Valor objetivo:", valor_objetivo)

            # Construir la mejor solución factible a partir del modelo relajado
            mejor_sol = construir_mejor_solucion(maestro_relajado, self.columnas.get(k, []), valor_objetivo, self.cant_var_inicio)

            # print("❤️ Cantidad de columnas antes de agregar:", len(self.columnas.get(k, [])))

            # Búsqueda de múltiples columnas mejoradoras en una misma iteración
            mejoras_en_iter = 0
            intentos = 0
            max_intentos = self.max_cols_per_iter  # configurable
            pasillos_excluidos_iter = set()
            while intentos < max_intentos:
                intentos += 1
                # Activar ruido a partir del segundo intento de la misma iteración
                usar_ruido = intentos > 1
                nueva_col = self.resolver_subproblema(self.W, self.S, duales, self.UB, k, tiempo_restante_total,
                                                     excluidos=pasillos_excluidos_iter, ruido_obj=usar_ruido)
                if nueva_col is None:
                    if mejoras_en_iter == 0:
                        print("No se generó una columna mejoradora o era repetida → Fin del bucle.")
                        intentos = max_intentos  # salir bucle externo
                    break
                print("Nueva columna encontrada:", nueva_col)
                print("➕ Agregando columna nueva al modelo maestro.")
                self.agregar_columna(maestro, nueva_col, x_vars, restr_card_k, restr_ordenes, restr_ub, restr_lb, k, restr_items=restr_items)
                mejoras_en_iter += 1
                pasillos_excluidos_iter.add(nueva_col['pasillo'])  # excluir este pasillo para próxima búsqueda
                # Criterio adicional de parada: si demasiadas columnas o tiempo bajo
                if len(self.columnas.get(k, [])) > self.max_total_cols_factor * self.A:
                    print("🛑 Límite global de columnas alcanzado para k, deteniendo iteraciones.")
                    intentos = max_intentos
                    break
                # Excluir patrón exacto en próximas llamadas: ya está en _patrones_vistos
                # Para intentar diversificar, podríamos agregar penalización, aquí sólo seguimos buscando.
            if mejoras_en_iter == 0:
                break

            # print("💙 Cantidad de columnas después de agregar:", len(self.columnas.get(k, [])))

        return mejor_sol


    def Opt_PasillosFijos(self, umbral):
        tiempo_ini = time.time()
        k = len(self.pasillos_fijos)

        # Tiempo restante para la fase final
        tiempo_restante_final = umbral - (time.time() - tiempo_ini)
        if tiempo_restante_final <= 0:
            print("⏳ No queda tiempo para Opt_PasillosFijos")
            return {
                "valor_objetivo": 0,
                "pasillos_seleccionados": set(),
                "ordenes_seleccionadas": set(),
                "restricciones": 0,
                "variables": 0,
                "variables_final": 0,
                "cota_dual": 0
            }

        # Verificación de existencia de columnas para este k
        if k not in self.columnas or not self.columnas[k]:
            print(f"❌ No hay columnas generadas para k = {k}")
            return {
                "valor_objetivo": 0,
                "pasillos_seleccionados": set(),
                "ordenes_seleccionadas": set(),
                "restricciones": 0,
                "variables": 0,
                "variables_final": 0,
                "cota_dual": 0
            }

        # Construir modelo maestro con cardinalidad estricta
        maestro, x_vars, *_ = self.construir_modelo_maestro(k, tiempo_restante_final, estricta_cardinalidad=True)

        maestro.setPresolve(SCIP_PARAMSETTING.OFF)
        maestro.setHeuristics(SCIP_PARAMSETTING.OFF)
        maestro.disablePropagation()
        maestro.optimize()
        status = maestro.getStatus()

        if status in ["optimal", "feasible"] and maestro.getNSols() > 0:
            obj_val = maestro.getObjVal()
            pasillos_seleccionados = set()
            ordenes_seleccionadas = set()
            for idx, x in enumerate(x_vars):
                val = x.getLPSol()
                if val and val > 1e-5:
                    pasillos_seleccionados.add(self.columnas[k][idx]['pasillo'])
                    for o, seleccionado in enumerate(self.columnas[k][idx]['ordenes']):
                        if seleccionado:
                            ordenes_seleccionadas.add(o)
            mejor_sol = {
                "valor_objetivo": obj_val / len(pasillos_seleccionados) if pasillos_seleccionados else 0,
                "pasillos_seleccionados": pasillos_seleccionados,
                "ordenes_seleccionadas": ordenes_seleccionadas,
                "restricciones": maestro.getNConss(),
                "variables": self.cant_var_inicio if hasattr(self, "cant_var_inicio") else 0,
                "variables_final": maestro.getNVars(),
                "cota_dual": maestro.getDualbound()
            }
        else:
            print(f"⚠️ Modelo no óptimo ni factible. Estado: {status}")
            mejor_sol = {
                "valor_objetivo": 0,
                "pasillos_seleccionados": set(),
                "ordenes_seleccionadas": set(),
                "restricciones": maestro.getNConss() if maestro else 0,
                "variables": self.cant_var_inicio if hasattr(self, "cant_var_inicio") else 0,
                "variables_final": maestro.getNVars() if maestro else 0,
                "cota_dual": maestro.getDualbound() if maestro else 0
            }
        return mejor_sol


    def Opt_ExplorarCantidadPasillos(self, umbral):
        self.columnas = {}
        best_sol = None
        tiempo_ini = time.time()

        # Obtener lista de valores k y tiempos asignados a cada uno según Rankear()
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
                sol_obj = sol.get("valor_objetivo", -float('inf'))
                best_obj = best_sol.get("valor_objetivo", -float('inf')) if best_sol else -float('inf')
                if sol_obj > best_obj:
                    best_sol = sol

        if best_sol:
            tiempo_usado = time.time() - tiempo_ini
            tiempo_final = max(1.0, umbral - tiempo_usado)
            print("✅ Resultado final relajado:", best_sol)
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

            resultado_final["tiempo_total"] = round(time.time() - tiempo_ini, 2)
            return resultado_final
        
        else:
            print("⚠️ No se encontró ninguna solución durante la exploración.")
            return {
                "valor_objetivo": 0,
                "ordenes_seleccionadas": set(),
                "pasillos_seleccionados": set(),
                "variables": 0,
                "variables_final": 0,
                "cota_dual": 0
            }


    def Rankear(self, umbral):
        # Calcular la capacidad total por pasillo
        capacidades = [sum(self.S[a]) for a in range(self.A)]
        # Ordenar los pasillos por capacidad de mayor a menor
        pasillos_ordenados = sorted(range(self.A), key=lambda a: capacidades[a], reverse=True)
        lista_k = pasillos_ordenados

        # Tiempo asignado por k, equitativamente
        tiempo_por_k = umbral 
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

