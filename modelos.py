from dataclasses import dataclass
from typing import List # Import List for type hinting

@dataclass
class Item:
    tipo: int
    cantidad: int
    beneficio: int = 1 # Acorde a b_o = 1

@dataclass
class Bolsita:
    indice: int
    items: List[Item]  # Lista de ítems (con cantidad y beneficio)

@dataclass
class Contenedor:
    indice: int
    items: List[Item]  # Lista de ítems (con cantidad y beneficio)
    beneficio: int = 1 # Acorde a b_a = 1

@dataclass
class Parametros:
    total_bolsitas: int # Corrected order as per typical usage
    total_items: int
    total_contenedores: int
    bolsitas: List[Bolsita]
    contenedores: List[Contenedor]
    LB: int = 0 # Added LB
    UB: int = 0 # Added UB