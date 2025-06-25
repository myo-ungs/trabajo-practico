"""
Solver rápido para instancias grandes usando heurísticas
"""
import time
import random
from collections import defaultdict

class FastSolver:
    def __init__(self, W, S, LB, UB):
        self.W = W
        self.S = S
        self.LB = LB
        self.UB = UB
        self.n_ordenes = len(W)
        self.n_items = len(W[0]) if W else 0
        self.n_pasillos = len(S)
    
    def heuristica_greedy(self, max_pasillos=None):
        """
        Heurística greedy rápida: selecciona pasillos y órdenes de mayor beneficio
        """
        if max_pasillos is None:
            max_pasillos = min(self.n_pasillos, 30)  # Limitar pasillos
        
        # 1. Rankear pasillos por capacidad total
        capacidades = [(i, sum(self.S[i])) for i in range(self.n_pasillos)]
        capacidades.sort(key=lambda x: x[1], reverse=True)
        pasillos_seleccionados = [p[0] for p in capacidades[:max_pasillos]]
        
        # 2. Calcular capacidad total disponible
        capacidad_total = defaultdict(int)
        for p in pasillos_seleccionados:
            for i, cap in enumerate(self.S[p]):
                capacidad_total[i] += cap
        
        # 3. Seleccionar órdenes greedy
        ordenes_seleccionadas = []
        demanda_usada = defaultdict(int)
        
        # Rankear órdenes por beneficio/demanda
        ratios = []
        for o in range(self.n_ordenes):
            beneficio = sum(self.W[o])
            demanda = sum(self.W[o])
            ratio = beneficio / max(demanda, 1)
            ratios.append((o, ratio, beneficio))
        
        ratios.sort(key=lambda x: x[1], reverse=True)
        
        # Seleccionar órdenes que quepan
        valor_objetivo = 0
        for orden_idx, ratio, beneficio in ratios:
            # Verificar si la orden cabe
            puede_agregar = True
            for i, demanda in enumerate(self.W[orden_idx]):
                if demanda_usada[i] + demanda > capacidad_total[i]:
                    puede_agregar = False
                    break
            
            if puede_agregar and valor_objetivo + beneficio <= self.UB:
                ordenes_seleccionadas.append(orden_idx)
                valor_objetivo += beneficio
                for i, demanda in enumerate(self.W[orden_idx]):
                    demanda_usada[i] += demanda
        
        return {
            "valor_objetivo": valor_objetivo,
            "ordenes_seleccionadas": ordenes_seleccionadas,
            "pasillos_seleccionados": pasillos_seleccionados,
            "variables": len(pasillos_seleccionados),
            "variables_final": len(pasillos_seleccionados),
            "cota_dual": valor_objetivo,
            "restricciones": self.n_items
        }
    
    def optimizacion_local(self, solucion_inicial, tiempo_limite=60):
        """
        Mejora la solución inicial con búsqueda local
        """
        mejor_solucion = solucion_inicial.copy()
        mejor_valor = solucion_inicial["valor_objetivo"]
        
        start_time = time.time()
        iteraciones = 0
        
        while time.time() - start_time < tiempo_limite and iteraciones < 100:
            # Intentar intercambiar órdenes
            nueva_solucion = self._intercambio_ordenes(mejor_solucion)
            
            if nueva_solucion["valor_objetivo"] > mejor_valor:
                mejor_solucion = nueva_solucion
                mejor_valor = nueva_solucion["valor_objetivo"]
                print(f"🔄 Mejora encontrada: {mejor_valor}")
            
            iteraciones += 1
        
        return mejor_solucion
    
    def _intercambio_ordenes(self, solucion):
        """
        Intenta intercambiar una orden seleccionada por una no seleccionada
        """
        ordenes_sel = set(solucion["ordenes_seleccionadas"])
        ordenes_no_sel = [i for i in range(self.n_ordenes) if i not in ordenes_sel]
        
        if not ordenes_no_sel or not ordenes_sel:
            return solucion
        
        # Elegir aleatoriamente
        orden_quitar = random.choice(list(ordenes_sel))
        orden_agregar = random.choice(ordenes_no_sel)
        
        # Crear nueva solución
        nuevas_ordenes = [o for o in solucion["ordenes_seleccionadas"] if o != orden_quitar]
        nuevas_ordenes.append(orden_agregar)
        
        # Verificar factibilidad (simplificado)
        nuevo_valor = sum(sum(self.W[o]) for o in nuevas_ordenes)
        
        if self.LB <= nuevo_valor <= self.UB:
            return {
                "valor_objetivo": nuevo_valor,
                "ordenes_seleccionadas": nuevas_ordenes,
                "pasillos_seleccionados": solucion["pasillos_seleccionados"],
                "variables": solucion["variables"],
                "variables_final": solucion["variables_final"],
                "cota_dual": nuevo_valor,
                "restricciones": solucion["restricciones"]
            }
        
        return solucion
    
    def Opt_ExplorarCantidadPasillos(self, tiempo_limite):
        """
        Método compatible con el solver original
        """
        print("🚀 Usando FastSolver para instancia grande...")
        
        # 1. Solución greedy inicial
        solucion_inicial = self.heuristica_greedy()
        print(f"✅ Solución greedy: {solucion_inicial['valor_objetivo']}")
        
        # 2. Optimización local si hay tiempo
        if tiempo_limite > 60:
            tiempo_local = min(tiempo_limite - 30, 120)  # Máximo 2 minutos
            solucion_final = self.optimizacion_local(solucion_inicial, tiempo_local)
            print(f"✅ Después de optimización local: {solucion_final['valor_objetivo']}")
        else:
            solucion_final = solucion_inicial
        
        return solucion_final
