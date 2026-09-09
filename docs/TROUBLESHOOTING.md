# Troubleshooting Guide

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Database Issues](#database-issues)
3. [UI Issues](#ui-issues)
4. [Configuration Issues](#configuration-issues)
5. [Performance Issues](#performance-issues)
6. [Security Issues](#security-issues)
7. [Understanding Logs](#understanding-logs)

## Connection Issues

### Cannot Connect to Modbus Device

**Symptoms:**
- Log shows "Failed to establish Modbus connection"
- Radiation gauge shows no data
- Safe state indicator is active

**Steps to diagnose:**

1. **Verify IP and port:**
   ```bash
   # Test connectivity
   ping 192.168.1.100
   telnet 192.168.1.100 502
   ```

2. **Check configuration:**
   ```yaml
   # config.yaml
   modbus:
     host: "192.168.1.100"  # Must match ESP8266 IP
     port: 502
     timeout: 5.0
   ```

3. **Check ESP8266 status:**
   - Verify ESP8266 is powered on
   - Check WiFi connection
   - Verify Modbus server is running on ESP8266

4. **Check network:**
   - Ensure computer and ESP8266 are on same network
   - Check firewall rules for port 502
   - Verify no IP conflicts

5. **Review logs:**
   ```bash
   # Check recent errors
   cat logs/solarsense.log | grep -i "error\|modbus\|connection"
   ```

**Common solutions:**
- Restart ESP8266 device
- Reconnect to WiFi
- Update ESP8266 firmware
- Increase timeout if network is slow

### Connection Drops Intermittently

**Symptoms:**
- Connection established but drops periodically
- Radiation data appears then disappears

**Steps to diagnose:**

1. **Check network stability:**
   ```bash
   # Continuous ping
   ping -t 192.168.1.100
   ```

2. **Review retry configuration:**
   ```yaml
   modbus:
     retry_attempts: 3      # Increase if needed
     retry_backoff: 1.0     # Base delay between retries
   ```

3. **Check ESP8266 resources:**
   - Memory usage on ESP8266
   - WiFi signal strength
   - Power supply stability

**Common solutions:**
- Move ESP8266 closer to WiFi router
- Use wired connection if possible
- Increase retry_attempts to 5
- Add external antenna to ESP8266

## Database Issues

### Database File Not Created

**Symptoms:**
- Error: "Permission or access error for database file"
- No `data/solarsense.db` file exists

**Steps to diagnose:**

1. **Check directory permissions:**
   ```bash
   # Windows
   icacls data
   # Linux
   ls -la data/
   ```

2. **Create directory manually:**
   ```bash
   mkdir data
   chmod 755 data
   ```

3. **Check configuration:**
   ```yaml
   database:
     path: "data/solarsense.db"
   ```

### Database Locked Error

**Symptoms:**
- Error: "database is locked"
- Application becomes unresponsive

**Steps to diagnose:**

1. **Check connection pool size:**
   ```yaml
   database:
     connection_pool_size: 5  # Reduce if too high
   ```

2. **Check for concurrent access:**
   - Ensure no other process is accessing the database
   - Close any database browsers/tools

3. **Review long-running transactions:**
   - Check logs for slow queries
   - Consider reducing chart_history_points

### Table Not Found

**Symptoms:**
- Error: "no such table: measurements"

**Steps to diagnose:**

1. **Check table name:**
   ```yaml
   database:
     table_name: "measurements"  # Must match
   ```

2. **Verify table exists:**
   ```bash
   sqlite3 data/solarsense.db ".tables"
   ```

3. **Recreate table:**
   - Restart application (creates table automatically)
   - Or run migration manually

## UI Issues

### Map Not Loading

**Symptoms:**
- Map area is blank or shows error
- Tiles not displayed

**Steps to diagnose:**

1. **Check internet connection:**
   - Map uses OpenStreetMap tiles online by default

2. **Check offline tiles:**
   ```bash
   # Verify tiles exist
   ls modbuspython/ui/assets/tiles/
   ```

3. **Check Leaflet assets:**
   ```bash
   ls modbuspython/ui/assets/leaflet/
   ```

4. **Check WebEngine:**
   ```bash
   # Verify PyQt6-WebEngine is installed
   pip show PyQt6-WebEngine
   ```

### 3D Viewer Not Working

**Symptoms:**
- 3D viewer is blank
- JavaScript errors in console

**Steps to diagnose:**

1. **Check PyQt6-WebEngine:**
   ```bash
   pip install PyQt6-WebEngine
   ```

2. **Check HTML file:**
   ```bash
   ls modbuspython/ui/visor_3d_piranometro.html
   ```

3. **Check browser console:**
   - Open Developer Tools in WebEngine
   - Look for JavaScript errors

### Gauges Not Updating

**Symptoms:**
- Circular gauges show stale data
- No new radiation readings

**Steps to diagnose:**

1. **Check Modbus connection:** See [Connection Issues](#connection-issues)

2. **Check update interval:**
   ```yaml
   ui:
     update_interval_ms: 1000  # 1 second
   ```

3. **Check signal connections:**
   - Look for "ModbusClient thread started" in logs
   - Check for "Solar radiation read" messages

## Configuration Issues

### Configuration Not Loading

**Symptoms:**
- Application starts with default values
- Warning about missing config file

**Steps to diagnose:**

1. **Check file location:**
   ```bash
   # Config should be in project root
   ls config.yaml
   ```

2. **Check file format:**
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

3. **Check file permissions:**
   ```bash
   chmod 644 config.yaml
   ```

### Environment Variables Not Expanding

**Symptoms:**
- Configuration shows `${VAR_NAME}` instead of actual values
- Warning: "Environment variable not set: VAR_NAME"

**Steps to diagnose:**

1. **Check .env file:**
   ```bash
   ls .env
   cat .env
   ```

2. **Check variable syntax:**
   ```bash
   # Correct: ${VAR_NAME}
   # Incorrect: $VAR_NAME or %VAR_NAME%
   ```

3. **Check variable is set:**
   ```bash
   # Windows
   echo %MODBUS_HOST%
   # Linux/macOS
   echo $MODBUS_HOST
   ```

### Validation Errors

**Symptoms:**
- Error: "Configuration schema validation failed"
- Application falls back to defaults

**Steps to diagnose:**

1. **Review validation error:**
   ```bash
   cat logs/solarsense.log | grep "validation"
   ```

2. **Check schema:**
   ```bash
   cat modbuspython/config/config_schema.json
   ```

3. **Validate manually:**
   ```python
   import json
   from jsonschema import validate
   config = json.load(open("config.yaml"))  # or yaml.safe_load
   schema = json.load(open("modbuspython/config/config_schema.json"))
   validate(instance=config, schema=schema)
   ```

## Performance Issues

### Slow Startup

**Symptoms:**
- Application takes > 5 seconds to start

**Steps to diagnose:**

1. **Check startup timeout:**
   ```yaml
   performance:
     startup_timeout_s: 5
   ```

2. **Check what's loading:**
   - Look at logs during startup
   - Identify slow-loading modules

3. **Reduce initial load:**
   - Decrease chart_history_points
   - Reduce connection_pool_size

### High Memory Usage

**Symptoms:**
- Memory usage exceeds 500 MB
- Warning in logs about memory

**Steps to diagnose:**

1. **Check memory limit:**
   ```yaml
   performance:
     max_memory_mb: 500
   ```

2. **Check data accumulation:**
   - Reduce chart_history_points
   - Clean up old database records

3. **Monitor memory:**
   ```bash
   # Windows
   tasklist /fi "imagename eq python.exe" /fo list
   # Linux
   ps aux | grep python
   ```

## Security Issues

### Credentials in Logs

**Symptoms:**
- Passwords or sensitive data visible in log files

**Steps to fix:**

1. **Verify SensitiveDataFilter is active:**
   - Check LoggingService setup
   - Verify sensitive_keys configuration

2. **Check log level:**
   ```yaml
   logging:
     level: "INFO"  # Use INFO, not DEBUG for production
   ```

3. **Audit log files:**
   ```bash
   grep -i "password\|secret\|token\|key" logs/solarsense.log
   ```

### Insecure File Permissions

**Symptoms:**
- Warning: "Configuration file has insecure permissions"

**Steps to fix:**

```bash
# Unix
chmod 600 config.yaml
chmod 600 .env

# Windows - use file properties to restrict access
```

## Understanding Logs

### Log Format

```
YYYY-MM-DD HH:MM:SS - LEVEL - module.function:line - Message
```

Example:
```
2026-05-06 14:30:00 - INFO - modbus_client.connect:271 - Modbus connection established: 192.168.1.100:502
```

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| DEBUG | Detailed diagnostics | Register read values, internal state |
| INFO | Important events | Connection established, config loaded |
| WARNING | Recoverable errors | Retry attempt, fallback to defaults |
| ERROR | Failures requiring attention | Connection failed, validation error |
| CRITICAL | System-impacting failures | Database corruption, fatal error |

### Common Log Messages

| Message | Meaning | Action |
|---------|---------|--------|
| "Modbus connection established" | Connected to ESP8266 | None - normal |
| "Failed to establish Modbus connection" | Connection failed | Check network, IP, port |
| "RetryStrategy initialized" | Retry logic configured | None - normal |
| "Configuration loaded successfully" | Config is valid | None - normal |
| "Falling back to default configuration" | Config was invalid | Check config.yaml |
| "Schema version updated" | Migration applied | None - normal |
| "System entering safe state" | Critical error occurred | Check error details, exit safe state manually |
| "Connection pool exhausted" | Too many DB connections | Increase pool_size or reduce usage |

### Log Location

```bash
# Default location
logs/solarsense.log

# Rotate files (if max_bytes exceeded)
logs/solarsense.log.1
logs/solarsense.log.2
...
```

### Changing Log Level at Runtime

```python
from modbuspython.data_access.logging_service import LoggingService

logger = LoggingService()
logger.set_level("DEBUG")  # Increase verbosity
logger.set_level("WARNING")  # Reduce verbosity
```

## Getting Help

If you cannot resolve the issue:

1. **Collect diagnostic information:**
   ```bash
   # System info
   python --version
   pip list

   # Logs
   tail -100 logs/solarsense.log

   # Configuration
   cat config.yaml (remove sensitive data)
   ```

2. **Open an issue:**
   - Include diagnostic information
   - Describe steps to reproduce
   - Include error messages

3. **Check existing issues:**
   - Search for similar problems
   - Check if a fix is available
