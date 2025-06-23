import time
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatusOptimal, PULP_CBC_CMD, LpBinary

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

    def _crear_columna_inicial(self, a):
        unidades_o = [sum(self.W[o]) for o in range(self.O)]
        ordenes = sorted(range(self.O), key=lambda o: -unidades_o[o])
        cap = self.S[a][:]
        sel = [0]*self.O
        total = 0
        for o in ordenes:
            if total + unidades_o[o] > self.UB:
                continue
            if all(self.W[o][i] <= cap[i] for i in range(self.I)):
                sel[o] = 1
                total += unidades_o[o]
                for i in range(self.I):
                    cap[i] -= self.W[o][i]
            if total == self.UB:
                break
        return {'pasillo': a, 'ordenes': sel, 'unidades': total}

    def construir_modelo(self, k):
        modelo = LpProblem(f"RMP_k_{k}", LpMaximize)

        if k not in self.columnas:
            self.columnas[k] = [self._crear_columna_inicial(a) for a in range(self.A)]

        x_vars = [LpVariable(f"x_{k}_{idx}", cat=LpBinary) for idx, _ in enumerate(self.columnas[k])]

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

        beneficio = lpSum(
            x_vars[j]*sum(self.W[o][i] for o in range(self.O) for i in range(self.I) if self.columnas[k][j]['ordenes'][o])
            for j in range(len(x_vars))
        )
        modelo += beneficio

        return modelo, x_vars

    def agregar_columna(self, k, nueva_col):
        if k not in self.columnas:
            self.columnas[k] = []
        for col in self.columnas[k]:
            if col['pasillo'] == nueva_col['pasillo'] and col['ordenes'] == nueva_col['ordenes']:
                return False
        self.columnas[k].append(nueva_col)
        print(f"[+] Nueva columna agregada para k={k}: pasillo={nueva_col['pasillo']} ords={nueva_col['ordenes']}")
        return True

    def resolver_modelo(self, modelo, time_limit):
        solver = PULP_CBC_CMD(timeLimit=time_limit, msg=0)
        resultado = modelo.solve(solver)
        return modelo if resultado == LpStatusOptimal else None

    def obtener_valores_duales(self, modelo):
        duales = []
        for o in range(self.O):
            cons = modelo.constraints.get(f"orden_{o}")
            duales.append(cons.pi if cons else 0.0)
        return duales

    def buscar_columna_mejoradora(self, k, duales):
        best_val = -float('inf'); best_col = None
        for a in range(self.A):
            ordenes = [0]*self.O; unidades_o = [sum(self.W[o]) for o in range(self.O)]
            cap = self.S[a][:]; total = 0
            for o in sorted(range(self.O), key=lambda o: -unidades_o[o]):
                if unidades_o[o] + total > self.UB:
                    continue
                if all(self.W[o][i] <= cap[i] for i in range(self.I)):
                    rc = unidades_o[o] - duales[o]
                    if rc > 0:
                        ordenes[o] = 1
                        total += unidades_o[o]
                        for i in range(self.I):
                            cap[i] -= self.W[o][i]
            valor_col = sum((sum(self.W[o]) - duales[o]) * ordenes[o] for o in range(self.O))
            if valor_col > best_val:
                best_val = valor_col
                best_col = {'pasillo': a, 'ordenes': ordenes, 'unidades': total}
        return best_col if best_val > 0 else None

    def Opt_cantidadPasillosFija(self, k, umbral):
        tiempo_ini = time.time()
        self.columnas.setdefault(k, [self._crear_columna_inicial(a) for a in range(self.A)])
        while time.time() - tiempo_ini < umbral:
            modelo, x_vars = self.construir_modelo(k)
            modelo_resuelto = self.resolver_modelo(modelo, umbral)
            if not modelo_resuelto:
                break
            duales = self.obtener_valores_duales(modelo)
            nueva = self.buscar_columna_mejoradora(k, duales)
            if not nueva or not self.agregar_columna(k, nueva):
                break
        modelo, x_vars = self.construir_modelo(k)
        modelo_resuelto = self.resolver_modelo(modelo, umbral)
        if not modelo_resuelto:
            return None
        aisles, orders = set(), set()
        for idx, x in enumerate(x_vars):
            if x.varValue and x.varValue > 1e-5:
                aisles.add(self.columnas[k][idx]['pasillo'])
                for o, val in enumerate(self.columnas[k][idx]['ordenes']):
                    if val:
                        orders.add(o)
        return {"valor_objetivo": int(modelo.objective.value()), "pasillos_seleccionados": aisles, "ordenes_seleccionadas": orders}

    def Opt_PasillosFijos(self, pasillos, umbral):
        k = len(pasillos)
        self.columnas[k] = [col for col in self.columnas.get(k, []) if col['pasillo'] in pasillos]
        return self.Opt_cantidadPasillosFija(k, umbral)

    def Opt_ExplorarCantidadPasillos(self, umbral):
        self.columnas = {}
        best_sol, best_val = None, -float('inf')
        tiempo_ini = time.time()
        for k in range(1, self.A+1):
            if time.time() - tiempo_ini >= umbral:
                break
            rem = umbral - (time.time() - tiempo_ini)
            sol = self.Opt_cantidadPasillosFija(k, rem)
            if sol and sol["valor_objetivo"] > best_val:
                best_val = sol["valor_objetivo"]
                best_sol = sol
        if best_sol:
            rem = max(0.1, umbral - (time.time() - tiempo_ini))
            return self.Opt_PasillosFijos(best_sol["pasillos_seleccionados"], rem)
        return None
