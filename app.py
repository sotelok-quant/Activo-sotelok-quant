from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__)

DB_NAME = "lottery.db"

# Diccionario oficial de animales de la lotería
ANIMALES = {
    0: "Delfín", 1: "Carnero", 2: "Toro", 3: "Ciempiés", 4: "Alacrán",
    5: "León", 6: "Rana", 7: "Perico", 8: "Ratón", 9: "Águila",
    10: "Tigre", 11: "Gato", 12: "Caballo", 13: "Mono", 14: "Paloma",
    15: "Zorro", 16: "Oso", 17: "Pavo", 18: "Burro", 19: "Chivo",
    20: "Cochino", 21: "Gallo", 22: "Camello", 23: "Zebra", 24: "Iguana",
    25: "Gallina", 26: "Vaca", 27: "Perro", 28: "Zamuro", 29: "Elefante",
    30: "Caimán", 31: "Lapa", 32: "Ardilla", 33: "Pescado", 34: "Venado",
    35: "Jirafas", 36: "Culebra"
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            numero INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/cargar', methods=['POST'])
def cargar_resultados():
    data = request.json
    fecha = data.get('fecha')
    numeros = data.get('numeros')

    if not fecha or not numeros:
        return jsonify({"error": "Faltan datos (fecha o números)"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for num in numeros:
        cursor.execute("INSERT INTO resultados (fecha, numero) VALUES (?, ?)", (fecha, int(num)))
    conn.commit()
    conn.close()

    return jsonify({"message": "Resultados guardados con éxito en la base de datos."}), 200

@app.route('/api/prediccion', methods=['GET'])
def prediccion_cuant():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT numero FROM resultados ORDER BY id ASC")
    filas = cursor.fetchall()
    conn.close()

    if len(filas) < 10:
        return jsonify({"error": "Se necesitan al menos 10 resultados en la base de datos para realizar un análisis cuantitativo confiable."}), 400

    secuencia = [row[0] for row in filas]
    ultimo = secuencia[-1]
    total_sorteos = len(secuencia)

    # 1. Análisis de Frecuencias Absolutas y Retrasos
    conteo_general = {i: 0 for i in ANIMALES.keys()}
    ultima_aparicion = {i: -1 for i in ANIMALES.keys()}

    for idx, num in enumerate(secuencia):
        if num in conteo_general:
            conteo_general[num] += 1
            ultima_aparicion[num] = idx

    retrasos = {}
    for num in ANIMALES.keys():
        if ultima_aparicion[num] == -1:
            retrasos[num] = total_sorteos  # Nunca ha salido o base máxima
        else:
            retrasos[num] = (total_sorteos - 1) - ultima_aparicion[num]

    # 2. Análisis de Transiciones de Markov (Orden 1)
    transiciones = {}
    for i in range(len(secuencia) - 1):
        actual = secuencia[i]
        siguiente = secuencia[i+1]
        if actual not in transiciones:
            transiciones[actual] = {}
        if siguiente not in transiciones[actual]:
            transiciones[actual][siguiente] = 0
        transiciones[actual][siguiente] += 1

    # 3. Sistema de Puntuación Ponderada (Scoring)
    puntajes = {i: 0.0 for i in ANIMALES.keys()}
    
    # Puntuación por transición directa desde el último número
    candidatos_trans = transiciones.get(ultimo, {})
    total_trans_ultimo = sum(candidatos_trans.values()) if candidatos_trans else 1

    for num in ANIMALES.keys():
        # Ponderación 1: Probabilidad de transición (Peso 40%)
        frec_trans = candidatos_trans.get(num, 0)
        prob_trans = (frec_trans / total_trans_ultimo) * 40 if total_trans_ultimo > 0 else 0

        # Ponderación 2: Factor de retraso (Peso 40%) - Premia animales con buen acumulado de ausencia
        retraso_actual = retrasos[num]
        factor_retraso = min(retraso_actual / (total_sorteos * 0.05 + 1), 1.0) * 40

        # Ponderación 3: Frecuencia global histórica (Peso 20%)
        frec_global = (conteo_general[num] / total_sorteos) * 20

        puntajes[num] = prob_trans + factor_retraso + frec_global

    # Ordenar los animales de mayor a menor puntaje
    candidatos_ordenados = sorted(puntajes.items(), key=lambda x: x[1], reverse=True)

    # Seleccionar el Super Fijo (1ro) y los Secundarios (2do y 3ro)
    super_fijo_num = candidatos_ordenados[0][0]
    sec_1_num = candidatos_ordenados[1][0]
    sec_2_num = candidatos_ordenados[2][0]

    return jsonify({
        "total_registros_analizados": total_sorteos,
        "ultimo_resultado": {
            "numero": ultimo,
            "animal": ANIMALES.get(ultimo, "Desconocido")
        },
        "pronostico_cuantitativo": {
            "super_fijo": {
                "numero": super_fijo_num,
                "animal": ANIMALES.get(super_fijo_num, "Desconocido"),
                "score": round(candidatos_ordenados[0][1], 2)
            },
            "secundarios_tripleta": [
                {"numero": sec_1_num, "animal": ANIMALES.get(sec_1_num, "Desconocido"), "score": round(candidatos_ordenados[1][1], 2)},
                {"numero": sec_2_num, "animal": ANIMALES.get(sec_2_num, "Desconocido"), "score": round(candidatos_ordenados[2][1], 2)}
            ]
        }
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
