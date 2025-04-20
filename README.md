# Trabajo Práctico - Modelado y Optimización

<div align="center">
  <h2>Universidad Nacional General Sarmiento</h2>
  <h3>Licenciatura en Sistemas</h3>
  <br>
  <strong>Integrantes:</strong><br>
  Juan Manuel Losada<br>
  Facundo Ruiz<br>
  Matías Morales<br>
  Vanesa Vera
  <br><br>
</div>

## Descripción del problema

Este trabajo práctico aborda un problema de optimización lineal relacionado con la asignación de recursos.

### Definiciones

Sea:

- $I = \{0, 1, ..., i-1\}$ un conjunto de tipos de ítems
- $O = \{0, 1, ..., o-1\}$ un conjunto de bolsitas
- $A = \{0, 1, ..., a-1\}$ un conjunto de contenedores

Cada bolsita $j \in O$ contiene una cierta cantidad de ítems $i \in I$. Esto se representa con $c_{ji}$.

De manera similar, cada contenedor $j \in A$ contiene una cierta cantidad de ítems $i \in I$, representado por $d_{ji}$.

Cada ítem proporciona un beneficio unitario por su uso.

### Problema 1

El primer problema consiste en encontrar un contenedor $a \in A$ y un subconjunto de bolsitas $O' \subseteq O$ tales que:

1. La cantidad de veces que aparece cada ítem $i \in I$ en el contenedor alcanza para cubrir las apariciones de $i$ en $O'$.
2. Se maximice la suma de beneficios del contenedor y de los ítems de las bolsitas $O'$.

Formalmente:

$$\max \sum_{i \in I} d_{ai} + \sum_{j \in O'} \sum_{i \in I} c_{ji}$$

sujeto a:

$$d_{ai} \geq \sum_{j \in O'} c_{ji} \quad \forall i \in I$$

### Problema 2

El segundo problema consiste en encontrar subconjuntos $A' \subseteq A$ de contenedores y $O' \subseteq O$ de bolsitas tales que:

1. La cantidad de veces que aparece cada ítem $i \in I$ en $A' alcanza para cubrir las apariciones de $i$ en $O'$.
2. Se maximice la suma de beneficios de los contenedores de $A' y de los ítems de las bolsitas de $O'$.

Formalmente:

$$\max \sum_{a \in A'}\sum_{i \in I} d_{ai} + \sum_{j \in O'} \sum_{i \in I} c_{ji}$$

sujeto a:

$$\sum_{a \in A'} d_{ai} \geq \sum_{j \in O'} c_{ji} \quad \forall i \in I$$

## Requisitos

Para ejecutar este proyecto necesitarás:

- Python 3.7 o superior
- Biblioteca PuLP para resolver problemas de programación lineal

## Instalación

1. Clone o descargue este repositorio
2. Instale la biblioteca PuLP:

```bash
pip install pulp
```

## Estructura del proyecto

El proyecto consta de los siguientes archivos:

- `modelos.py`: Define las clases para representar los datos del problema.
- `leer_archivo.py`: Funciones para cargar los datos desde un archivo de entrada.
- `resolver.py`: Implementación de los modelos de programación lineal para resolver los problemas planteados.
- `entrada_test.txt`: Un archivo de ejemplo con datos de prueba.

## Formato del archivo de entrada

El formato del archivo de entrada es el siguiente:

```
o i a
k tipo_item_1 cantidad_1 tipo_item_2 cantidad_2 ... tipo_item_k cantidad_k
...
l tipo_item_1 cantidad_1 tipo_item_2 cantidad_2 ... tipo_item_l cantidad_l
...
```

Donde:

- Primera línea: `o` (número de bolsitas), `i` (número de tipos de ítems), `a` (número de contenedores)
- Siguientes `o` líneas: descripción de cada bolsita
  - `k` seguido de `k` pares `(tipo_item, cantidad)`
- Siguientes `a` líneas: descripción de cada contenedor
  - `l` seguido de `l` pares `(tipo_item, cantidad)`

## Ejecución

Para ejecutar el programa con los datos de prueba:

```bash
python resolver.py
```

Por defecto, el programa utiliza el archivo `entrada_test.txt`, pero puede modificarse para usar otros archivos de entrada.

## Ejemplo

El archivo de entrada `entrada_test.txt` contiene un ejemplo con:

- 3 bolsitas
- 4 tipos de ítems (0, 1, 2, 3)
- 2 contenedores

El programa resuelve los dos problemas y muestra:

1. Para el Problema 1: qué contenedor seleccionar y qué bolsitas incluir
2. Para el Problema 2: qué subconjunto de contenedores y bolsitas seleccionar

## Implementación

Los modelos de programación lineal se implementan utilizando PuLP, una biblioteca de Python para resolver problemas de optimización lineal. Cada variable de decisión es binaria, indicando si un contenedor o bolsita es seleccionado o no.

Las restricciones principales garantizan que la cantidad de cada tipo de ítem disponible en los contenedores seleccionados sea suficiente para cubrir la demanda de las bolsitas seleccionadas.

La función objetivo maximiza el beneficio total (suma de ítems en contenedores seleccionados y bolsitas seleccionadas).
