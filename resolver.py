from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, lpSum, LpBinary
from leer_archivo import cargar_parametros_desde_archivo, imprimir_parametros
from modelos import Parametros

def resolver_problema1(parametros: Parametros):
    """
    Resuelve el problema 1:
    Encontrar un container a ∈ A y un subconjunto de bolsitas O' ⊆ O tales que:
    - La cantidad de veces que aparece cada item i ∈ I en el container alcance para cubrir
      las apariciones de i en O'
    - Se maximice la suma de beneficios del container y de los items de las bolsitas O'
    """
    print("\n======== RESOLVIENDO PROBLEMA 1 ========")
    
    modelo = LpProblem(name="problema1", sense=LpMaximize)

    # Variables binarias para seleccionar contenedor (solo uno)
    x_contenedor = [LpVariable(f"x_contenedor_{j}", cat=LpBinary) for j in range(parametros.total_contenedores)]
    
    # Variables binarias para seleccionar bolsitas
    y_bolsita = [LpVariable(f"y_bolsita_{j}", cat=LpBinary) for j in range(parametros.total_bolsitas)]
    
    # Restricción: seleccionar exactamente un contenedor
    modelo += lpSum(x_contenedor) == 1, "seleccionar_un_contenedor"
    
    # Restricciones de capacidad para cada tipo de ítem
    for i in range(parametros.total_items):
        # Cantidad disponible en el contenedor seleccionado
        disponible = lpSum(
            x_contenedor[contenedor.indice] * sum(item.cantidad for item in contenedor.items if item.tipo == i)
            for contenedor in parametros.contenedores
        )
        
        # Cantidad requerida por las bolsitas seleccionadas
        requerido = lpSum(
            y_bolsita[bolsita.indice] * sum(item.cantidad for item in bolsita.items if item.tipo == i)
            for bolsita in parametros.bolsitas
        )
        
        # La cantidad disponible debe ser mayor o igual a la requerida
        modelo += disponible >= requerido, f"capacidad_item_{i}"
    
    # Función objetivo: maximizar beneficios (asumiendo beneficio = 1 para todos)
    # Beneficios de contenedores
    beneficio_contenedores = lpSum(
        x_contenedor[contenedor.indice] * sum(item.beneficio * item.cantidad for item in contenedor.items)
        for contenedor in parametros.contenedores
    )
    
    # Beneficios de bolsitas
    beneficio_bolsitas = lpSum(
        y_bolsita[bolsita.indice] * sum(item.beneficio * item.cantidad for item in bolsita.items)
        for bolsita in parametros.bolsitas
    )
    
    modelo += beneficio_contenedores + beneficio_bolsitas, "maximizar_beneficio_total"
    
    # Resolver modelo
    status = modelo.solve()
    
    # Mostrar resultados
    print(f"Status: {LpStatus[status]}")
    
    if status == 1:  # Optimal
        print("\nSOLUCIÓN ÓPTIMA ENCONTRADA:")
        
        # Contenedor seleccionado
        contenedor_seleccionado = None
        for j in range(parametros.total_contenedores):
            if x_contenedor[j].value() > 0.5:
                contenedor_seleccionado = j
                print(f"Contenedor seleccionado: {j}")
                break
        
        # Bolsitas seleccionadas
        bolsitas_seleccionadas = []
        for j in range(parametros.total_bolsitas):
            if y_bolsita[j].value() > 0.5:
                bolsitas_seleccionadas.append(j)
        
        print(f"Bolsitas seleccionadas: {bolsitas_seleccionadas}")
        print(f"Beneficio total: {modelo.objective.value()}")
        
        return {
            "contenedor": contenedor_seleccionado,
            "bolsitas": bolsitas_seleccionadas,
            "beneficio": modelo.objective.value()
        }
    else:
        print("No se encontró solución óptima.")
        return None

def resolver_problema2(parametros: Parametros):
    """
    Resuelve el problema 2:
    Encontrar subconjuntos A' ⊆ A de contenedores y O' ⊆ O de bolsitas tales que:
    - La cantidad de veces que aparece cada item i ∈ I en A' alcance para cubrir
      las apariciones de i en O'
    - Se maximice la suma de beneficios de los contenedores de A' y de los items de las bolsitas de O'
    """
    print("\n======== RESOLVIENDO PROBLEMA 2 ========")
    
    modelo = LpProblem(name="problema2", sense=LpMaximize)

    # Variables binarias para seleccionar contenedores
    x_contenedor = [LpVariable(f"x_contenedor_{j}", cat=LpBinary) for j in range(parametros.total_contenedores)]
    
    # Variables binarias para seleccionar bolsitas
    y_bolsita = [LpVariable(f"y_bolsita_{j}", cat=LpBinary) for j in range(parametros.total_bolsitas)]
    
    # Restricciones de capacidad para cada tipo de ítem
    for i in range(parametros.total_items):
        # Cantidad disponible en los contenedores seleccionados
        disponible = lpSum(
            x_contenedor[contenedor.indice] * sum(item.cantidad for item in contenedor.items if item.tipo == i)
            for contenedor in parametros.contenedores
        )
        
        # Cantidad requerida por las bolsitas seleccionadas
        requerido = lpSum(
            y_bolsita[bolsita.indice] * sum(item.cantidad for item in bolsita.items if item.tipo == i)
            for bolsita in parametros.bolsitas
        )
        
        # La cantidad disponible debe ser mayor o igual a la requerida
        modelo += disponible >= requerido, f"capacidad_item_{i}"
    
    # Función objetivo: maximizar beneficios (asumiendo beneficio = 1 para todos)
    # Beneficios de contenedores
    beneficio_contenedores = lpSum(
        x_contenedor[contenedor.indice] * sum(item.beneficio * item.cantidad for item in contenedor.items)
        for contenedor in parametros.contenedores
    )
    
    # Beneficios de bolsitas
    beneficio_bolsitas = lpSum(
        y_bolsita[bolsita.indice] * sum(item.beneficio * item.cantidad for item in bolsita.items)
        for bolsita in parametros.bolsitas
    )
    
    modelo += beneficio_contenedores + beneficio_bolsitas, "maximizar_beneficio_total"
    
    # Resolver modelo
    status = modelo.solve()
    
    # Mostrar resultados
    print(f"Status: {LpStatus[status]}")
    
    if status == 1:  # Optimal
        print("\nSOLUCIÓN ÓPTIMA ENCONTRADA:")
        
        # Contenedores seleccionados
        contenedores_seleccionados = []
        for j in range(parametros.total_contenedores):
            if x_contenedor[j].value() > 0.5:
                contenedores_seleccionados.append(j)
        
        print(f"Contenedores seleccionados: {contenedores_seleccionados}")
        
        # Bolsitas seleccionadas
        bolsitas_seleccionadas = []
        for j in range(parametros.total_bolsitas):
            if y_bolsita[j].value() > 0.5:
                bolsitas_seleccionadas.append(j)
        
        print(f"Bolsitas seleccionadas: {bolsitas_seleccionadas}")
        print(f"Beneficio total: {modelo.objective.value()}")
        
        return {
            "contenedores": contenedores_seleccionados,
            "bolsitas": bolsitas_seleccionadas,
            "beneficio": modelo.objective.value()
        }
    else:
        print("No se encontró solución óptima.")
        return None

if __name__ == "__main__":
    # Cargar parámetros desde el archivo
    nombre_archivo = "entrada_test.txt"
    parametros = cargar_parametros_desde_archivo(nombre_archivo)
    
    print(f"Cargando datos del archivo: {nombre_archivo}")
    imprimir_parametros(parametros)
    
    # Resolver problema 1
    solucion1 = resolver_problema1(parametros)
    
    # Resolver problema 2
    solucion2 = resolver_problema2(parametros)