import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def verificar_solucion(path, ordenes_sel, pasillos_sel):

    with open(path, "r") as f:
        data = [line.strip() for line in f if line.strip()]

    # ===== Leer encabezado =====
    o, i, a = map(int, data[0].split())
    idx = 1

    # ===== Leer órdenes =====
    W = [[0]*i for _ in range(o)]
    for ord_id in range(o):
        parts = list(map(int, data[idx].split()))
        idx += 1
        k = parts[0]
        for j in range(k):
            e = parts[1 + 2*j]
            q = parts[2 + 2*j]
            W[ord_id][e] = q

    # ===== Leer pasillos =====
    S = [[0]*i for _ in range(a)]
    for pas_id in range(a):
        parts = list(map(int, data[idx].split()))
        idx += 1
        l = parts[0]
        for j in range(l):
            e = parts[1 + 2*j]
            q = parts[2 + 2*j]
            S[pas_id][e] = q

    # ===== Leer LB y UB =====
    LB, UB = map(int, data[idx].split())

    # ===== Calcular demanda y capacidad =====
    demanda = [0]*i
    for o_id in ordenes_sel:
        for e in range(i):
            demanda[e] += W[o_id][e]

    capacidad = [0]*i
    for a_id in pasillos_sel:
        for e in range(i):
            capacidad[e] += S[a_id][e]

    # ===== Verificar capacidades =====
    for e in range(i):
        if demanda[e] > capacidad[e]:
            print(f"❌ No factible: elemento {e}, demanda {demanda[e]}, capacidad {capacidad[e]}")
            return False

    # ===== Unidades totales =====
    total_unidades = sum(demanda)
    if total_unidades > UB:
        print(f"❌ No factible: unidades {total_unidades} fuera de [{UB}]")
        return False

    # ===== Objetivo =====
    if len(pasillos_sel) == 0:
        print("❌ No factible: sin pasillos")
        return False

    valor_obj = total_unidades / len(pasillos_sel)

    print("✅ Solución factible")
    print(f"Unidades totales: {total_unidades}, Pasillos usados: {len(pasillos_sel)}, Valor objetivo: {valor_obj:.2f}")

    return True

def leer_out(path_out):
    ordenes = set()
    pasillos = set()

    with open(path_out, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    modo = None
    for line in lines:
        low = line.lower()

        if low.startswith("ordenes"):
            modo = "ordenes"
            continue
        if low.startswith("pasillos"):
            modo = "pasillos"
            continue

        if modo == "ordenes":
            for x in line.split():
                ordenes.add(int(x))

        elif modo == "pasillos":
            for x in line.split():
                pasillos.add(int(x))

    return ordenes, pasillos


if __name__ == "__main__":
    from pathlib import Path

    base_input = Path("datos_de_entrada")
    base_output = Path("parte5") / "OUTPUT"

    grupos = ["a", "b"]
    instancias = ["instance_0001.txt", "instance_0002.txt"]

    print("=" * 70)
    print("VERIFICACIÓN DE SOLUCIONES – PARTE 5")
    print("=" * 70)

    for grupo in grupos:
        print(f"\nGrupo {grupo.upper()}")
        print("-" * 70)

        carpeta_output_grupo = base_output / grupo.upper()

        if not carpeta_output_grupo.exists():
            print(f"❌ Carpeta de output no encontrada: {carpeta_output_grupo}")
            continue

        for instancia in instancias:
            path_instancia = base_input / grupo / instancia
            print(f"\n📄 Instancia: {instancia}")

            if not path_instancia.exists():
                print(f"   ❌ Input no encontrado: {path_instancia}")
                continue

            path_out = carpeta_output_grupo / instancia.replace(".txt", ".out")

            if not path_out.exists():
                print(f"   ⚠️ Output no encontrado: {path_out.name}")
                continue

            try:
                ordenes, pasillos = leer_out(path_out)
                verificar_solucion(path_instancia, ordenes, pasillos)
            except Exception as e:
                print(f"   ❌ Error: {e}")

    print("\n" + "=" * 70)
    print("FIN DE LA VERIFICACIÓN PARTE 5")
    print("=" * 70)
