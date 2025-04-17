import random
import os
def generar_archivo_inicial(nombre_archivo, cantidad_archivos, megas_disco):
    with open(nombre_archivo, 'w') as f:
        f.write(f"# disk capacities in TB (= 1.000.000 MB)\n")
        f.write(f"{megas_disco}\n")
        f.write("\n")
        f.write(f"# number of files to backup\n")
        f.write(f"{cantidad_archivos}\n")
        f.write("\n")
        f.write("# files: file_id, size (in MB)")
        f.write("\n")
        for i in range(1, cantidad_archivos + 1):
            # Generar un tamaño aleatorio entre 1 MB y 10,000,000 MB
            peso = random.randint(1, 10000000)
            f.write(f"archivo_{i} {peso}\n")

if __name__ == "__main__":
    generar_archivo_inicial("a_1.in", 40, 16)

