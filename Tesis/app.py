from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
import numpy as np
from collections import deque
import sqlite3

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = 'thermal_monitoring.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            species TEXT NOT NULL,
            breed TEXT,
            age_months INTEGER,
            weight_kg REAL,
            location TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thermal_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            avg_temp REAL,
            max_temp REAL,
            min_temp REAL,
            stress_level REAL,
            is_stressed INTEGER,
            zones_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (animal_id) REFERENCES animals(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            alert_type TEXT,
            message TEXT,
            severity TEXT,
            is_resolved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (animal_id) REFERENCES animals(id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

camera_data = {
    'current_temp': 37.5,
    'avg_temp': 37.5,
    'max_temp': 37.5,
    'min_temp': 37.5,
    'thermal_image': None,
    'timestamp': None,
    'stress_level': 0,
    'zones': {}
}

# Historial de datos
data_history = deque(maxlen=100)
stress_history = deque(maxlen=100)

system_state = {
    'connected': False,
    'monitoring': True,
    'alerts_enabled': True,
    'stress_threshold': 70,
    'notifications': []
}

class StressDetector:
    def __init__(self):
        self.temp_history = deque(maxlen=10)
        self.stress_level = 0
        
    def detect_stress(self, thermal_data):
        avg_temp = thermal_data.get('avg_temp', 37.5)
        max_temp = thermal_data.get('max_temp', 37.5)
        min_temp = thermal_data.get('min_temp', 37.5)
        
        self.temp_history.append(avg_temp)
        
        stress_factors = {}
        
        if avg_temp > 39.5:
            stress_factors['high_temp'] = (avg_temp - 39.5) * 20
        else:
            stress_factors['high_temp'] = 0
            
        temp_range = max_temp - min_temp
        if temp_range > 3:
            stress_factors['temp_variance'] = min(temp_range * 15, 100)
        else:
            stress_factors['temp_variance'] = 0
            
        if len(self.temp_history) >= 3:
            recent_trend = self.temp_history[-1] - self.temp_history[-3]
            if recent_trend > 0.5:
                stress_factors['rising_trend'] = min(recent_trend * 30, 100)
            else:
                stress_factors['rising_trend'] = 0
        else:
            stress_factors['rising_trend'] = 0
            
        zones = thermal_data.get('zones', {})
        hot_zones = sum(1 for z in zones.values() if z.get('avg_temp', 0) > 40.5)
        if hot_zones > 2:
            stress_factors['hot_zones'] = hot_zones * 25
        else:
            stress_factors['hot_zones'] = 0
        
        weights = {
            'high_temp': 0.35,
            'temp_variance': 0.25,
            'rising_trend': 0.25,
            'hot_zones': 0.15
        }
        
        self.stress_level = sum(
            stress_factors.get(factor, 0) * weights.get(factor, 0)
            for factor in weights
        )
        self.stress_level = min(100, max(0, self.stress_level))
        
        return {
            'stress_level': self.stress_level,
            'factors': stress_factors,
            'is_stressed': self.stress_level > system_state['stress_threshold']
        }

stress_detector = StressDetector()

def send_notification(message, alert_type='info'):
    notification = {
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'type': alert_type
    }
    system_state['notifications'].append(notification)
    
    if len(system_state['notifications']) > 50:
        system_state['notifications'].pop(0)
    
    try:
        socketio.emit('notification', notification)
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"[{alert_type.upper()}] {message}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Obtiene estado actual del sistema"""
    return jsonify({
        'system_state': system_state,
        'camera_data': {
            'current_temp': camera_data['current_temp'],
            'avg_temp': camera_data['avg_temp'],
            'max_temp': camera_data['max_temp'],
            'min_temp': camera_data['min_temp'],
            'stress_level': camera_data['stress_level'],
            'timestamp': camera_data['timestamp']
        },
        'recent_history': list(data_history)[-20:]
    })

@app.route('/api/thermal-data', methods=['POST'])
def receive_thermal_data():
    """
    Recibe datos de la cámara térmica ESP32-S3
    
    Formato esperado:
    {
        'avg_temp': float,
        'max_temp': float,
        'min_temp': float,
        'zones': {
            'head': {'avg_temp': float, 'max_temp': float},
            'body': {'avg_temp': float, 'max_temp': float},
            'legs': {'avg_temp': float, 'max_temp': float}
        },
        'frame_data': base64_image (opcional)
    }
    """
    try:
        data = request.json
        
        # Actualizar datos de cámara
        camera_data['current_temp'] = data.get('avg_temp', 37.5)
        camera_data['avg_temp'] = data.get('avg_temp', 37.5)
        camera_data['max_temp'] = data.get('max_temp', 37.5)
        camera_data['min_temp'] = data.get('min_temp', 37.5)
        camera_data['zones'] = data.get('zones', {})
        camera_data['timestamp'] = datetime.now().isoformat()
        
        # Detectar estrés
        stress_result = stress_detector.detect_stress(camera_data)
        camera_data['stress_level'] = stress_result['stress_level']
        
        # Almacenar en historial
        history_entry = {
            'timestamp': camera_data['timestamp'],
            'avg_temp': camera_data['avg_temp'],
            'stress_level': camera_data['stress_level'],
            'is_stressed': stress_result['is_stressed']
        }
        data_history.append(history_entry)
        stress_history.append(stress_result['stress_level'])
        
        # Generar alertas si hay estrés
        if stress_result['is_stressed']:
            stress_msg = f"⚠️ Estrés detectado: {camera_data['stress_level']:.1f}% - Temp: {camera_data['avg_temp']:.1f}°C"
            send_notification(stress_msg, 'danger')
        
        # Alertas por temperatura crítica
        if camera_data['max_temp'] > 41.5:
            temp_msg = f"🚨 TEMPERATURA CRÍTICA: {camera_data['max_temp']:.1f}°C detectada"
            send_notification(temp_msg, 'danger')
        elif camera_data['avg_temp'] > 40.5:
            temp_msg = f"⚠️ Temperatura elevada: {camera_data['avg_temp']:.1f}°C"
            send_notification(temp_msg, 'warning')
        
        # Emitir actualización a clientes WebSocket
        try:
            socketio.emit('thermal_update', {
                'camera_data': camera_data,
                'stress_result': stress_result,
                'history': list(data_history)[-20:]
            })
        except Exception as e:
            print(f"Error emitiendo WebSocket: {e}")
        
        system_state['connected'] = True
        
        return jsonify({
            'success': True,
            'stress_level': camera_data['stress_level'],
            'is_stressed': stress_result['is_stressed']
        })
        
    except Exception as e:
        print(f"Error procesando datos térmicos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/configure', methods=['POST'])
def configure_system():
    """Configura parámetros del sistema"""
    config = request.json
    
    if 'stress_threshold' in config:
        system_state['stress_threshold'] = config['stress_threshold']
    
    if 'alerts_enabled' in config:
        system_state['alerts_enabled'] = config['alerts_enabled']
    
    if 'monitoring' in config:
        system_state['monitoring'] = config['monitoring']
    
    try:
        socketio.emit('system_config', system_state)
    except Exception as e:
        print(f"Error emitiendo configuración: {e}")
    
    return jsonify({'success': True, 'system_state': system_state})

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    limit = request.args.get('limit', 20, type=int)
    return jsonify({
        'notifications': system_state['notifications'][-limit:],
        'total': len(system_state['notifications'])
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    limit = request.args.get('limit', 50, type=int)
    return jsonify({
        'history': list(data_history)[-limit:],
        'stress_history': list(stress_history)[-limit:]
    })

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'data': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('request_update')
def handle_update_request():
    emit('thermal_update', {
        'camera_data': camera_data,
        'stress_level': camera_data['stress_level']
    })

@app.route('/api/animals', methods=['GET'])
def list_animals():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM animals ORDER BY created_at DESC')
        animals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'data': animals})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/animals/<int:animal_id>', methods=['GET'])
def get_animal(animal_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM animals WHERE id = ?', (animal_id,))
        animal = cursor.fetchone()
        conn.close()
        
        if not animal:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        return jsonify({'success': True, 'data': dict(animal)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/animals', methods=['POST'])
def create_animal():
    try:
        data = request.json
        required_fields = ['name', 'species']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing fields'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO animals (name, species, breed, age_months, weight_kg, location, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name'),
            data.get('species'),
            data.get('breed'),
            data.get('age_months'),
            data.get('weight_kg'),
            data.get('location'),
            data.get('status', 'active')
        ))
        conn.commit()
        animal_id = cursor.lastrowid
        conn.close()
        
        send_notification(f"Animal '{data.get('name')}' created", 'info')
        return jsonify({'success': True, 'animal_id': animal_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/animals/<int:animal_id>', methods=['PUT'])
def update_animal(animal_id):
    try:
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM animals WHERE id = ?', (animal_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        update_fields = []
        values = []
        for field in ['name', 'species', 'breed', 'age_months', 'weight_kg', 'location', 'status']:
            if field in data:
                update_fields.append(f'{field} = ?')
                values.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({'success': False, 'error': 'No fields to update'}), 400
        
        values.append(animal_id)
        query = f"UPDATE animals SET updated_at = CURRENT_TIMESTAMP, {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        
        send_notification(f"Animal {animal_id} updated", 'info')
        return jsonify({'success': True, 'message': 'Updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/animals/<int:animal_id>', methods=['DELETE'])
def delete_animal(animal_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM animals WHERE id = ?', (animal_id,))
        animal = cursor.fetchone()
        if not animal:
            conn.close()
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        animal_name = animal[0]
        cursor.execute('UPDATE animals SET status = ? WHERE id = ?', ('deleted', animal_id))
        conn.commit()
        conn.close()
        
        send_notification(f"Animal '{animal_name}' deleted", 'info')
        return jsonify({'success': True, 'message': 'Deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ==================== OPERACIONES CRUD PARA REGISTROS TÉRMICOS ====================

@app.route('/api/records', methods=['GET'])
def list_records():
    try:
        animal_id = request.args.get('animal_id', type=int)
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if animal_id:
            cursor.execute('''
                SELECT * FROM thermal_records 
                WHERE animal_id = ? 
                ORDER BY created_at DESC LIMIT ?
            ''', (animal_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM thermal_records 
                ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        
        records = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'data': records})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/records/<int:record_id>', methods=['GET'])
def get_record(record_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM thermal_records WHERE id = ?', (record_id,))
        record = cursor.fetchone()
        conn.close()
        
        if not record:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        return jsonify({'success': True, 'data': dict(record)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/records', methods=['POST'])
def create_record():
    try:
        data = request.json
        if 'animal_id' not in data or 'avg_temp' not in data:
            return jsonify({'success': False, 'error': 'Missing fields'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM animals WHERE id = ?', (data['animal_id'],))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        cursor.execute('''
            INSERT INTO thermal_records (animal_id, avg_temp, max_temp, min_temp, stress_level, is_stressed, zones_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['animal_id'],
            data['avg_temp'],
            data.get('max_temp'),
            data.get('min_temp'),
            data.get('stress_level'),
            data.get('is_stressed', 0),
            json.dumps(data.get('zones_data', {}))
        ))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'record_id': record_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/records/<int:record_id>', methods=['PUT'])
def update_record(record_id):
    try:
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM thermal_records WHERE id = ?', (record_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        update_fields = []
        values = []
        for field in ['avg_temp', 'max_temp', 'min_temp', 'stress_level', 'is_stressed']:
            if field in data:
                update_fields.append(f'{field} = ?')
                values.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({'success': False, 'error': 'No fields'}), 400
        
        values.append(record_id)
        query = f"UPDATE thermal_records SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Registro actualizado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    """Eliminar un registro"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar que el registro existe
        cursor.execute('SELECT id FROM thermal_records WHERE id = ?', (record_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Registro no encontrado'}), 404
        
        cursor.execute('DELETE FROM thermal_records WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Registro eliminado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ==================== OPERACIONES CRUD PARA ALERTAS ====================

@app.route('/api/alerts', methods=['GET'])
def list_alerts():
    """Listar alertas"""
    try:
        animal_id = request.args.get('animal_id', type=int)
        unresolved_only = request.args.get('unresolved_only', 'false').lower() == 'true'
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM alerts WHERE 1=1'
        params = []
        
        if animal_id:
            query += ' AND animal_id = ?'
            params.append(animal_id)
        
        if unresolved_only:
            query += ' AND is_resolved = 0'
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'data': alerts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/alerts/<int:alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Leer una alerta específica"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM alerts WHERE id = ?', (alert_id,))
        alert = cursor.fetchone()
        conn.close()
        
        if not alert:
            return jsonify({'success': False, 'error': 'Alerta no encontrada'}), 404
        return jsonify({'success': True, 'data': dict(alert)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """Agregar una nueva alerta"""
    try:
        data = request.json
        if 'animal_id' not in data or 'message' not in data:
            return jsonify({'success': False, 'error': 'Faltan campos requeridos'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (animal_id, alert_type, message, severity, is_resolved)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['animal_id'],
            data.get('alert_type', 'general'),
            data['message'],
            data.get('severity', 'info'),
            0
        ))
        conn.commit()
        alert_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'alert_id': alert_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/alerts/<int:alert_id>', methods=['PUT'])
def update_alert(alert_id):
    """Modificar una alerta (por ejemplo, marcar como resuelta)"""
    try:
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar que la alerta existe
        cursor.execute('SELECT id FROM alerts WHERE id = ?', (alert_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Alerta no encontrada'}), 404
        
        update_fields = []
        values = []
        
        if 'is_resolved' in data:
            update_fields.append('is_resolved = ?')
            values.append(data['is_resolved'])
            if data['is_resolved']:
                update_fields.append('resolved_at = CURRENT_TIMESTAMP')
        
        if 'severity' in data:
            update_fields.append('severity = ?')
            values.append(data['severity'])
        
        if not update_fields:
            conn.close()
            return jsonify({'success': False, 'error': 'No hay campos para actualizar'}), 400
        
        values.append(alert_id)
        query = f"UPDATE alerts SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Alerta actualizada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Eliminar una alerta"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar que la alerta existe
        cursor.execute('SELECT id FROM alerts WHERE id = ?', (alert_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Alerta no encontrada'}), 404
        
        cursor.execute('DELETE FROM alerts WHERE id = ?', (alert_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Alerta eliminada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    print("🌡️ Servidor de Monitoreo Térmico iniciado")
    print("Escuchando en http://localhost:5000")
    print("ESP32-S3 enviar datos a: http://localhost:5000/api/thermal-data")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
