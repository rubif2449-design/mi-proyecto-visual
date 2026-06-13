import sqlite3
import json
from datetime import datetime, timedelta
from tabulate import tabulate
import os

DB_PATH = 'thermal_monitoring.db'

def connect_db():
    """Conectar a la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def print_table(title, rows, headers):
    """Imprime una tabla formateada"""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}")
    if rows:
        print(tabulate(rows, headers=headers, tablefmt="grid", showindex=True))
    else:
        print(" No hay datos")

def listar_animales():
    """Listar todos los animales"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, species, breed, age_months, weight_kg, location, status FROM animals ORDER BY created_at DESC')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    headers = ["ID", "Nombre", "Especie", "Raza", "Edad (meses)", "Peso (kg)", "Ubicación", "Estado"]
    data = [[r['id'], r['name'], r['species'], r['breed'], r['age_months'], r['weight_kg'], r['location'], r['status']] for r in rows]
    
    print_table("ANIMALES REGISTRADOS", data, headers)
    return len(rows)

def listar_registros(animal_id=None, limit=50):
    """Listar registros térmicos"""
    conn = connect_db()
    cursor = conn.cursor()
    
    if animal_id:
        cursor.execute('''
            SELECT tr.id, a.name, tr.avg_temp, tr.max_temp, tr.min_temp, 
                   tr.stress_level, tr.is_stressed, tr.created_at
            FROM thermal_records tr
            JOIN animals a ON tr.animal_id = a.id
            WHERE tr.animal_id = ? 
            ORDER BY tr.created_at DESC LIMIT ?
        ''', (animal_id, limit))
        title = f"REGISTROS TÉRMICOS - Animal {animal_id}"
    else:
        cursor.execute('''
            SELECT tr.id, a.name, tr.avg_temp, tr.max_temp, tr.min_temp,
                   tr.stress_level, tr.is_stressed, tr.created_at
            FROM thermal_records tr
            JOIN animals a ON tr.animal_id = a.id
            ORDER BY tr.created_at DESC LIMIT ?
        ''', (limit,))
        title = "REGISTROS TÉRMICOS"
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    headers = ["ID", "Animal", "Temp. Prom.", "Temp. Máx.", "Temp. Mín.", "Estrés (%)", "Estresado", "Fecha"]
    data = [[r['id'], r['name'], f"{r['avg_temp']:.1f}°C", f"{r['max_temp']:.1f}°C", 
             f"{r['min_temp']:.1f}°C", f"{r['stress_level']:.1f}", "Sí" if r['is_stressed'] else "No", 
             r['created_at']] for r in rows]
    
    print_table(title, data, headers)
    return len(rows)

def listar_alertas(unresolved_only=False):
    """Listar alertas"""
    conn = connect_db()
    cursor = conn.cursor()
    
    if unresolved_only:
        cursor.execute('''
            SELECT a.id, an.name, a.alert_type, a.message, a.severity, 
                   a.is_resolved, a.created_at
            FROM alerts a
            JOIN animals an ON a.animal_id = an.id
            WHERE a.is_resolved = 0
            ORDER BY a.created_at DESC
        ''')
        title = "ALERTAS SIN RESOLVER"
    else:
        cursor.execute('''
            SELECT a.id, an.name, a.alert_type, a.message, a.severity, 
                   a.is_resolved, a.created_at
            FROM alerts a
            JOIN animals an ON a.animal_id = an.id
            ORDER BY a.created_at DESC LIMIT 50
        ''')
        title = "ALERTAS RECIENTES"
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    headers = ["ID", "Animal", "Tipo", "Mensaje", "Severidad", "Resuelta", "Fecha"]
    data = [[r['id'], r['name'], r['alert_type'], r['message'][:30], r['severity'],
             "Sí" if r['is_resolved'] else "No", r['created_at']] for r in rows]
    
    print_table(title, data, headers)
    return len(rows)

def estadisticas_animal(animal_id):
    """Mostrar estadísticas de un animal"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Datos del animal
    cursor.execute('SELECT * FROM animals WHERE id = ?', (animal_id,))
    animal = cursor.fetchone()
    
    if not animal:
        print(f" Animal {animal_id} no encontrado")
        conn.close()
        return
    
    # Registros
    cursor.execute('''
        SELECT COUNT(*) as count, AVG(avg_temp) as avg, MAX(max_temp) as max_val, MIN(min_temp) as min_val,
               AVG(stress_level) as stress_avg
        FROM thermal_records WHERE animal_id = ?
    ''', (animal_id,))
    stats = dict(cursor.fetchone())
    
    # Alertas
    cursor.execute('''
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) as unresolved
        FROM alerts WHERE animal_id = ?
    ''', (animal_id,))
    alerts = dict(cursor.fetchone())
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"📈 ESTADÍSTICAS - {animal['name']}")
    print(f"{'='*80}")
    print(f"\n Información del Animal:")
    print(f"   ID: {animal['id']}")
    print(f"   Nombre: {animal['name']}")
    print(f"   Especie: {animal['species']}")
    print(f"   Raza: {animal['breed']}")
    print(f"   Edad: {animal['age_months']} meses")
    print(f"   Peso: {animal['weight_kg']} kg")
    print(f"   Ubicación: {animal['location']}")
    print(f"   Estado: {animal['status']}")
    
    if stats['count'] and stats['count'] > 0:
        print(f"\n Estadísticas Térmicas:")
        print(f"   Registros: {stats['count']}")
        print(f"   Temp. Promedio: {stats['avg']:.1f}°C")
        print(f"   Temp. Máxima: {stats['max_val']:.1f}°C")
        print(f"   Temp. Mínima: {stats['min_val']:.1f}°C")
        print(f"   Estrés Promedio: {stats['stress_avg']:.1f}%")
    else:
        print(f"\n Sin registros térmicos aún")
    
    print(f"\n Alertas:")
    print(f"   Total: {alerts['total']}")
    print(f"   Sin Resolver: {alerts['unresolved']}")

def limpieza_base_datos():
    """Mostrar opciones de limpieza"""
    print(f"\n{'='*80}")
    print(f" LIMPIEZA DE BASE DE DATOS")
    print(f"{'='*80}")
    print(f"\nOpciones:")
    print(f"  1. Eliminar registros térmicos más antiguos de 30 días")
    print(f"  2. Eliminar alertas resueltas")
    print(f"  3. Resetear base de datos completamente")
    print(f"  0. Volver")
    
    choice = input("\nSelecciona una opción: ").strip()
    
    if choice == '1':
        conn = connect_db()
        cursor = conn.cursor()
        before_date = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute('DELETE FROM thermal_records WHERE created_at < ?', (before_date,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        print(f" {deleted} registros antiguos eliminados")
    
    elif choice == '2':
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM alerts WHERE is_resolved = 1')
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        print(f" {deleted} alertas resueltas eliminadas")
    
    elif choice == '3':
        if input(" ¿Estás seguro? Esto eliminará TODO (s/n): ").lower() == 's':
            os.remove(DB_PATH)
            print(" Base de datos reseteada")

def exportar_datos_csv(animal_id=None):
    """Exportar datos a CSV"""
    import csv
    
    conn = connect_db()
    cursor = conn.cursor()
    
    if animal_id:
        cursor.execute('''
            SELECT tr.id, a.name, tr.avg_temp, tr.max_temp, tr.min_temp,
                   tr.stress_level, tr.is_stressed, tr.created_at
            FROM thermal_records tr
            JOIN animals a ON tr.animal_id = a.id
            WHERE tr.animal_id = ?
            ORDER BY tr.created_at
        ''', (animal_id,))
        filename = f'animal_{animal_id}_records.csv'
    else:
        cursor.execute('''
            SELECT tr.id, a.name, tr.avg_temp, tr.max_temp, tr.min_temp,
                   tr.stress_level, tr.is_stressed, tr.created_at
            FROM thermal_records tr
            JOIN animals a ON tr.animal_id = a.id
            ORDER BY tr.created_at
        ''')
        filename = 'all_thermal_records.csv'
    
    rows = cursor.fetchall()
    conn.close()
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Animal', 'Temp. Prom.', 'Temp. Máx.', 'Temp. Mín.', 'Estrés (%)', 'Estresado', 'Fecha'])
        for row in rows:
            writer.writerow(row)
    
    print(f" Datos exportados a {filename}")

def menu_principal():
    """Menú interactivo"""
    while True:
        print(f"\n{'='*80}")
        print(f" UTILIDADES DE BASE DE DATOS")
        print(f"{'='*80}")
        print(f"\nOpciones:")
        print(f"  1. Listar todos los animales")
        print(f"  2. Listar registros térmicos")
        print(f"  3. Listar alertas")
        print(f"  4. Ver estadísticas de un animal")
        print(f"  5. Exportar datos a CSV")
        print(f"  6. Limpieza de base de datos")
        print(f"  0. Salir")
        
        choice = input("\nSelecciona una opción: ").strip()
        
        if choice == '1':
            listar_animales()
        
        elif choice == '2':
            try:
                animal_id = input("Ingresa ID del animal (Enter para todos): ").strip()
                animal_id = int(animal_id) if animal_id else None
                listar_registros(animal_id)
            except ValueError:
                print(" ID inválido")
        
        elif choice == '3':
            unresolved = input("¿Solo sin resolver? (s/n): ").lower() == 's'
            listar_alertas(unresolved)
        
        elif choice == '4':
            try:
                animal_id = int(input("Ingresa ID del animal: ").strip())
                estadisticas_animal(animal_id)
            except ValueError:
                print(" ID inválido")
        
        elif choice == '5':
            try:
                animal_id = input("Ingresa ID del animal (Enter para todos): ").strip()
                animal_id = int(animal_id) if animal_id else None
                exportar_datos_csv(animal_id)
            except ValueError:
                print(" ID inválido")
        
        elif choice == '6':
            limpieza_base_datos()
        
        elif choice == '0':
            print("\n¡Hasta luego! ")
            break
        
        else:
            print(" Opción inválida")

if __name__ == "__main__":
    print("""
    
          UTILIDADES DE BASE DE DATOS - MONITOREO TÉRMICO      
    
    """)
    
    if not os.path.exists(DB_PATH):
        print(f" Base de datos no encontrada: {DB_PATH}")
        print("Asegúrate de haber ejecutado: python app.py")
    else:
        try:
            menu_principal()
        except KeyboardInterrupt:
            print("\n\n¡Hasta luego! ")
        except Exception as e:
            print(f"\n Error: {str(e)}")
            import traceback
            traceback.print_exc()
