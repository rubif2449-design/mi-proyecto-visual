"""
Script de prueba para los endpoints CRUD del backend
Ejecutar con: python test_api.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

def print_response(response, title=""):
    """Imprime la respuesta de forma legible"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text)

# ==================== PRUEBAS DE ANIMALES ====================

def test_animals():
    print("\n\n🐷 PRUEBAS DE OPERACIONES CON ANIMALES")
    
    # 1. AGREGAR animales
    print("\n1️⃣ AGREGAR ANIMALES...")
    animals_data = [
        {
            "name": "Cerdo-001",
            "species": "Sus scrofa",
            "breed": "Landrace",
            "age_months": 12,
            "weight_kg": 120.5,
            "location": "Corral A"
        },
        {
            "name": "Cerdo-002",
            "species": "Sus scrofa",
            "breed": "Duroc",
            "age_months": 8,
            "weight_kg": 95.3,
            "location": "Corral B"
        }
    ]
    
    created_ids = []
    for animal in animals_data:
        response = requests.post(f"{BASE_URL}/api/animals", json=animal)
        print_response(response, f"Agregar: {animal['name']}")
        if response.status_code == 201:
            created_ids.append(response.json()['animal_id'])
    
    # 2. LISTAR todos los animales
    print("\n2️⃣ LISTAR TODOS LOS ANIMALES...")
    response = requests.get(f"{BASE_URL}/api/animals")
    print_response(response, "Listar Animales")
    
    # 3. LEER un animal específico
    if created_ids:
        print(f"\n3️⃣ LEER ANIMAL ESPECÍFICO (ID: {created_ids[0]})...")
        response = requests.get(f"{BASE_URL}/api/animals/{created_ids[0]}")
        print_response(response, f"Leer Animal {created_ids[0]}")
    
    # 4. MODIFICAR un animal
    if created_ids:
        print(f"\n4️⃣ MODIFICAR ANIMAL (ID: {created_ids[0]})...")
        update_data = {
            "age_months": 13,
            "weight_kg": 125.0,
            "location": "Corral C"
        }
        response = requests.put(f"{BASE_URL}/api/animals/{created_ids[0]}", json=update_data)
        print_response(response, f"Modificar Animal {created_ids[0]}")
    
    # 5. LEER el animal modificado
    if created_ids:
        print(f"\n5️⃣ VERIFICAR CAMBIOS...")
        response = requests.get(f"{BASE_URL}/api/animals/{created_ids[0]}")
        print_response(response, "Animal Modificado")
    
    return created_ids

# ==================== PRUEBAS DE REGISTROS TÉRMICOS ====================

def test_records(animal_ids):
    print("\n\n🌡️ PRUEBAS DE OPERACIONES CON REGISTROS TÉRMICOS")
    
    if not animal_ids:
        print("⚠️ No hay animales para crear registros")
        return []
    
    # 1. AGREGAR registros
    print("\n1️⃣ AGREGAR REGISTROS TÉRMICOS...")
    records_data = [
        {
            "animal_id": animal_ids[0],
            "avg_temp": 38.5,
            "max_temp": 39.2,
            "min_temp": 37.8,
            "stress_level": 45.2,
            "is_stressed": 0,
            "zones_data": {"head": 39.1, "body": 38.5, "legs": 37.9}
        },
        {
            "animal_id": animal_ids[0],
            "avg_temp": 38.7,
            "max_temp": 39.5,
            "min_temp": 37.9,
            "stress_level": 52.1,
            "is_stressed": 0,
            "zones_data": {"head": 39.3, "body": 38.7, "legs": 38.0}
        }
    ]
    
    record_ids = []
    for record in records_data:
        response = requests.post(f"{BASE_URL}/api/records", json=record)
        print_response(response, f"Agregar Registro - Temp: {record['avg_temp']}°C")
        if response.status_code == 201:
            record_ids.append(response.json()['record_id'])
    
    # 2. LISTAR registros
    print("\n2️⃣ LISTAR REGISTROS...")
    response = requests.get(f"{BASE_URL}/api/records?animal_id={animal_ids[0]}&limit=10")
    print_response(response, f"Registros del Animal {animal_ids[0]}")
    
    # 3. LEER un registro específico
    if record_ids:
        print(f"\n3️⃣ LEER REGISTRO ESPECÍFICO (ID: {record_ids[0]})...")
        response = requests.get(f"{BASE_URL}/api/records/{record_ids[0]}")
        print_response(response, f"Leer Registro {record_ids[0]}")
    
    # 4. MODIFICAR un registro
    if record_ids:
        print(f"\n4️⃣ MODIFICAR REGISTRO (ID: {record_ids[0]})...")
        update_data = {
            "stress_level": 55.0,
            "is_stressed": 1
        }
        response = requests.put(f"{BASE_URL}/api/records/{record_ids[0]}", json=update_data)
        print_response(response, f"Modificar Registro {record_ids[0]}")
    
    return record_ids

# ==================== PRUEBAS DE ALERTAS ====================

def test_alerts(animal_ids):
    print("\n\n⚠️ PRUEBAS DE OPERACIONES CON ALERTAS")
    
    if not animal_ids:
        print("⚠️ No hay animales para crear alertas")
        return []
    
    # 1. AGREGAR alertas
    print("\n1️⃣ AGREGAR ALERTAS...")
    alerts_data = [
        {
            "animal_id": animal_ids[0],
            "alert_type": "temperature",
            "message": "Temperatura elevada detectada: 39.5°C",
            "severity": "warning"
        },
        {
            "animal_id": animal_ids[0],
            "alert_type": "stress",
            "message": "Nivel de estrés alto: 55%",
            "severity": "danger"
        }
    ]
    
    alert_ids = []
    for alert in alerts_data:
        response = requests.post(f"{BASE_URL}/api/alerts", json=alert)
        print_response(response, f"Agregar Alerta: {alert['message']}")
        if response.status_code == 201:
            alert_ids.append(response.json()['alert_id'])
    
    # 2. LISTAR alertas sin resolver
    print("\n2️⃣ LISTAR ALERTAS SIN RESOLVER...")
    response = requests.get(f"{BASE_URL}/api/alerts?unresolved_only=true&limit=10")
    print_response(response, "Alertas Activas")
    
    # 3. LEER una alerta específica
    if alert_ids:
        print(f"\n3️⃣ LEER ALERTA ESPECÍFICA (ID: {alert_ids[0]})...")
        response = requests.get(f"{BASE_URL}/api/alerts/{alert_ids[0]}")
        print_response(response, f"Leer Alerta {alert_ids[0]}")
    
    # 4. MODIFICAR una alerta (marcar como resuelta)
    if alert_ids:
        print(f"\n4️⃣ MARCAR ALERTA COMO RESUELTA (ID: {alert_ids[0]})...")
        update_data = {
            "is_resolved": 1,
            "severity": "info"
        }
        response = requests.put(f"{BASE_URL}/api/alerts/{alert_ids[0]}", json=update_data)
        print_response(response, f"Resolver Alerta {alert_ids[0]}")
    
    # 5. LISTAR alertas nuevamente
    print("\n5️⃣ VERIFICAR ALERTAS DESPUÉS DE RESOLVER...")
    response = requests.get(f"{BASE_URL}/api/alerts?unresolved_only=true")
    print_response(response, "Alertas Sin Resolver Restantes")
    
    return alert_ids

# ==================== ELIMINAR RECURSOS ====================

def test_delete(animal_ids, record_ids, alert_ids):
    print("\n\n🗑️ PRUEBAS DE ELIMINACIÓN")
    
    # Eliminar una alerta
    if alert_ids:
        print(f"\n1️⃣ ELIMINAR ALERTA (ID: {alert_ids[-1]})...")
        response = requests.delete(f"{BASE_URL}/api/alerts/{alert_ids[-1]}")
        print_response(response, f"Eliminar Alerta {alert_ids[-1]}")
    
    # Eliminar un registro
    if record_ids:
        print(f"\n2️⃣ ELIMINAR REGISTRO (ID: {record_ids[-1]})...")
        response = requests.delete(f"{BASE_URL}/api/records/{record_ids[-1]}")
        print_response(response, f"Eliminar Registro {record_ids[-1]}")
    
    # Eliminar un animal
    if animal_ids:
        print(f"\n3️⃣ ELIMINAR ANIMAL (ID: {animal_ids[-1]})...")
        response = requests.delete(f"{BASE_URL}/api/animals/{animal_ids[-1]}")
        print_response(response, f"Eliminar Animal {animal_ids[-1]}")
    
    # Verificar que fue eliminado
    if animal_ids:
        print(f"\n4️⃣ VERIFICAR ELIMINACIÓN...")
        response = requests.get(f"{BASE_URL}/api/animals/{animal_ids[-1]}")
        print(f"Status: {response.status_code}")
        print("Animal debería estar marcado como 'deleted'")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# ==================== FUNCIÓN PRINCIPAL ====================

def main():
    print("""
    
    ╔════════════════════════════════════════════════════════════╗
    ║       PRUEBAS COMPLETAS DE API CRUD - MONITOREO TÉRMICO    ║
    ║                                                            ║
    ║  Asegúrate de que el servidor está corriendo:             ║
    ║  python app.py                                            ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Pruebas
        animal_ids = test_animals()
        record_ids = test_records(animal_ids)
        alert_ids = test_alerts(animal_ids)
        test_delete(animal_ids, record_ids, alert_ids)
        
        print(f"\n\n✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se puede conectar al servidor")
        print("Asegúrate de ejecutar: python app.py")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
