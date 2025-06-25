import time
import random
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatusOptimal, PULP_CBC_CMD, LpBinary, LpStatus

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

    def inicializar_columnas_para_k(self, k): # reduzco las iniciales para probar
        if k not in self.columnas:
            columnas_iniciales = []
            unidades_o = [sum(self.W[o]) for o in range(self.O)]
            for o in range(self.O):
                for a in range(self.A):
                    cap = self.S[a][:]
                    if all(self.W[o][i] <= cap[i] for i in range(self.I)) and unidades_o[o] <= self.UB:
                        sel = [0] * self.O
                        sel[o] = 1
                        columnas_iniciales.append({'pasillo': a, 'ordenes': sel, 'unidades': unidades_o[o]})
                        break  # solo una columna con esta orden, en el primer pasillo que quepa
            self.columnas[k] = columnas_iniciales

    def _crear_columna_inicial(self, a):
        unidades_o = [sum(self.W[o]) for o in range(self.O)]
        ordenes_ordenadas = sorted(range(self.O), key=lambda o: -unidades_o[o])
        cap = self.S[a][:]
        sel = [0] * self.O
        total = 0
        for o in ordenes_ordenadas:
            if unidades_o[o] + total > self.UB:
                continue
            if all(self.W[o][i] <= cap[i] for i in range(self.I)):
                sel[o] = 1
                total += unidades_o[o]
                for i in range(self.I):
                    cap[i] -= self.W[o][i]
            if total >= self.UB:
                break
        return {'pasillo': a, 'ordenes': sel, 'unidades': total}

    def construir_modelo(self, k):
        self.inicializar_columnas_para_k(k)
        modelo = LpProblem(f"RMP_k_{k}", LpMaximize)
        x_vars = [LpVariable(f"x_{self.columnas[k][idx]['pasillo']}_{idx}", cat=LpBinary) for idx in range(len(self.columnas[k]))]

        modelo += lpSum(x_vars) == k, "card_k"
        for o in range(self.O):
            modelo += lpSum(x_vars[j]*self.columnas[k][j]['ordenes'][o] for j in range(len(x_vars))) <= 1, f"orden_{o}"
        for i in range(self.I):
            modelo += lpSum(
                x_vars[j]*sum(self.W[o][i]*self.columnas[k][j]['ordenes'][o] for o in range(self.O))
                for j in range(len(x_vars))
            ) <= lpSum(
                x_vars[j]*self.S[self.columnas[k][j]['pasillo']][i]
                for j in range(len(x_vars))
            ), f"cov_{i}"
        modelo += lpSum(
            x_vars[j]*sum(self.W[o][i] for o in range(self.O) for i in range(self.I) if self.columnas[k][j]['ordenes'][o])
            for j in range(len(x_vars))
        )
        return modelo, x_vars

    def agregar_columna(self, k, nueva_col):
        if k not in self.columnas:
            print(f"Error: Columnas no inicializadas para k={k}. Llama primero a inicializar_columnas_para_k(k).")
            return False
        for col in self.columnas[k]:
            if (col['pasillo'] == nueva_col['pasillo'] and tuple(col['ordenes']) == tuple(nueva_col['ordenes'])):
                print("Columna ya existe, no se agrega.")
                return False
        self.columnas[k].append({
            'pasillo': nueva_col['pasillo'],
            'ordenes': nueva_col['ordenes'][:],
            'unidades': nueva_col['unidades']
        })
        ordenes_idx = [i for i, val in enumerate(nueva_col['ordenes']) if val]
        print(f"[+] Nueva columna agregada para k={k}: pasillo={nueva_col['pasillo']} ords_idx={ordenes_idx}")
        return True

    def resolver_modelo(self, modelo, time_limit):
        solver = PULP_CBC_CMD(timeLimit=time_limit, msg=0)
        resultado = modelo.solve(solver)
        if resultado != LpStatusOptimal:
            print(f"Resolver modelo: No se encontró solución óptima (status {LpStatus[resultado]}).")
        return modelo if resultado == LpStatusOptimal else None

    def obtener_valores_duales(self, modelo):
        duales = []
        for o in range(self.O):
            cons = modelo.constraints.get(f"orden_{o}")
            duales.append(cons.pi if cons else 0.0)
        return duales


    def buscar_columna_mejoradora(self, k, duales):
        best_val = -float('inf')
        best_col = None
        unidades_o = [sum(self.W[o]) for o in range(self.O)]

        for a in range(self.A):
            cap = self.S[a][:]
            ordenes = [0] * self.O
            total = 0

            # Introducimos ruido aleatorio pequeño para romper empates y variar orden
            ruido = [random.uniform(0, 0.01) for _ in range(self.O)]
            ordenes_ordenadas = sorted(
                range(self.O),
                key=lambda o: (unidades_o[o] - duales[o] + ruido[o]),
                reverse=True
            )

            for o in ordenes_ordenadas:
                rc = unidades_o[o] - duales[o]
                if rc <= 1e-3:
                    continue
                if total + unidades_o[o] > self.UB:
                    continue
                if all(self.W[o][i] <= cap[i] for i in range(self.I)):
                    ordenes[o] = 1
                    total += unidades_o[o]
                    for i in range(self.I):
                        cap[i] -= self.W[o][i]

            valor_reducido_total = sum((unidades_o[o] - duales[o]) * ordenes[o] for o in range(self.O))

            if valor_reducido_total > best_val and any(ordenes):
                best_val = valor_reducido_total
                best_col = {'pasillo': a, 'ordenes': ordenes.copy(), 'unidades': total}
                print(f"✔️ Columna candidata mejoradora en pasillo {a} con valor reducido {valor_reducido_total}")


        return best_col if best_val > 1e-3 else None

    def Opt_cantidadPasillosFija(self, k, umbral):
        
        tiempo_ini = time.time()
        self.inicializar_columnas_para_k(k)
        print(f"Columnas iniciales para k={k}: {len(self.columnas[k])}")
        self.columnas_iniciales = len(self.columnas[k])

        while time.time() - tiempo_ini < umbral:
            print(f"⌛ Iteración con {len(self.columnas[k])} columnas")
            print(f"Columnas actuales para k={k}: {len(self.columnas[k])}")
            modelo, x_vars = self.construir_modelo(k)
            modelo_resuelto = self.resolver_modelo(modelo, umbral)
            if not modelo_resuelto:
                break
            duales = self.obtener_valores_duales(modelo)
            nueva = self.buscar_columna_mejoradora(k, duales)
            if not nueva or not self.agregar_columna(k, nueva):
                break
            if time.time() - tiempo_ini > umbral:
                print("⏰ Umbral de tiempo alcanzado, saliendo del bucle")
                break


        modelo, x_vars = self.construir_modelo(k)
        modelo_resuelto = self.resolver_modelo(modelo, umbral)
        if not modelo_resuelto:
            print("No se pudo resolver el modelo final para k =", k)
            return None
        
        self.columnas_finales = len(self.columnas[k])
        self.ultima_cota_dual = modelo.objective.value()


        pasillos_seleccionados, ordenes_seleccionadas = set(), set()
        for idx, x in enumerate(x_vars):
            if x.varValue and x.varValue > 1e-5:
                pasillos_seleccionados.add(self.columnas[k][idx]['pasillo'])
                for o, val in enumerate(self.columnas[k][idx]['ordenes']):
                    if val:
                        ordenes_seleccionadas.add(o)

        return {
            "valor_objetivo": int(modelo.objective.value()),
            "pasillos_seleccionados": pasillos_seleccionados,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "variables": self.columnas_iniciales,
            "variables_final": self.columnas_finales,
            "cota_dual": self.ultima_cota_dual
        }

    def Opt_PasillosFijos(self, umbral):
        if not self.pasillos_fijos:
            print("No hay pasillos fijos definidos para Opt_PasillosFijos")
            return None

        start = time.time()
        modelo = LpProblem("Opt_PasillosFijos", LpMaximize)
        x = LpVariable.dicts("x", range(self.O), cat=LpBinary)

        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.O) for i in range(self.I)), "TotalRecolectado"
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.O) for i in range(self.I)) >= self.LB
        modelo += lpSum(self.W[o][i] * x[o] for o in range(self.O) for i in range(self.I)) <= self.UB

        for i in range(self.I):
            disponibilidad_total = sum(self.S[a][i] for a in self.pasillos_fijos)
            modelo += lpSum(self.W[o][i] * x[o] for o in range(self.O)) <= disponibilidad_total

        tiempo_restante = umbral - (time.time() - start)
        if tiempo_restante <= 0:
            print("Tiempo agotado antes de resolver el modelo en Opt_PasillosFijos")
        solver = PULP_CBC_CMD(msg=0)
        modelo.solve(solver)

        if LpStatus[modelo.status] != "Optimal":
            print(f"Modelo no óptimo: {LpStatus[modelo.status]}")
            return None

        ordenes_seleccionadas = [o for o in range(self.O) if x[o].varValue == 1]
        valor_objetivo = int(modelo.objective.value())
        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": self.pasillos_fijos,
            "restricciones": len(modelo.constraints),
            "variables": len(x),
            "variables_final": len(x),
            "cota_dual": None
        }

    def Opt_ExplorarCantidadPasillos(self, umbral):
        self.columnas = {}
        best_sol, best_val = None, -float('inf')
        tiempo_ini = time.time()
        lista_k = self.Rankear()  # [(k1, potencial1), (k2, potencial2), ...]
        total_potencial = sum(pot for _, pot in lista_k)

        for k, potencial in lista_k:
            tiempo_restante = umbral - (time.time() - tiempo_ini)
            if tiempo_restante <= 0:
                break
            tiempo_k = max(0.1, umbral * (potencial / total_potencial))
            tiempo_k = min(tiempo_k, tiempo_restante)

            print(f"Evaluando k={k} con tiempo asignado {tiempo_k:.2f} segundos")
            sol = self.Opt_cantidadPasillosFija(k, tiempo_k)
            if sol is not None:
                print("Se encontró solución")
            else:
                print("No se encontró una solución dentro del tiempo límite.")

            if sol:
                n_ordenes = len(sol["ordenes_seleccionadas"])
                n_pasillos = len(sol["pasillos_seleccionados"])
                best_n_ordenes = len(best_sol["ordenes_seleccionadas"]) if best_sol else -1
                best_n_pasillos = len(best_sol["pasillos_seleccionados"]) if best_sol else float('inf')

                if (n_ordenes > best_n_ordenes) or (n_ordenes == best_n_ordenes and n_pasillos < best_n_pasillos):
                    best_sol = sol

        if best_sol:
            tiempo_final = max(0.1, umbral - (time.time() - tiempo_ini))
            self.pasillos_fijos = best_sol["pasillos_seleccionados"]
            resultado_final = self.Opt_PasillosFijos(tiempo_final)

            # ⚠️ AGREGADO: controlar si resultado_final es None
            if resultado_final is None:
                print("⚠️ Opt_PasillosFijos no devolvió una solución válida.")
                return {
                    "valor_objetivo": 0,
                    "ordenes_seleccionadas": set(),
                    "pasillos_seleccionados": set(),
                    "variables": best_sol.get("variables", 0),
                    "variables_final": best_sol.get("variables_final", 0),
                    "cota_dual": best_sol.get("cota_dual", 0),
                    "instancia": self.nombre_input if hasattr(self, "nombre_input") else ""
                }

            resultado_final["variables"] = best_sol.get("variables", None)
            resultado_final["variables_final"] = best_sol.get("variables_final", None)
            resultado_final["cota_dual"] = best_sol.get("cota_dual", None)

            return resultado_final

        # Si best_sol fue None (nunca se encontró una solución aceptable)
        print("⚠️ No se encontró ninguna solución válida para ningún valor de k")
        return {
            "valor_objetivo": 0,
            "ordenes_seleccionadas": set(),
            "pasillos_seleccionados": set(),
            "variables": 0,
            "variables_final": 0,
            "cota_dual": 0,
            "instancia": self.nombre_input if hasattr(self, "nombre_input") else ""
        }



    def Rankear(self):
        capacidades = [sum(self.S[a]) for a in range(self.A)]
        pasillos_ordenados = sorted(range(self.A), key=lambda a: capacidades[a], reverse=True)

        lista_k = []
        for k in range(1, self.A + 1):
            suma_capacidad_k = sum(capacidades[a] for a in pasillos_ordenados[:k])
            lista_k.append((k, suma_capacidad_k))

        lista_k.sort(key=lambda x: x[1], reverse=True)
        return lista_k  # Devuelve lista de tuplas (k, potencial)
