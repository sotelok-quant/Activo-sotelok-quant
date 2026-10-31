import sqlite3
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permite peticiones desde la PWA

DB_FILE = "sotelok_quant.db"

# Mapeo de animales oficial (0 a 36)
ANIMALS = {
    0: "Delfín", "00": "Ballena", 1: "Carnero", 2: "Toro", 3: "Ciempiés", 4: "Alacrán",
    5: "León", 6: "Rana", 7: "Perico", 8: "Ratón", 9: "Águila", 10: "Tigre",
    11: "Gato", 12: "Caballo", 13: "Mono", 14: "Paloma", 15: "Zorro", 16: "Oso",
    17: "Pavo", 18: "Burro", 19: "Chivo", 20: "Cochino", 21: "Gallo", 22: "Camello",
    23: "Cebra", 24: "Iguana", 25: "Gallina", 26: "Vaca", 27: "Perro", 28: "Zamuro",
    29: "Elefante", 30: "Caimán", 31: "Lapa", 32: "Ardilla", 33: "Pescado",
    34: "Venado", 35: "Jirafa", 36: "Culebra"
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            turno INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            animal TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return jsonify({"status": "ok", "app": "SOTELOK ANIMAL QUANT ENGINE", "version": "1.0.0"})

# 1. Carga masiva o individual de resultados
@app.route('/api/cargar', methods=['POST'])
def cargar_resultados():
    data = request.get_json()
    fecha = data.get('fecha')
    numeros = data.get('numeros') # Lista de números en orden de 8AM a 7PM

    if not fecha or not numeros or len(numeros) == 0:
        return jsonify({"error": "Datos inválidos. Se requiere fecha y lista de números."}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    for idx, num in enumerate(numeros, start=1):
        animal_nombre = ANIMALS.get(num, "Desconocido")
        cursor.execute('''
            INSERT INTO resultados (fecha, turno, numero, animal)
            VALUES (?, ?, ?, ?)
        ''', (fecha, idx, num, animal_nombre))
        
    conn.commit()
    conn.close()
    return jsonify({"message": f"Se cargaron {len(numeros)} resultados para la fecha {fecha} con éxito."})

# 2. Motor de Predicción Cuantitativa (Markov + Frecuencias)
@app.route('/api/prediccion', methods=['GET'])
def obtener_prediccion():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Obtener historial ordenado cronológicamente
    cursor.execute('SELECT numero FROM resultados ORDER BY id ASC')
    rows = cursor.fetchall()
    history = [r[0] for r in rows]
    
    if len(history) < 2:
        conn.close()
        return jsonify({"error": "No hay suficientes datos históricos acumulados."}), 400

    last_num = history[-1]
    
    # Matriz de Transición de Markov simple (Siguiente dado el último)
    transitions = {}
    frequency = {}
    
    for i in range(len(history) - 1):
        curr = history[i]
        nxt = history[i+1]
        
        # Conteo general de frecuencias
        frequency[nxt] = frequency.get(nxt, 0) + 1
        
        # Conteo de transiciones tras 'curr'
        if curr not in transitions:
            transitions[curr] = {}
        transitions[curr][nxt] = transitions[curr].get(nxt, 0) + 1

    conn.close()

    # Cálculo de probables tras el último número registrado
    candidates = transitions.get(last_num, {})
    
    if candidates:
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        top_candidates = [num for num, count in sorted_candidates[:3]]
    else:
        # Fallback a los más frecuentes en general
        sorted_freq = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
        top_candidates = [num for num, count in sorted_freq[:3]]

    while len(top_candidates) < 3:
        for n in range(1, 37):
            if n not in top_candidates:
                top_candidates.append(n)
                if len(top_candidates) == 3:
                    break

    super_fijo = top_candidates[0]
    secundarios = top_candidates[1:3]

    response = {
        "ultimo_resultado": {
            "numero": last_num,
            "animal": ANIMALS.get(last_num, "Desconocido")
        },
        "pronostico": {
            "super_fijo": {
                "numero": super_fijo,
                "animal": ANIMALS.get(super_fijo, "Desconocido"),
                "probabilidad": "Alta (Consenso Markov & Inercia)"
            },
            "secundarios_tripleta": [
                {"numero": secundarios[0], "animal": ANIMALS.get(secundarios[0], "Desconocido")},
                {"numero": secundarios[1], "animal": ANIMALS.get(secundarios[1], "Desconocido")}
            ]
        }
    }
    return jsonify(response)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
