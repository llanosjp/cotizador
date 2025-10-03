from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
import pandas as pd
import time
import os
import requests
from datetime import datetime
from threading import Thread
import uuid

app = Flask(__name__)
app.secret_key = 'dni-verification-platform-2025'
CORS(app)

# Directorio para archivos temporales
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RESULTS_FOLDER = os.path.join(BASE_DIR, "results")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Almacén de progreso en memoria (en producción usar Redis o DB)
progress_store = {}

# === Configuración API externa (Azure Logic Apps) ===
API_URL = "https://prod-03.brazilsouth.logic.azure.com/workflows/284301da7bf04dfcad6ffc4972f76169/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=_iprUF64z4RkmQzfw-s7-IPZ26p7xZyULK6429jGdAc"  
API_HEADERS = {"Content-Type": "application/json"}
API_USER = "API_SCP_INTELIGENCIA_COMERCIAL"
API_PASS = "1d$4F5f^4G&9h*8I(9h)0K!1l4M+3n4O=5p7r[8S]6t~0V="

# Función para llamar a la API real
def verificar_dni_api(dni: str):
    """Llama a la API externa de Azure Logic Apps"""
    payload = {
        "USUARIO": API_USER,
        "CONTRASENA_USUARIO": API_PASS,
        "TIPO_DOCUMENTO": "1",   # 1 = DNI
        "NRO_DOCUMENTO": dni
    }

    try:
        response = requests.post(API_URL, headers=API_HEADERS, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            # Aseguramos formato uniforme
            return {
                "Resultado": data.get("Resultado", "SIN_RESPUESTA"),
                "Detalle": data
            }
        else:
            return {"Resultado": "ERROR", "Detalle": response.text}
    except Exception as e:
        return {"Resultado": "ERROR", "Detalle": str(e)}

# Procesamiento en segundo plano
def procesar_archivo_bg(task_id, filepath):
    """Procesa archivo Excel en background con actualización de progreso"""
    try:
        # Leer archivo Excel
        df = pd.read_excel(filepath)

        # Validar columna DNI
        if 'DNI' not in df.columns:
            progress_store[task_id] = {
                'status': 'error',
                'message': 'La columna "DNI" no existe en el archivo',
                'progress': 0
            }
            return

        total = len(df)
        resultados = []

        # Procesar cada DNI
        for index, row in df.iterrows():
            dni = str(row['DNI']).strip()

            # Llamar a la API real
            api_response = verificar_dni_api(dni)

            resultados.append({
                'DNI': dni,
                'Resultado': api_response['Resultado']
            })

            # Actualizar progreso
            progreso = int(((index + 1) / total) * 100)
            progress_store[task_id] = {
                'status': 'processing',
                'progress': progreso,
                'processed': index + 1,
                'total': total
            }

        # Guardar resultados
        df_resultados = pd.DataFrame(resultados)
        result_filename = f'resultado_{task_id}.xlsx'
        result_path = os.path.join(RESULTS_FOLDER, result_filename)
        df_resultados.to_excel(result_path, index=False)

        # Marcar como completado
        progress_store[task_id] = {
            'status': 'completed',
            'progress': 100,
            'processed': total,
            'total': total,
            'result_file': result_filename,
            'resultados': resultados
        }

    except Exception as e:
        progress_store[task_id] = {
            'status': 'error',
            'message': str(e),
            'progress': 0
        }

# =======================
#        Rutas
# =======================

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/buscar')
def buscar():
    return render_template('buscar.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Recibe archivo y lanza procesamiento en background"""
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Archivo sin nombre'}), 400

    if not file.filename.endswith(('.xls', '.xlsx')):
        return jsonify({'error': 'Solo se permiten archivos Excel (.xls, .xlsx)'}), 400

    # Guardar archivo
    task_id = str(uuid.uuid4())
    filename = f'{task_id}_{file.filename}'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Inicializar progreso
    progress_store[task_id] = {
        'status': 'processing',
        'progress': 0,
        'processed': 0,
        'total': 0
    }

    # Lanzar procesamiento en background
    thread = Thread(target=procesar_archivo_bg, args=(task_id, filepath))
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def get_progress(task_id):
    """Endpoint para polling de progreso"""
    if task_id not in progress_store:
        return jsonify({'error': 'Tarea no encontrada'}), 404

    return jsonify(progress_store[task_id])

@app.route('/resultados/<task_id>')
def resultados(task_id):
    """Página de visualización de resultados"""
    if task_id not in progress_store:
        return render_template('resultados.html', error='Tarea no encontrada')

    task_data = progress_store[task_id]

    if task_data['status'] != 'completed':
        return render_template('resultados.html', error='Procesamiento no completado')

    return render_template('resultados.html',
                          task_id=task_id,
                          resultados=task_data['resultados'])

@app.route('/descargar/<task_id>')
def descargar(task_id):
    """Descarga archivo de resultados consolidado"""
    if task_id not in progress_store:
        return jsonify({'error': 'Tarea no encontrada'}), 404

    task_data = progress_store[task_id]

    if task_data['status'] != 'completed':
        return jsonify({'error': 'Procesamiento no completado'}), 400

    result_path = os.path.join(RESULTS_FOLDER, task_data['result_file'])

    return send_file(
        result_path,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'verificacion_dni_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/verificar-dni', methods=['POST'])
def verificar_dni_individual():
    """Endpoint para verificación individual de DNI"""
    data = request.get_json()

    if not data or 'dni' not in data:
        return jsonify({'error': 'DNI no proporcionado'}), 400

    dni = str(data['dni']).strip()

    if not dni:
        return jsonify({'error': 'DNI inválido'}), 400

    # Llamar a API real
    resultado = verificar_dni_api(dni)

    return jsonify({
        'DNI': dni,
        'Resultado': resultado['Resultado'],
        'Detalle': resultado.get("Detalle", {})
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
