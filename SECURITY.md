# Política de Seguridad

## Versiones Soportadas

| Versión | Soportada |
|---------|-----------|
| 1.2.x   | ✅        |
| 1.1.x   | ✅        |
| < 1.0   | ❌        |

## Reportar una Vulnerabilidad

Tomamos la seguridad muy en serio. Si descubres una vulnerabilidad de seguridad, por favor:

1. **NO** crees un issue público en GitHub
2. Envía un email a: security@solarsense.example.com
3. Incluye la siguiente información:
   - Descripción de la vulnerabilidad
   - Pasos para reproducir
   - Impacto potencial
   - Sugerencia de corrección (si la tienes)

Recibirás una respuesta dentro de 48 horas confirmando la recepción del reporte.

## Proceso de Manejo de Vulnerabilidades

1. **Recepción** - Confirmación en 48 horas
2. **Evaluación** - Análisis de impacto en 5 días hábiles
3. **Corrección** - Desarrollo de parche en 15 días hábiles
4. **Lanzamiento** - Publicación de versión parcheada
5. **Divulgación** - Publicación de advisory de seguridad

## Buenas Prácticas de Seguridad

### Configuración

- **Nunca** commitees credenciales en el repositorio
- Usa archivos `.env` para variables sensibles
- Establece permisos restrictivos en archivos de configuración:
  ```bash
  chmod 600 config.yaml .env
  ```
- Rota las credenciales de cifrado periódicamente

### Red

- Aísla el dispositivo ESP8266 en una red separada
- Usa VLANs para segmentar tráfico SCADA
- Configura firewalls para permitir solo tráfico Modbus TCP (puerto 502)
- Monitorea conexiones no autorizadas

### Base de Datos

- Usa rutas relativas para archivos SQLite
- Realiza backups regulares de la base de datos
- No almacenes credenciales en la base de datos
- Valida todos los identificadores SQL

### Logs

- Revisa logs regularmente en busca de actividad sospechosa
- Configura rotación de logs para prevenir llenado de disco
- Verifica que los datos sensibles estén enmascarados
- Almacena logs en servidor separado para auditoría

### Actualizaciones

- Mantén Python y dependencias actualizadas
- Revisa advisory de seguridad de dependencias regularmente
- Aplica parches de seguridad promptly
- Usa `pip-audit` para verificar vulnerabilidades conocidas:
  ```bash
  pip install pip-audit
  pip-audit -r requirements.txt
  ```

## Herramientas de Seguridad Integradas

### 1. Cifrado de Credenciales

Las credenciales sensibles se cifran usando Fernet (symmetric encryption):

```python
from modbuspython.config.credential_encryptor import CredentialEncryptor

encryptor = CredentialEncryptor()
encrypted = encryptor.encrypt("sensitive_value")
```

### 2. Filtro de Datos Sensibles

El `LoggingService` incluye un filtro que enmascara automáticamente datos sensibles en logs:

- Contraseñas
- Tokens de acceso
- Claves de API
- Credenciales de base de datos

### 3. Validación de Entrada

Todos los inputs de usuario pasan por `ValidationService`:

- Validación de formato IP
- Validación de rangos de puertos
- Validación de identificadores SQL
- Sanitización de strings

### 4. Estado Seguro (Safe State)

El sistema entra en estado seguro cuando detecta errores críticos:

- Bloqueo de operaciones de escritura
- Continuación de operaciones de lectura
- Registro detallado del error
- Requiere intervención manual para salir

## Auditoría de Seguridad

### Checklist de Auditoría

- [ ] Revisar permisos de archivos de configuración
- [ ] Verificar enmascaramiento de logs
- [ ] Validar que no hay credenciales en código
- [ ] Verificar cifrado de credenciales almacenadas
- [ ] Revisar reglas de firewall
- [ ] Validar inputs de usuario en todas las interfaces
- [ ] Verificar que safe-state funciona correctamente
- [ ] Ejecutar `pip-audit` contra dependencias
- [ ] Revisar logs de acceso no autorizado

### Frecuencia Recomendada

- **Auditoría interna**: Mensual
- **Auditoría externa**: Anual
- **Escaneo de dependencias**: Semanal
- **Revisión de logs**: Diaria

## Divulgación Responsable

Seguimos las mejores prácticas de divulgación responsable:

1. No divulgamos vulnerabilidades hasta que exista un parche
2. Coordinamos con investigadores de seguridad
3. Publicamos advisories después de que los usuarios puedan actualizar
4. Reconocemos a investigadores que reporten vulnerabilidades

## Contacto

- **Email**: security@solarsense.example.com
- **PGP Key**: [Descargar](https://example.com/pgp-key.asc)
- **Tiempo de respuesta**: 48 horas

---

Última actualización: 2026-05-06
