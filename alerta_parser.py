#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alerta_parser.py - Analizador léxico y sintáctico del mini-lenguaje ALERTA.

Uso:
    python alerta_parser.py programa.alerta            árbol o lista de errores
    python alerta_parser.py programa.alerta --tokens   además, lista de tokens
    python alerta_parser.py programa.alerta --traza    además, cada paso del AFD
    python alerta_parser.py --pruebas                  batería de pruebas

Parte 1: el AFD convierte el texto en tokens (Tabla 3 del documento).
Parte 2: el parser comprueba la gramática G; cada regla es una función.
Parte 3: se imprime el árbol de derivación o la lista de errores.
"""

import sys

sys.setrecursionlimit(20000)

# =============================================================================
# PARTE 1. ANÁLISIS LÉXICO (AFD)
# =============================================================================

MINUSCULAS = set("abcdefghijklmnopqrstuvwxyzñ")
MAYUSCULAS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZÑ")
DIGITOS = set("0123456789")
ACENTOS = set("áéíóúüÁÉÍÓÚÜ¿¡")
ESPACIOS = set(" \t\r")
ASCII_IMPRIMIBLE = {chr(codigo) for codigo in range(32, 127)}
SIGMA = ASCII_IMPRIMIBLE | MINUSCULAS | MAYUSCULAS | ACENTOS | ESPACIOS | {"\n"}

CLASES_DE_UN_SIMBOLO = {
    "_": "_", "=": "=", "<": "<>", ">": "<>", "!": "!", "+": "+-", "-": "+-",
    "*": "*/", "/": "*/", "(": "(", ")": ")", ";": ";", "#": "#", "\n": "nl",
}


def clase(simbolo):
    """Devuelve la columna de la matriz, o None si el símbolo no está en Σ."""
    if simbolo not in SIGMA:
        return None
    if simbolo in MINUSCULAS:
        return "l"
    if simbolo in MAYUSCULAS:
        return "U"
    if simbolo in DIGITOS:
        return "d"
    if simbolo in ESPACIOS:
        return "esp"
    return CLASES_DE_UN_SIMBOLO.get(simbolo, "otro")


# Función de transición δ. Cada fila es un estado; E es el estado trampa qE.
COLUMNAS = "l U d _ = <> ! +- */ ( ) ; # esp nl otro".split()
MATRIZ = """
q0   q1  q2  q3  E   q6 q7 q9 q10 q11 q12 q13 q14 q4 q5 q5 E
q1   q1  q15 q1  q1  E  E  E  E   E   E   E   E   E  E  E  E
q2   q15 q2  q2  q2  E  E  E  E   E   E   E   E   E  E  E  E
q3   q15 q15 q3  q15 E  E  E  E   E   E   E   E   E  E  E  E
q4   q4  q4  q4  q4  q4 q4 q4 q4  q4  q4  q4  q4  q4 q4 E  q4
q5   E   E   E   E   E  E  E  E   E   E   E   E   E  q5 q5 E
q6   E   E   E   E   q8 E  E  E   E   E   E   E   E  E  E  E
q7   E   E   E   E   q8 E  E  E   E   E   E   E   E  E  E  E
q8   E   E   E   E   E  E  E  E   E   E   E   E   E  E  E  E
q9   E   E   E   E   q8 E  E  E   E   E   E   E   E  E  E  E
q10  E   E   E   E   E  E  E  E   E   E   E   E   E  E  E  E
q11  E   E   E   E   E  E  E  E   E   E   E   E   E  E  E  E
q12  E   E   E   E   E  E  E  E   E   E   E   E   E  E  E  E
q13  E   E   E   E   E  E  E  E   E   E   E   E   E  E  E  E
q14  E   E   E   E   E  E  E  E   E   E   E   E   E  E  E  E
q15  q15 q15 q15 q15 E  E  E  E   E   E   E   E   E  E  E  E
E    E   E   E   E   E  E  E  E   E   E   E   E   E  E  E  E
"""

DELTA = {}
for fila in MATRIZ.strip().splitlines():
    estado, *destinos = fila.split()
    DELTA[estado] = dict(zip(COLUMNAS, destinos))

# Estados de aceptación y el token que produce cada uno.
ACEPTACION = {
    "q1": "ID", "q2": "NOMBRE", "q3": "NUM", "q4": "COMENTARIO", "q5": "ESPACIO",
    "q6": "=", "q7": "OPREL", "q8": "OPREL", "q10": "OPSUMA", "q11": "OPMUL",
    "q12": "(", "q13": ")", "q14": ";",
}
IGNORADOS = {"COMENTARIO", "ESPACIO"}

# Estados de rechazo: (código, mensaje, token con el que sigue el parser).
RECHAZO = {
    "q9": ("L02", "'!' aislado: el operador válido es '!='", "OPREL"),
    "q15": ("L03", "palabra mal formada: mezcla mayúsculas, minúsculas o dígitos", "ID"),
}

RESERVADAS = {
    "programa", "sensor", "inicio", "fin", "alertar", "esperar", "si", "entonces",
    "sino", "mientras", "hacer", "leer", "o", "y", "AMARILLA", "NARANJA", "ROJA",
}


class Token:
    def __init__(self, tipo, lexema, linea, columna):
        self.tipo, self.lexema, self.linea, self.columna = tipo, lexema, linea, columna


class Error:
    def __init__(self, codigo, mensaje, linea, columna):
        self.codigo, self.mensaje, self.linea, self.columna = codigo, mensaje, linea, columna

    def __str__(self):
        return f"[{self.codigo}] línea {self.linea}, columna {self.columna}: {self.mensaje}"


def analizar_lexico(texto, mostrar_traza=False):
    """Recorre el texto con δ. Cada token termina cuando δ lleva a qE."""
    tokens, errores = [], []
    i, linea, columna = 0, 1, 1

    while i < len(texto):
        estado, j = "q0", i
        while j < len(texto) and clase(texto[j]) is not None:
            siguiente = DELTA[estado][clase(texto[j])]
            if mostrar_traza:
                print(f"  δ({estado}, {texto[j]!r}) = {'qE' if siguiente == 'E' else siguiente}")
            if siguiente == "E":
                break
            estado, j = siguiente, j + 1

        if j == i:  # Ningún token empieza con este símbolo.
            if clase(texto[i]) is None:
                errores.append(Error("L04", f"símbolo fuera de Σ: {texto[i]!r}", linea, columna))
            else:
                errores.append(Error("L01", f"símbolo que no inicia un token: {texto[i]!r}",
                                     linea, columna))
            j = i + 1
        else:
            lexema = texto[i:j]
            if estado in ACEPTACION:
                tipo = lexema if lexema in RESERVADAS else ACEPTACION[estado]
                if tipo not in IGNORADOS:
                    tokens.append(Token(tipo, lexema, linea, columna))
            else:
                codigo, mensaje, tipo = RECHAZO[estado]
                errores.append(Error(codigo, f"{mensaje}: {lexema!r}", linea, columna))
                tokens.append(Token(tipo, lexema, linea, columna))

        for simbolo in texto[i:j]:  # Actualiza la posición para los mensajes.
            linea, columna = (linea + 1, 1) if simbolo == "\n" else (linea, columna + 1)
        i = j

    tokens.append(Token("$", "fin de archivo", linea, columna))
    return tokens, errores


# =============================================================================
# PARTE 2. ANÁLISIS SINTÁCTICO (descendente recursivo)
# =============================================================================
# Cada función corresponde a un no terminal de la gramática G. Para decidir qué
# alternativa usar, basta mirar el token actual, porque G es LL(1).

class ErrorSintactico(Exception):
    pass


class Nodo:
    """Nodo del árbol de derivación."""

    def __init__(self, simbolo, hijos=None, lexema=""):
        self.simbolo, self.hijos, self.lexema = simbolo, hijos or [], lexema


def epsilon(no_terminal):
    return Nodo(no_terminal, [Nodo("ε")])


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        self.errores = []

    def tipo(self):
        return self.tokens[self.i].tipo

    def consumir(self, esperado):
        """Empareja un terminal y avanza; si no coincide, es un error S01."""
        token = self.tokens[self.i]
        if token.tipo != esperado:
            self.fallar("S01", f"se esperaba {esperado} y se encontró {token.lexema!r}")
        self.i += 1
        return Nodo(token.tipo, lexema=token.lexema)

    def fallar(self, codigo, mensaje):
        token = self.tokens[self.i]
        raise ErrorSintactico(Error(codigo, mensaje, token.linea, token.columna))

    def registrar(self, excepcion):
        """Guarda el error; si ya hay uno en la misma posición, lo ignora."""
        error = excepcion.args[0]
        if not any((e.linea, e.columna) == (error.linea, error.columna) for e in self.errores):
            self.errores.append(error)

    def sincronizar(self, parada):
        """Modo pánico: salta tokens hasta el fin de la sentencia o una parada."""
        while self.tipo() not in parada and self.tipo() != "$":
            if self.tipo() == ";":
                self.i += 1
                return
            self.i += 1

    # <programa> ::= "programa" NOMBRE <sensores> "inicio" <sentencias> "fin"
    def programa(self):
        hijos = [self.consumir("programa"), self.consumir("NOMBRE"), self.sensores(),
                 self.consumir("inicio"), self.sentencias(), self.consumir("fin")]
        self.consumir("$")
        return Nodo("<programa>", hijos)

    # <sensores> ::= "sensor" NOMBRE ";" <sensores> | ε
    def sensores(self):
        if self.tipo() != "sensor":
            return epsilon("<sensores>")
        try:
            hijos = [self.consumir("sensor"), self.consumir("NOMBRE"), self.consumir(";")]
        except ErrorSintactico as error:
            self.registrar(error)
            self.sincronizar({"sensor", "inicio"})
            hijos = []
        return Nodo("<sensores>", hijos + [self.sensores()])

    # <sentencias> ::= <sentencia> <sentencias> | ε
    def sentencias(self):
        if self.tipo() in ("fin", "sino", "$"):
            return epsilon("<sentencias>")
        try:
            hijos = [self.sentencia()]
        except ErrorSintactico as error:
            self.registrar(error)
            self.sincronizar({"fin", "sino", "ID", "alertar", "esperar", "si", "mientras"})
            hijos = []
        return Nodo("<sentencias>", hijos + [self.sentencias()])

    # <sentencia> ::= ID "=" <exp> ";" | "alertar" <nivel> ";" | "esperar" <exp> ";"
    #               | "si" <exp> "entonces" <sentencias> <alternativa> "fin"
    #               | "mientras" <exp> "hacer" <sentencias> "fin"
    def sentencia(self):
        tipo = self.tipo()
        if tipo == "ID":
            hijos = [self.consumir("ID"), self.consumir("="), self.exp(), self.consumir(";")]
        elif tipo == "alertar":
            hijos = [self.consumir("alertar"), self.nivel(), self.consumir(";")]
        elif tipo == "esperar":
            hijos = [self.consumir("esperar"), self.exp(), self.consumir(";")]
        elif tipo == "si":
            hijos = [self.consumir("si"), self.exp(), self.consumir("entonces"),
                     self.sentencias(), self.alternativa(), self.consumir("fin")]
        elif tipo == "mientras":
            hijos = [self.consumir("mientras"), self.exp(), self.consumir("hacer"),
                     self.sentencias(), self.consumir("fin")]
        else:
            self.fallar("S02", f"se esperaba una sentencia y se encontró "
                               f"{self.tokens[self.i].lexema!r}")
        return Nodo("<sentencia>", hijos)

    # <alternativa> ::= "sino" <sentencias> | ε
    def alternativa(self):
        if self.tipo() != "sino":
            return epsilon("<alternativa>")
        return Nodo("<alternativa>", [self.consumir("sino"), self.sentencias()])

    # <nivel> ::= "AMARILLA" | "NARANJA" | "ROJA"
    def nivel(self):
        if self.tipo() not in ("AMARILLA", "NARANJA", "ROJA"):
            self.fallar("S02", f"nivel de alerta no válido: {self.tokens[self.i].lexema!r}")
        return Nodo("<nivel>", [self.consumir(self.tipo())])

    # <exp> ::= <conj> <exp'>
    def exp(self):
        return Nodo("<exp>", [self.conj(), self.exp_prima()])

    # <exp'> ::= "o" <conj> <exp'> | ε
    def exp_prima(self):
        if self.tipo() != "o":
            return epsilon("<exp'>")
        return Nodo("<exp'>", [self.consumir("o"), self.conj(), self.exp_prima()])

    # <conj> ::= <rel> <conj'>
    def conj(self):
        return Nodo("<conj>", [self.rel(), self.conj_prima()])

    # <conj'> ::= "y" <rel> <conj'> | ε
    def conj_prima(self):
        if self.tipo() != "y":
            return epsilon("<conj'>")
        return Nodo("<conj'>", [self.consumir("y"), self.rel(), self.conj_prima()])

    # <rel> ::= <suma> <rel'>
    def rel(self):
        return Nodo("<rel>", [self.suma(), self.rel_prima()])

    # <rel'> ::= OPREL <suma> | ε
    def rel_prima(self):
        if self.tipo() != "OPREL":
            return epsilon("<rel'>")
        return Nodo("<rel'>", [self.consumir("OPREL"), self.suma()])

    # <suma> ::= <prod> <suma'>
    def suma(self):
        return Nodo("<suma>", [self.prod(), self.suma_prima()])

    # <suma'> ::= OPSUMA <prod> <suma'> | ε
    def suma_prima(self):
        if self.tipo() != "OPSUMA":
            return epsilon("<suma'>")
        return Nodo("<suma'>", [self.consumir("OPSUMA"), self.prod(), self.suma_prima()])

    # <prod> ::= <factor> <prod'>
    def prod(self):
        return Nodo("<prod>", [self.factor(), self.prod_prima()])

    # <prod'> ::= OPMUL <factor> <prod'> | ε
    def prod_prima(self):
        if self.tipo() != "OPMUL":
            return epsilon("<prod'>")
        return Nodo("<prod'>", [self.consumir("OPMUL"), self.factor(), self.prod_prima()])

    # <factor> ::= NUM | ID | "leer" NOMBRE | "(" <exp> ")"
    def factor(self):
        tipo = self.tipo()
        if tipo in ("NUM", "ID"):
            hijos = [self.consumir(tipo)]
        elif tipo == "leer":
            hijos = [self.consumir("leer"), self.consumir("NOMBRE")]
        elif tipo == "(":
            hijos = [self.consumir("("), self.exp(), self.consumir(")")]
        else:
            self.fallar("S02", f"se esperaba un valor y se encontró "
                               f"{self.tokens[self.i].lexema!r}")
        return Nodo("<factor>", hijos)


def analizar_sintaxis(tokens):
    """Devuelve (árbol, errores). Si algo falla fuera de una sentencia, se detiene."""
    parser = Parser(tokens)
    try:
        arbol = parser.programa()
    except ErrorSintactico as error:
        parser.registrar(error)
        arbol = None
    return arbol, parser.errores


# =============================================================================
# PARTE 3. SALIDAS Y PROGRAMA PRINCIPAL
# =============================================================================

def imprimir_arbol(nodo, prefijo="", ultimo=True, raiz=True):
    etiqueta = nodo.simbolo
    if nodo.lexema and nodo.lexema != nodo.simbolo:
        etiqueta += f": {nodo.lexema}"
    print(prefijo + ("" if raiz else "└── " if ultimo else "├── ") + etiqueta)
    prefijo_hijos = prefijo + ("" if raiz else "    " if ultimo else "│   ")
    for indice, hijo in enumerate(nodo.hijos):
        imprimir_arbol(hijo, prefijo_hijos, indice == len(nodo.hijos) - 1, False)


def en_programa(sentencias):
    return f"programa P inicio {sentencias} fin"


# (nombre de la prueba, código, códigos de error esperados)
PRUEBAS = [
    ("programa mínimo", "programa P inicio fin", []),
    ("sensores y lectura", "programa P sensor A; sensor B; inicio x = leer A; fin", []),
    ("jerarquía de operadores", en_programa("x = 2 + 3 * (4 - 1) / 5;"), []),
    ("expresión lógica", en_programa("x = a < 1 o b >= 2 y c != 3;"), []),
    ("condicional anidado", en_programa("si a entonces si b entonces alertar ROJA; "
                                        "sino esperar 2; fin sino alertar AMARILLA; fin"), []),
    ("ciclo y comentario", "programa P # nota\ninicio mientras i < 3 hacer i = i + 1; fin fin", []),
    ("L01 símbolo sin token", en_programa("x = 2 @;"), ["L01"]),
    ("L02 admiración aislada", en_programa("x = a ! b;"), ["L02"]),
    ("L03 palabra mal formada", en_programa("x = 12abc;"), ["L03"]),
    ("L04 símbolo fuera de Σ", en_programa("x = 2 €;"), ["L04"]),
    ("S01 falta punto y coma", en_programa("x = 1 esperar 2;"), ["S01"]),
    ("S01 falta fin", "programa P inicio si a entonces esperar 1;", ["S01"]),
    ("S02 expresión incompleta", en_programa("x = 2 + ;"), ["S02"]),
    ("S02 nivel inexistente", en_programa("alertar VERDE;"), ["S02"]),
    ("S01 relación encadenada", en_programa("x = 1 < 2 < 3;"), ["S01"]),
    ("varios errores", en_programa("x = ; esperar ; z = 2 3;"), ["S02", "S02", "S01"]),
]


def ejecutar_pruebas():
    correctas = 0
    for nombre, codigo, esperado in PRUEBAS:
        tokens, errores_lexicos = analizar_lexico(codigo)
        _, errores_sintacticos = analizar_sintaxis(tokens)
        obtenido = [e.codigo for e in errores_lexicos + errores_sintacticos]
        correctas += obtenido == esperado
        print(f"{'OK   ' if obtenido == esperado else 'FALLA'} {nombre}: {obtenido or 'sin errores'}")
    print(f"\n{correctas} de {len(PRUEBAS)} pruebas correctas.")
    return 0 if correctas == len(PRUEBAS) else 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argumentos = sys.argv[1:]
    if "--pruebas" in argumentos:
        return ejecutar_pruebas()
    archivos = [a for a in argumentos if not a.startswith("--")]
    if len(archivos) != 1:
        print(__doc__)
        return 2

    try:
        with open(archivos[0], encoding="utf-8", newline="") as fuente:
            codigo = fuente.read()
    except (OSError, UnicodeDecodeError) as error:
        print(f"No se pudo leer {archivos[0]}: {error}")
        return 2

    tokens, errores_lexicos = analizar_lexico(codigo, "--traza" in argumentos)
    if "--tokens" in argumentos:
        for token in tokens:
            print(f"{token.linea:>4}:{token.columna:<4} {token.tipo:10} {token.lexema}")
    arbol, errores_sintacticos = analizar_sintaxis(tokens)

    errores = sorted(errores_lexicos + errores_sintacticos, key=lambda e: (e.linea, e.columna))
    if errores:
        print(f"LISTA DE ERRORES ({len(errores)})")
        for error in errores:
            print(f"  {error}")
        print("\nRESULTADO: programa RECHAZADO.")
        return 1
    print("ÁRBOL DE DERIVACIÓN")
    imprimir_arbol(arbol)
    print("\nRESULTADO: programa ACEPTADO.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
