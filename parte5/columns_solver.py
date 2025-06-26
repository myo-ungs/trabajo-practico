import time
import random
from pyscipopt import Model, quicksum, SCIP_PARAMSETTING

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


    def inicializar_columnas_para_k(self, k, umbral):
        tiempo_ini = time.time()
        if k not in self.columnas:
            columnas_iniciales = []
            unidades_o = [sum(self.W[o]) for o in range(self.O)]

            for o in range(self.O):
                print("coluumna", (time.time() - tiempo_ini), umbral)
                
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

    def construir_modelo(self, k, umbral):
        self.inicializar_columnas_para_k(k, umbral)
        modelo = Model(f"RMP_k_{k}")
        modelo.setParam('display/verblevel', 0)  # silenciar logs
        x_vars = []
        for idx, col in enumerate(self.columnas[k]):
            x = modelo.addVar(vtype="B", name=f"x_{col['pasillo']}_{idx}")
            x_vars.append(x)

        modelo.addCons(quicksum(x_vars) == k, name="card_k")
        restricciones_duales = {}  # Diccionario separado

        for o in range(self.O):
            cons = modelo.addCons(
                quicksum(x_vars[j]*self.columnas[k][j]['ordenes'][o] for j in range(len(x_vars))) <= 1,
                name=f"orden_{o}"
            )
            restricciones_duales[o] = cons

        for i in range(self.I):
            lhs = quicksum(
                x_vars[j]*sum(self.W[o][i]*self.columnas[k][j]['ordenes'][o] for o in range(self.O))
                for j in range(len(x_vars))
            )
            rhs = quicksum(
                x_vars[j]*self.S[self.columnas[k][j]['pasillo']][i]
                for j in range(len(x_vars))
            )
            modelo.addCons(lhs <= rhs, name=f"cov_{i}")

        modelo.setObjective(
            quicksum(x_vars[j]*sum(self.W[o][i] for o in range(self.O) for i in range(self.I) if self.columnas[k][j]['ordenes'][o]) for j in range(len(x_vars))),
            sense="maximize"
        )
        return modelo, x_vars,restricciones_duales

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
        modelo.setParam("limits/time", time_limit)
        modelo.optimize()
        if modelo.getStatus() != 'optimal':
            print(f"Resolver modelo: No se encontró solución óptima (status {modelo.getStatus()}).")
            return None
        return modelo

    def obtener_valores_duales(self, modelo, restricciones_duales):
        duales = []
        for o in range(self.O):
            try:
                cons = restricciones_duales.get(o)
                tcons = modelo.getTransformedCons(cons)
                dual = modelo.getDualsolLinear(tcons)
            except Exception as e:
                dual = 0.0
            duales.append(dual)
        return duales


    def buscar_columna_mejoradora(self, k, duales):
        best_val = -float('inf')
        best_col = None
        unidades_o = [sum(self.W[o]) for o in range(self.O)]

        for a in range(self.A):
            cap = self.S[a][:]
            ordenes = [0] * self.O
            total = 0

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
        self.inicializar_columnas_para_k(k, umbral)
        print(f"Columnas iniciales para k={k}: {len(self.columnas[k])}")
        self.columnas_iniciales = len(self.columnas[k])

        while True:
            tiempo_actual = time.time()
            tiempo_transcurrido = tiempo_actual - tiempo_ini
            tiempo_restante = umbral - tiempo_transcurrido

            if tiempo_restante <= 1:
                print("⏰ Tiempo insuficiente para continuar (restante <= 1s)")
                break

            print(f"⌛ Iteración con {len(self.columnas[k])} columnas")

            modelo, x_vars, restricciones_duales = self.construir_modelo(k, umbral)
            modelo_resuelto = self.resolver_modelo(modelo, time_limit=tiempo_restante)

            if not modelo_resuelto:
                print("No se pudo resolver el modelo (o no óptimo)")
                break

            duales = self.obtener_valores_duales(modelo, restricciones_duales)

            nueva = self.buscar_columna_mejoradora(k, duales)
            if not nueva or not self.agregar_columna(k, nueva):
                print("No se encontró columna mejoradora o no se pudo agregar")
                break

        # Último intento de resolver modelo final con lo que se tiene
        tiempo_restante_final = umbral - (time.time() - tiempo_ini)
        if tiempo_restante_final <= 1:
            print("⏰ Sin tiempo suficiente para resolver el modelo final")
            return None

        modelo, x_vars, restricciones_duales = self.construir_modelo(k, umbral)
        modelo_resuelto = self.resolver_modelo(modelo, time_limit=tiempo_restante_final)

        if not modelo_resuelto:
            print("No se pudo resolver el modelo final para k =", k)
            return None

        self.columnas_finales = len(self.columnas[k])
        self.ultima_cota_dual = modelo.getObjVal()

        pasillos_seleccionados, ordenes_seleccionadas = set(), set()
        for idx, x in enumerate(x_vars):
            if x.getLPSol() and x.getLPSol() > 1e-5:
                pasillos_seleccionados.add(self.columnas[k][idx]['pasillo'])
                for o, val in enumerate(self.columnas[k][idx]['ordenes']):
                    if val:
                        ordenes_seleccionadas.add(o)

        return {
            "valor_objetivo": int(self.ultima_cota_dual),
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
        model = Model("Opt_PasillosFijos")
        model.setParam('display/verblevel', 0)  # silenciar logs
        model.setParam('limits/nodes', 5000)  # limitar nodos
        model.setParam("limits/time", umbral)

        x = {}
        for o in range(self.O):
            x[o] = model.addVar(vtype="B", name=f"x_{o}")

        model.setObjective(
            quicksum(self.W[o][i] * x[o] for o in range(self.O) for i in range(self.I)),
            "maximize"
        )

        total = quicksum(self.W[o][i] * x[o] for o in range(self.O) for i in range(self.I))
        model.addCons(total >= self.LB)
        model.addCons(total <= self.UB)

        for i in range(self.I):
            disponibilidad_total = sum(self.S[a][i] for a in self.pasillos_fijos)
            model.addCons(quicksum(self.W[o][i] * x[o] for o in range(self.O)) <= disponibilidad_total)

        cantidad_restricciones = model.getNConss()
        model.optimize()

        if model.getStatus() != "optimal":
            print(f"Modelo no óptimo: {model.getStatus()}")
            return None

        ordenes_seleccionadas = [o for o in range(self.O) if model.getVal(x[o]) > 0.5]
        valor_objetivo = int(model.getObjVal())

        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": self.pasillos_fijos,
            "restricciones": cantidad_restricciones,
            "variables": len(x),
            "variables_final": len(x),
            "cota_dual": None
        }

    def Opt_ExplorarCantidadPasillos(self, umbral):
        self.columnas = {}
        best_sol, best_val = None, -float('inf')
        tiempo_ini = time.time()
        lista_k = self.Rankear()
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

            if resultado_final is None:
                print("⚠️ Opt_PasillosFijos no devolvió una solución válida.")
                return {
                    "valor_objetivo": 0,
                    "ordenes_seleccionadas": set(),
                    "pasillos_seleccionados": set(),
                    "variables": best_sol.get("variables", 0),
                    "variables_final": best_sol.get("variables_final", 0),
                    "cota_dual": best_sol.get("cota_dual", 0),
                    "instancia": getattr(self, "nombre_input", "")
                }

            resultado_final["variables"] = best_sol.get("variables", None)
            resultado_final["variables_final"] = best_sol.get("variables_final", None)
            resultado_final["cota_dual"] = best_sol.get("cota_dual", None)

            return resultado_final

        print("⚠️ No se encontró ninguna solución válida para ningún valor de k")
        return {
            "valor_objetivo": 0,
            "ordenes_seleccionadas": set(),
            "pasillos_seleccionados": set(),
            "variables": 0,
            "variables_final": 0,
            "cota_dual": 0,
            "restricciones": 0,
            "instancia": getattr(self, "nombre_input", "")
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
