// WebSocket Connection
const socket = io();

// Global State
let chartsInstance = {};
let sessionStartTime = Date.now();
let maxStressRecorded = 0;
let maxTempRecorded = 0;

// Chart instances
let tempChart, stressChart;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Inicializando Sistema de Monitoreo Térmico');
    initializeCharts();
    initializeEventListeners();
    initializeWebSocket();
    startSessionTimer();
});

// Initialize Charts
function initializeCharts() {
    const ctxTemp = document.getElementById('tempChart').getContext('2d');
    tempChart = new Chart(ctxTemp, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperatura (°C)',
                data: [],
                borderColor: '#FF6B35',
                backgroundColor: 'rgba(255, 107, 53, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 2,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#e8eaed' } }
            },
            scales: {
                y: {
                    min: 30,
                    max: 42,
                    grid: { color: 'rgba(64, 68, 86, 0.3)' },
                    ticks: { color: '#a8adb5' }
                },
                x: {
                    grid: { color: 'rgba(64, 68, 86, 0.3)' },
                    ticks: { color: '#a8adb5' }
                }
            }
        }
    });

    const ctxStress = document.getElementById('stressChart').getContext('2d');
    stressChart = new Chart(ctxStress, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Nivel de Estrés (%)',
                data: [],
                borderColor: '#f44336',
                backgroundColor: 'rgba(244, 67, 54, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 2,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#e8eaed' } }
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(64, 68, 86, 0.3)' },
                    ticks: { color: '#a8adb5' }
                },
                x: {
                    grid: { color: 'rgba(64, 68, 86, 0.3)' },
                    ticks: { color: '#a8adb5' }
                }
            }
        }
    });
}

// Initialize Event Listeners
function initializeEventListeners() {
    document.getElementById('stressThreshold').addEventListener('change', (e) => {
        const threshold = e.target.value;
        document.getElementById('thresholdValue').textContent = threshold + '%';
        updateSystemConfig({ stress_threshold: parseInt(threshold) });
    });

    document.getElementById('alertsToggle').addEventListener('change', (e) => {
        const status = e.target.checked ? 'Activadas' : 'Desactivadas';
        document.getElementById('alertsStatus').textContent = status;
        updateSystemConfig({ alerts_enabled: e.target.checked });
    });

    document.getElementById('monitoringToggle').addEventListener('change', (e) => {
        const status = e.target.checked ? 'Activo' : 'Pausado';
        document.getElementById('monitoringStatus').textContent = status;
        updateSystemConfig({ monitoring: e.target.checked });
    });
}

// WebSocket Events
function initializeWebSocket() {
    socket.on('connect', () => {
        console.log('Conectado al servidor');
        updateConnectionStatus(true);
    });

    socket.on('disconnect', () => {
        console.log('Desconectado del servidor');
        updateConnectionStatus(false);
    });

    socket.on('thermal_update', (data) => {
        handleThermalUpdate(data);
    });

    socket.on('notification', (notification) => {
        addNotification(notification);
    });

    socket.on('system_config', (config) => {
        updateSystemUI(config);
    });
}

// Handle Thermal Data
function handleThermalUpdate(data) {
    const camera = data.camera_data;
    const stress = data.stress_result;
    const history = data.history || [];

    // Actualizar datos de temperatura
    updateTemperatureDisplay(camera);
    updateStressDisplay(stress);
    updateThermalZones(camera.zones);
    updateCharts(history);
    updateStatistics(camera, stress);

    // Actualizar timestamp
    const now = new Date();
    document.getElementById('lastUpdate').textContent = now.toLocaleTimeString('es-ES');

    // Conectar cámara
    if (!document.getElementById('cameraStatus').classList.contains('connected')) {
        document.getElementById('cameraStatus').textContent = 'Conectada';
        document.getElementById('cameraStatus').className = 'status-badge connected';
    }
}

// Update Temperature Display
function updateTemperatureDisplay(camera) {
    document.getElementById('currentTemp').textContent = camera.current_temp.toFixed(1) + '°C';
    document.getElementById('avgTemp').textContent = camera.avg_temp.toFixed(1) + '°C';
    document.getElementById('maxTemp').textContent = camera.max_temp.toFixed(1) + '°C';
    document.getElementById('minTemp').textContent = camera.min_temp.toFixed(1) + '°C';

    maxTempRecorded = Math.max(maxTempRecorded, camera.max_temp);
    document.getElementById('maxRecorded').textContent = maxTempRecorded.toFixed(1) + '°C';
}

// Update Stress Display
function updateStressDisplay(stress) {
    const stressLevel = stress.stress_level;
    const isStressed = stress.is_stressed;

    document.getElementById('stressValue').textContent = stressLevel.toFixed(1) + '%';
    document.getElementById('stressBar').style.width = stressLevel + '%';

    maxStressRecorded = Math.max(maxStressRecorded, stressLevel);
    document.getElementById('maxStress').textContent = maxStressRecorded.toFixed(1) + '%';

    // Actualizar estado
    let statusText, statusColor;
    if (stressLevel < 30) {
        statusText = '✓ Normal';
        statusColor = '#4caf50';
    } else if (stressLevel < 50) {
        statusText = '⚠️ Leve';
        statusColor = '#ff9800';
    } else if (stressLevel < 70) {
        statusText = 'Moderado';
        statusColor = '#ff5722';
    } else {
        statusText = 'Alto';
        statusColor = '#f44336';
    }

    document.getElementById('stressStatus').textContent = statusText;
    document.getElementById('stressStatus').style.color = statusColor;
}

// Update Thermal Zones
function updateThermalZones(zones) {
    const zoneIds = {
        'head': 'zoneHead',
        'body': 'zoneBody',
        'legs': 'zoneLegs'
    };

    Object.keys(zones).forEach(zone => {
        const elementId = zoneIds[zone];
        if (elementId && zones[zone].avg_temp) {
            document.getElementById(elementId).textContent = zones[zone].avg_temp.toFixed(1) + '°C';
        }
    });
}

// Update Charts
function updateCharts(history) {
    if (history.length === 0) return;

    const labels = history.map(h => {
        const date = new Date(h.timestamp);
        return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });

    const temps = history.map(h => h.avg_temp);
    const stress = history.map(h => h.stress_level);

    // Temperature Chart
    tempChart.data.labels = labels;
    tempChart.data.datasets[0].data = temps;
    tempChart.update();

    // Stress Chart
    stressChart.data.labels = labels;
    stressChart.data.datasets[0].data = stress;
    stressChart.update();
}

// Update Statistics
function updateStatistics(camera, stress) {
    const alerts = document.querySelectorAll('.alert').length;
    document.getElementById('totalAlerts').textContent = alerts;
}

// Add Notification
function addNotification(notification) {
    const alertsList = document.getElementById('alertsList');
    
    // Limpiar notificación inicial si existe
    const initialAlert = alertsList.querySelector('.alert-info');
    if (initialAlert) {
        initialAlert.remove();
    }

    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${notification.type}`;
    alertElement.innerHTML = `
        <span class="alert-icon">${getAlertIcon(notification.type)}</span>
        <span>${notification.message}</span>
    `;

    alertsList.insertBefore(alertElement, alertsList.firstChild);

    // Mantener solo últimas 10 alertas
    while (alertsList.children.length > 10) {
        alertsList.removeChild(alertsList.lastChild);
    }

    // Reproducir sonido de notificación para alertas críticas
    if (notification.type === 'danger') {
        playNotificationSound();
    }
}

function getAlertIcon(type) {
    const icons = {
        'info': 'i',
        'success': '✓',
        'warning': '',
        'danger': ''
    };
    return icons[type] || 'i';
}

function playNotificationSound() {
    // Crear un tono de alerta
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();

    oscillator.connect(gain);
    gain.connect(audioContext.destination);

    oscillator.frequency.value = 800;
    oscillator.type = 'sine';

    gain.gain.setValueAtTime(0.3, audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
}

// Update System Config
function updateSystemConfig(config) {
    fetch('/api/configure', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    }).catch(err => console.error('Error:', err));
}

// Update System UI
function updateSystemUI(config) {
    document.getElementById('stressThreshold').value = config.stress_threshold;
    document.getElementById('thresholdValue').textContent = config.stress_threshold + '%';
    document.getElementById('alertsToggle').checked = config.alerts_enabled;
    document.getElementById('monitoringToggle').checked = config.monitoring;
}

// Update Connection Status
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connectionIndicator');
    const text = document.getElementById('connectionText');

    if (connected) {
        indicator.className = 'indicator connected';
        text.textContent = 'Conectado';
    } else {
        indicator.className = 'indicator disconnected';
        text.textContent = 'Desconectado';
    }
}

// Session Timer
function startSessionTimer() {
    setInterval(() => {
        const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        document.getElementById('sessionTime').textContent = timeStr;
    }, 1000);
}

console.log('Script cargado correctamente');
