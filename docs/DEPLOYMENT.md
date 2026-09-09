# Guía de Despliegue

## Índice

1. [Requisitos del Sistema](#requisitos-del-sistema)
2. [Despliegue en Windows](#despliegue-en-windows)
3. [Despliegue en Linux](#despliegue-en-linux)
4. [Despliegue con Docker](#despliegue-con-docker)
5. [Configuración de Producción](#configuración-de-producción)
6. [Monitoreo y Mantenimiento](#monitoreo-y-mantenimiento)
7. [Backup y Recuperación](#backup-y-recuperación)
8. [Solución de Problemas de Despliegue](#solución-de-problemas-de-despliegue)

---

## Requisitos del Sistema

### Mínimos

| Componente | Requisito |
|------------|-----------|
| CPU | 2 núcleos |
| RAM | 2 GB |
| Disco | 5 GB libres |
| SO | Windows 10+, Ubuntu 20.04+, Debian 11+ |
| Python | 3.10+ |
| Red | Conexión a red local con ESP8266 |

### Recomendados

| Componente | Requisito |
|------------|-----------|
| CPU | 4 núcleos |
| RAM | 4 GB |
| Disco | 10 GB SSD |
| SO | Windows 11, Ubuntu 22.04 LTS |
| Python | 3.13+ |
| Red | Conexión cableada o WiFi 5GHz |

---

## Despliegue en Windows

### 1. Instalar Python

Descargar e instalar Python 3.10+ desde [python.org](https://www.python.org/downloads/).

Durante la instalación, marcar:
- ✅ "Add Python to PATH"
- ✅ "Install launcher for all users"

Verificar instalación:
```powershell
python --version
pip --version
```

### 2. Descargar el Código

```powershell
# Con Git
git clone https://github.com/EdinsonMoreno/nexo-solar.git
cd nexo-solar

# O descargar ZIP y extraer
```

### 3. Crear Entorno Virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si hay error de política de ejecución:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Instalar Dependencias

```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # opcional, para desarrollo
```

### 5. Configurar Aplicación

```powershell
# Copiar archivos de configuración
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml

# Editar configuración
notepad .env
notepad config.yaml
```

### 6. Crear Carpetas Requeridas

```powershell
New-Item -ItemType Directory -Path data, logs -Force
```

### 7. Ejecutar Aplicación

```powershell
python run.py
```

### 8. Crear Acceso Directo (Opcional)

Crear un archivo `SolarSense.bat`:
```batch
@echo off
cd /d C:\ruta\al\proyecto
call .venv\Scripts\activate.bat
python run.py
```

Colocar en `shell:startup` para inicio automático:
```powershell
Copy-Item SolarSense.bat "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\"
```

---

## Despliegue en Linux

### 1. Instalar Python y Dependencias del Sistema

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip git

# RHEL/CentOS/Fedora
sudo dnf install python3 python3-devel git
```

### 2. Descargar el Código

```bash
git clone https://github.com/EdinsonMoreno/nexo-solar.git
cd nexo-solar
```

### 3. Crear Entorno Virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configurar Aplicación

```bash
cp .env.example .env
cp config.example.yaml config.yaml
nano .env
nano config.yaml
```

### 6. Crear Carpetas y Permisos

```bash
mkdir -p data logs
chmod 750 data logs
chmod 600 .env config.yaml
```

### 7. Crear Servicio systemd

Crear `/etc/systemd/system/solarsense.service`:

```ini
[Unit]
Description=SolarSense SCADA
After=network.target

[Service]
Type=simple
User=solarsense
Group=solarsense
WorkingDirectory=/opt/solarsense-scada
ExecStart=/opt/solarsense-scada/.venv/bin/python run.py
Restart=on-failure
RestartSec=5
Environment=PATH=/opt/solarsense-scada/.venv/bin

[Install]
WantedBy=multi-user.target
```

### 8. Habilitar y Ejecutar Servicio

```bash
sudo systemctl daemon-reload
sudo systemctl enable solarsense
sudo systemctl start solarsense
sudo systemctl status solarsense
```

---

## Despliegue con Docker

### 1. Crear Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Crear directorios
RUN mkdir -p data logs

# Exponer puerto (si aplica para API futura)
EXPOSE 5000

# Ejecutar aplicación
CMD ["python", "run.py"]
```

### 2. Crear docker-compose.yml

```yaml
version: '3.8'

services:
  solarsense:
    build: .
    container_name: solarsense-scada
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config.yaml:/app/config.yaml:ro
      - ./.env:/app/.env:ro
    environment:
      - DISPLAY=${DISPLAY}
      - MODBUS_HOST=${MODBUS_HOST}
      - MODBUS_PORT=${MODBUS_PORT}
    network_mode: host  # Necesario para comunicación Modbus TCP local
    deploy:
      resources:
        limits:
          memory: 500M
          cpus: '1.0'
```

### 3. Construir y Ejecutar

```bash
docker-compose up -d --build

# Ver logs
docker-compose logs -f solarsense

# Detener
docker-compose down
```

**Nota:** Para aplicaciones GUI con PyQt6, se requiere configuración adicional de X11 forwarding o usar VNC/RDP.

---

## Configuración de Producción

### 1. Configuración Recomendada

```yaml
# config.yaml
modbus:
  timeout: 10.0
  retry_attempts: 5
  retry_backoff: 2.0

logging:
  level: "WARNING"  # Menos verboso en producción
  max_bytes: 52428800  # 50 MB
  backup_count: 10

performance:
  startup_timeout_s: 10
  shutdown_timeout_s: 15
  max_memory_mb: 500
```

### 2. Variables de Entorno

```bash
# .env
MODBUS_HOST=192.168.1.100
MODBUS_PORT=502
DB_PATH=data/solarsense.db
LOG_LEVEL=WARNING
ENCRYPTION_KEY=<generar_con_credential_encryptor>
```

### 3. Hardening de Seguridad

```bash
# Restringir permisos
chmod 600 .env config.yaml
chmod 750 data logs

# Configurar firewall (Linux)
sudo ufw allow from 192.168.1.0/24 to any port 502
sudo ufw enable

# Configurar firewall (Windows)
New-NetFirewallRule -DisplayName "Modbus TCP" -Direction Inbound -LocalPort 502 -Protocol TCP -Action Allow
```

### 4. Rotación de Logs con Logrotate (Linux)

Crear `/etc/logrotate.d/solarsense`:

```
/opt/solarsense-scada/logs/*.log {
    daily
    rotate 10
    compress
    delaycompress
    missingok
    notifempty
    create 0640 solarsense solarsense
    sharedscripts
    postrotate
        systemctl reload solarsense > /dev/null 2>&1 || true
    endscript
}
```

---

## Monitoreo y Mantenimiento

### 1. Verificar Estado del Servicio

```bash
# Linux systemd
sudo systemctl status solarsense

# Windows
Get-Service -Name "SolarSense"  # si está registrado como servicio
```

### 2. Monitorear Logs

```bash
# Seguir logs en tiempo real
tail -f logs/solarsense.log

# Buscar errores
grep "ERROR\|CRITICAL" logs/solarsense.log

# Estadísticas de logs
awk '{print $5}' logs/solarsense.log | sort | uniq -c | sort -nr
```

### 3. Verificar Conexión Modbus

```bash
# Test de conectividad
ping 192.168.1.100
nc -zv 192.168.1.100 502
```

### 4. Monitorear Uso de Recursos

```bash
# Linux
top -p $(pgrep -f "run.py")
ps aux | grep python

# Windows
tasklist /fi "imagename eq python.exe"
Get-Process python | Select-Object CPU,WorkingSet
```

### 5. Actualizar Aplicación

```bash
# Detener servicio
sudo systemctl stop solarsense

# Actualizar código
git pull origin main

# Actualizar dependencias
pip install -r requirements.txt

# Ejecutar migraciones
python -c "from modbuspython.migrations.migration_manager import MigrationManager; MigrationManager().run_migrations()"

# Iniciar servicio
sudo systemctl start solarsense
```

---

## Backup y Recuperación

### 1. Backup Automático (Linux)

Crear script `/opt/solarsense-scada/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup/solarsense"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup base de datos
cp data/solarsense.db $BACKUP_DIR/solarsense_$DATE.db

# Backup configuración
cp config.yaml $BACKUP_DIR/config_$DATE.yaml
cp .env $BACKUP_DIR/env_$DATE

# Mantener solo últimos 7 días
find $BACKUP_DIR -mtime +7 -delete

echo "Backup completado: $DATE"
```

Agregar a crontab (`crontab -e`):
```
0 2 * * * /opt/solarsense-scada/backup.sh
```

### 2. Backup Manual (Windows)

```powershell
$Date = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Path "backup" -Force

Copy-Item "data\solarsense.db" "backup\solarsense_$Date.db"
Copy-Item "config.yaml" "backup\config_$Date.yaml"
Copy-Item ".env" "backup\env_$Date"
```

### 3. Recuperación de Base de Datos

```bash
# Detener aplicación
sudo systemctl stop solarsense

# Restaurar backup
cp /backup/solarsense/solarsense_20260506_020000.db data/solarsense.db

# Iniciar aplicación
sudo systemctl start solarsense
```

---

## Solución de Problemas de Despliegue

### La aplicación no inicia

```bash
# Verificar Python
python --version

# Verificar dependencias
pip list | grep -E "PyQt6|pymodbus|pyyaml"

# Ejecutar con debug
python -c "import modbuspython; print('OK')"
```

### Error de permisos

```bash
# Verificar propietario
ls -la data/ logs/

# Corregir permisos
chown -R solarsense:solarsense /opt/solarsense-scada
chmod -R 750 data logs
```

### Error de conexión Modbus

```bash
# Verificar red
ip addr show
ping 192.168.1.100

# Verificar puerto
netstat -tulpn | grep 502
```

### Servicio no se mantiene activo

```bash
# Ver logs del servicio
journalctl -u solarsense -n 100

# Verificar configuración
cat /etc/systemd/system/solarsense.service
```

---

## Checklist de Despliegue

- [ ] Python 3.10+ instalado
- [ ] Entorno virtual creado
- [ ] Dependencias instaladas
- [ ] Configuración copiada y editada
- [ ] Carpetas `data` y `logs` creadas
- [ ] Permisos configurados correctamente
- [ ] Firewall configurado
- [ ] Servicio configurado (systemd o Windows Service)
- [ ] Backup automático configurado
- [ ] Monitoreo de logs configurado
- [ ] Prueba de conexión Modbus exitosa
- [ ] Prueba de escritura en base de datos exitosa

---

Última actualización: 2026-05-06
