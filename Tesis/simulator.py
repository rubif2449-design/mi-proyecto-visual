import requests
import json
import time
import random
from datetime import datetime

SERVER_URL = "http://localhost:5000/api/thermal-data"

class ThermalSimulator:
    def __init__(self):
        self.base_temp = 37.5
        self.ambient = 22.0
        self.stress_trigger = False
        self.trend = 0
        
    def generate_realistic_data(self):        
        self.trend += random.uniform(-0.05, 0.1)
        self.trend = max(-0.5, min(0.5, self.trend))  # Limitar tendencia
        
        avg_temp = self.base_temp + self.trend + random.gauss(0, 0.2)
        avg_temp = max(35, min(42, avg_temp))
        
        max_temp = avg_temp + random.uniform(0, 3)
    
        min_temp = avg_temp - random.uniform(0, 2)
        
        zones = {
            'head': {
                'avg_temp': avg_temp - 0.5 + random.gauss(0, 0.3),
                'max_temp': max_temp - 0.5
            },
            'body': {
                'avg_temp': avg_temp + random.gauss(0, 0.3),
                'max_temp': max_temp
            },
            'legs': {
                'avg_temp': avg_temp - 1.0 + random.gauss(0, 0.3),
                'max_temp': max_temp - 1.0
            }
        }
        
        return {
            'avg_temp': round(avg_temp, 2),
            'max_temp': round(max_temp, 2),
            'min_temp': round(min_temp, 2),
            'zones': zones
        }
    
    def simulate_normal(self):
        self.base_temp = 37.5
        self.trend = 0
        
    def simulate_elevated(self):
        self.base_temp = 39.5
        self.trend = 0.2
        
    def simulate_stress(self):
        self.base_temp = 40.5
        self.trend = 0.3
        
    def send_data(self, data):
        try:
            response = requests.post(
                SERVER_URL,
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                stress_level = result.get('stress_level', 0)
                is_stressed = result.get('is_stressed', False)
                
                status = " ESTRÉS" if is_stressed else "✓ Normal"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Temp: {data['avg_temp']}°C | "
                      f"Estrés: {stress_level:.1f}% | "
                      f"{status}")
                
                return result
            else:
                print(f" Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f" Error al conectar: {e}")
            return None

def run_simulation(duration_seconds=120, scenario='normal'):
    """
    Ejecuta simulación continua
    
    Scenarios:
    - 'normal': Comportamiento normal
    - 'elevated': Temperatura elevada
    - 'stress': Estrés simulado
    - 'cycle': Ciclo de normal -> stress -> normal
    """
    
    print(" Iniciando Simulación de Cámara Térmica")
    print(f"Duración: {duration_seconds}s | Escenario: {scenario}")
    print("-" * 60)
    
    simulator = ThermalSimulator()
    start_time = time.time()
    cycle_duration = duration_seconds // 3 if scenario == 'cycle' else duration_seconds
    cycle_start = start_time
    cycle_phase = 0
    
    try:
        while time.time() - start_time < duration_seconds:
            
            if scenario == 'cycle':
                elapsed_in_phase = time.time() - cycle_start
                if elapsed_in_phase > cycle_duration:
                    cycle_phase = (cycle_phase + 1) % 3
                    cycle_start = time.time()
                
                if cycle_phase == 0:
                    simulator.simulate_normal()
                    current_scenario = "Normal"
                elif cycle_phase == 1:
                    simulator.simulate_elevated()
                    current_scenario = "Elevado"
                else:
                    simulator.simulate_stress()
                    current_scenario = "Estrés"
            else:
                if scenario == 'elevated':
                    simulator.simulate_elevated()
                    current_scenario = "Elevado"
                elif scenario == 'stress':
                    simulator.simulate_stress()
                    current_scenario = "Estrés"
                else:
                    simulator.simulate_normal()
                    current_scenario = "Normal"
            
            data = simulator.generate_realistic_data()
            simulator.send_data(data)
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n Simulación detenida por el usuario")
    except Exception as e:
        print(f"\n Error durante simulación: {e}")
    
    print("-" * 60)
    print(" Simulación completada")

if __name__ == "__main__":
    import sys
    
    duration = 120
    scenario = 'normal'
    
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    if len(sys.argv) > 2:
        duration = int(sys.argv[2])
    
    valid_scenarios = ['normal', 'elevated', 'stress', 'cycle']
    if scenario not in valid_scenarios:
        print(f" Escenario inválido: {scenario}")
        print(f"Opciones válidas: {', '.join(valid_scenarios)}")
        sys.exit(1)
    
    run_simulation(duration, scenario)
