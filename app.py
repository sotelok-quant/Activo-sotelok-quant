from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
import random

app = Flask(__name__)

DB_NAME = "lottery.db"

# Lista de animales de la lotería (ejemplo tradicional venezolano)
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
def prediccion_markov():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT numero FROM resultados ORDER BY id ASC")
    filas = cursor.fetchall()
    conn.close()

    if len(filas) < 2:
        return jsonify({"error": "Se necesitan al menos 2 resultados registrados para calcular la matriz de Markov."}), 400

    secuencia = [row[0] for row in filas]
    ultimo = secuencia[-1]

    # Motor simplificado de Markov basado en transiciones históricas
    transiciones = {}
    for i in range(len(secuencia) - 1):
        actual = secuencia[i]
        siguiente = secuencia[i+1]
        if actual not in transiciones:
            transiciones[actual] = []
        transiciones[actual].append(siguiente)

    # Si el último número tiene historial de transición, elegimos los más frecuentes
    candidatos = transiciones.get(ultimo, list(ANIMALES.keys()))
    
    super_fijo = random.choice(candidatos)
    secundario_1 = random.choice(list(ANIMALES.keys()))
    secundario_2 = random.choice(list(ANIMALES.keys()))

    return jsonify({
        "ultimo_resultado": {
            "numero": ultimo,
            "animal": ANIMALES.get(ultimo, "Desconocido")
        },
        "pronostico": {
            "super_fijo": {
                "numero": super_fijo,
                "animal": ANIMALES.get(super_fijo, "Desconocido")
            },
            "secundarios_tripleta": [
                {"numero": secundario_1, "animal": ANIMALES.get(secundario_1, "Desconocido")},
                {"numero": secundario_2, "animal": ANIMALES.get(secundario_2, "Desconocido")}
            ]
        }
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
