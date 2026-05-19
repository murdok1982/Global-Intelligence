# Runbook operacional

Este documento describe los procedimientos de despliegue, operación
y recuperación de la plataforma Global Intelligence en un entorno
de producción o preproducción.

Audiencia. Personal técnico autorizado del operador: SysOps, DevOps,
DBAs, equipo de seguridad.

---

## 1. Despliegue en producción

### 1.1 Modelos de despliegue soportados

- VPS Linux con Docker Engine 24+ y Docker Compose plugin. Mínimo
  recomendado: 4 vCPU, 16 GB RAM, 100 GB SSD. Para inferencia local
  con GPU, añadir GPU NVIDIA con drivers CUDA 12+ y NVIDIA Container
  Toolkit.
- Servidor on-premise con la misma especificación. Recomendado para
  despliegues clasificados.
- Cluster Kubernetes. No cubierto por este runbook; los manifiestos
  son convertibles desde `docker-compose.yml` pero requieren ajustes
  de RLS y de afinidad por GPU.

### 1.2 Preparación del host

1. Sistema operativo: distribución Linux con soporte de larga
   duración (Debian 12, Ubuntu 22.04 LTS o RHEL 9).
2. Aplicar parches del sistema. Configurar `unattended-upgrades`
   solo para parches de seguridad.
3. Endurecer SSH: deshabilitar login root y autenticación por
   password, exigir clave pública, restringir por IP.
4. Instalar Docker Engine y Compose plugin desde repositorios
   oficiales.
5. Configurar reverse proxy TLS frente a los puertos del backend y
   del frontend (nginx, Caddy o Traefik). Renovación automática
   mediante ACME o certificado del operador.
6. Crear usuario sistema dedicado para la operación de la
   plataforma. No usar root.

### 1.3 Procedimiento de instalación

```bash
# Como el usuario dedicado del servicio
git clone <url-del-repositorio> global-intelligence
cd global-intelligence
cp backend/.env.example backend/.env
$EDITOR backend/.env       # rellenar secrets
docker compose pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M
```

Verificación inmediata:

```bash
curl -fsS http://127.0.0.1:8000/health || echo "BACKEND DOWN"
docker compose exec ollama ollama list
docker compose ps
```

---

## 2. Variables de entorno

Las variables se definen en `backend/.env`. La plantilla autoritativa
es `backend/.env.example`. La validación de arranque se ejecuta en
`app.core.config.Settings.validate_secrets()`.

### 2.1 Generación de secretos

Todos los valores hexadecimales requeridos se generan con `openssl`:

```bash
openssl rand -hex 32        # 32 bytes -> 64 caracteres hex
```

### 2.2 Tabla de variables

| Variable | Obligatoria | Cómo se genera o configura |
| --- | --- | --- |
| `ENV` | Sí | `production`, `staging` o `development`. |
| `SECRET_KEY` | Sí (production) | `openssl rand -hex 32`. Firma JWT access. |
| `REFRESH_SECRET_KEY` | Sí (production) | `openssl rand -hex 32`. Firma JWT refresh. |
| `POSTGRES_USER` | Sí | Usuario aplicación Postgres. |
| `POSTGRES_PASSWORD` | Sí (production) | Generar con `openssl rand -base64 32`. |
| `POSTGRES_SERVER` | Sí | Hostname/contenedor Postgres (`db` por defecto). |
| `POSTGRES_PORT` | Sí | Puerto Postgres (`5432`). |
| `POSTGRES_DB` | Sí | Nombre de base de datos. |
| `REDIS_URL` | Sí | URL Redis (`redis://redis:6379/0`). |
| `REDIS_PASSWORD` | Recomendada | Password Redis si autenticación habilitada. |
| `OLLAMA_BASE_URL` | Sí | URL del servicio Ollama interno. |
| `OLLAMA_MODEL` | Sí | Identificador de modelo Ollama. |
| `OLLAMA_TIMEOUT` | No | Timeout HTTP en segundos (120 por defecto). |
| `VLLM_BASE_URL` | No | URL vLLM si segundo proveedor local en uso. |
| `VLLM_MODEL` | No | Identificador modelo vLLM. |
| `OPENROUTER_API_KEY` | No | Dejar vacío en despliegue estatal. |
| `ENABLE_OPENROUTER_FALLBACK` | Sí | `false` en despliegue estatal. |
| `OPENROUTER_DEFAULT_MODEL` | No | Modelo por defecto si fallback habilitado. |
| `STATE_GRADE_MODE` | Sí | `true` en cualquier despliegue clasificado. |
| `MFA_ENCRYPTION_KEY` | Sí (state-grade) | `openssl rand -hex 32`. AES-GCM 256-bit. |
| `MFA_CHALLENGE_SECRET` | Sí (state-grade) | `openssl rand -hex 32`. Distinto de SECRET_KEY. |
| `MFA_CHALLENGE_TTL_SECONDS` | No | TTL del challenge MFA (300 por defecto). |
| `MFA_RECOVERY_CODES_COUNT` | No | Códigos de recuperación generados al alta MFA. |
| `MFA_ISSUER` | No | Etiqueta que muestran las apps autenticadoras. |
| `STRIPE_SECRET_KEY` | No | Vacío en despliegue estatal (ver nota). |
| `STRIPE_WEBHOOK_SECRET` | No | Vacío en despliegue estatal. |

> Nota sobre Stripe. El endpoint de webhook permanece en el código
> por compatibilidad histórica. En despliegue estatal debe quedar
> sin claves configuradas; se recomienda al operador eliminar la
> ruta o bloquearla en el reverse proxy. La eliminación del módulo
> está prevista en el siguiente saneamiento de código.

---

## 3. Arranque y validación de Ollama

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M
docker compose exec ollama ollama list
curl -fsS http://127.0.0.1:11434/api/tags
```

Modelos alternativos soportados (cambiar `OLLAMA_MODEL` en `.env`):

- `qwen2.5:14b-instruct-q4_K_M`
- `mistral-nemo:12b-instruct-q4_K_M`

Para GPU NVIDIA: descomentar el bloque `deploy.resources.reservations`
del servicio `ollama` en `docker-compose.yml` e instalar
`nvidia-container-toolkit`.

---

## 4. Gestión de usuarios

### 4.1 Alta de usuario

Hasta que el endpoint administrativo dedicado esté disponible (P2),
el alta se realiza por SQL:

```sql
INSERT INTO users (id, email, hashed_password, is_active, clearance_level, org_id)
VALUES (
    gen_random_uuid(),
    'analista.uno@agencia.gob',
    crypt('PWD_TEMPORAL', gen_salt('bf', 12)),
    TRUE,
    0,        -- PUBLIC por defecto
    NULL      -- sin organización
);
```

El usuario debe cambiar la password en el primer login. Si la
extensión `pgcrypto` no está disponible, generar el hash bcrypt
fuera de banda y registrarlo directamente.

### 4.2 Asignación de nivel de habilitación

```sql
UPDATE users
SET clearance_level = 2          -- CONFIDENTIAL
WHERE email = 'analista.uno@agencia.gob';
```

Niveles: 0 PUBLIC, 1 RESTRICTED, 2 CONFIDENTIAL, 3 SECRET.

Cualquier modificación de `clearance_level` queda registrada en el
audit log con el identificador del administrador que la ejecuta. Si
la modificación se realiza por SQL directo, **registrar manualmente
un evento en el audit log** con motivo, autorizador y referencia
documental.

### 4.3 Asignación de organización (multi-tenant)

```sql
UPDATE users
SET org_id = '<uuid-de-la-organizacion>'
WHERE email = 'analista.uno@agencia.gob';
```

`org_id = NULL` indica usuario global (operación inter-organismos).
Reservar este valor para administradores plataforma.

### 4.4 Restablecimiento de MFA

Procedimiento manual ante pérdida del segundo factor (cambio de
dispositivo, robo, etc.):

1. Verificar identidad del titular por canal fuera de banda
   (presencial, video con documento, llamada de jefatura). Registrar
   la verificación en el sistema de tickets del operador.
2. Aplicar reset en base de datos:

   ```sql
   UPDATE users
   SET two_factor_enabled = FALSE,
       mfa_secret_encrypted = NULL,
       mfa_recovery_codes = NULL
   WHERE email = 'analista.uno@agencia.gob';
   ```

3. Registrar manualmente en el audit log:

   ```sql
   INSERT INTO audit_events (event_type, actor_id, target_user_id, metadata)
   VALUES (
       'mfa.reset.manual',
       '<uuid-del-admin>',
       '<uuid-del-usuario>',
       jsonb_build_object(
           'reason', 'lost_device',
           'authorized_by', '<nombre>',
           'ticket', 'OPS-1234'
       )
   );
   ```

4. Notificar al usuario por canal fuera de banda. En el siguiente
   login se le pedirá realizar el alta MFA de nuevo.

### 4.5 Baja de usuario

```sql
UPDATE users
SET is_active = FALSE,
    deactivated_at = NOW()
WHERE email = 'analista.uno@agencia.gob';
```

No se borran filas: el audit log debe poder referenciar la cuenta
históricamente.

---

## 5. Procedimientos críticos

### 5.1 Copia de seguridad de PostgreSQL

Backup cifrado con `pg_dump` + GPG:

```bash
docker compose exec -T db pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --format=custom \
  | gpg --encrypt --recipient backup@operador.local \
  > /var/backups/gi/$(date +%Y%m%d-%H%M)-pg.dump.gpg
```

Frecuencia recomendada: cada 6 horas en producción, retención mínima
30 días, almacenamiento secundario en sitio físico distinto.

### 5.2 Copia de seguridad de volúmenes Docker

```bash
docker run --rm \
    -v gi_postgres_data:/data:ro \
    -v /var/backups/gi:/backup \
    alpine \
    tar czf /backup/$(date +%Y%m%d)-pg-volume.tar.gz -C /data .
```

Repetir para `gi_redis_data`, `gi_ollama_data`.

### 5.3 Restauración

1. Detener la plataforma: `docker compose down`.
2. Restaurar el volumen Postgres a partir del tarball o crear uno
   limpio y restaurar desde el `pg_dump`:

   ```bash
   gpg --decrypt /var/backups/gi/<fichero>.dump.gpg \
     | docker compose exec -T db pg_restore \
         -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists
   ```

3. Verificar la cadena del audit log antes de reabrir el servicio
   (sección 5.6).
4. Repoblar Ollama:

   ```bash
   docker compose up -d ollama
   docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M
   ```

5. Levantar el resto de servicios: `docker compose up -d`.

### 5.4 Rotación de claves

`SECRET_KEY` y `REFRESH_SECRET_KEY`:

1. Generar el nuevo valor: `openssl rand -hex 32`.
2. Editar `backend/.env`.
3. Reiniciar: `docker compose restart backend celery_worker`.
4. Consecuencia: todos los tokens JWT activos quedan invalidados;
   los usuarios deben volver a autenticarse. Coordinar con
   antelación.

`MFA_ENCRYPTION_KEY`:

> Cuidado. Esta clave protege los secretos TOTP existentes. Rotarla
> sin migrar los secretos invalida todos los enrollments MFA.

Procedimiento recomendado (rotación con migración):

1. Mantenimiento programado. Bloquear logins.
2. Exportar y descifrar todos los `mfa_secret_encrypted` con la
   clave actual (script de migración a desarrollar bajo P3).
3. Re-cifrar con la nueva clave.
4. Actualizar `MFA_ENCRYPTION_KEY` y reiniciar.

Como alternativa simple en P1: forzar reset MFA a todos los usuarios
y rotar la clave. Procede solo si la organización lo asume.

`MFA_CHALLENGE_SECRET`: rotación libre, invalida challenges en
vuelo (impacto mínimo, < 5 minutos por defecto).

### 5.5 Verificación periódica del audit log

Cron diario sugerido (3:00 hora local):

```bash
0 3 * * * docker compose exec -T backend python -m app.tools.audit_verify \
    --since "$(date -d '1 day ago' --iso-8601=seconds)" \
    || /usr/local/bin/alert-soc "AUDIT CHAIN BROKEN"
```

La verificación recorre la tabla de audit por orden de inserción y
recalcula la cadena de hash. Cualquier discrepancia se trata como
incidente de seguridad alta.

### 5.6 Verificación tras restauración

Tras una restauración desde backup, ejecutar la verificación de
integridad antes de levantar tráfico:

```bash
docker compose run --rm backend python -m app.tools.audit_verify --full
```

---

## 6. Monitorización

### 6.1 Healthchecks

| Servicio | Endpoint | Comportamiento esperado |
| --- | --- | --- |
| Backend | `GET /health` | 200 con `{"status": "ok"}`. |
| Backend (clasificado) | `GET /api/v1/classified/health` | 200 si MFA validado y Ollama alcanzable. |
| Postgres | `pg_isready` interno | 200. |
| Redis | `PING` | `PONG`. |
| Ollama | `GET /api/tags` | 200, lista no vacía. |

### 6.2 Logs centralizados

Recomendación de stack:

- Recolector: Vector o Fluent Bit como sidecar.
- Almacén: Elasticsearch + Kibana, Loki + Grafana, o Wazuh.
- Transporte: TLS mutuo al colector.

Etiquetar cada flujo con `service`, `env`, `org` y `severity`.

### 6.3 Alertas sugeridas

| Alerta | Condición | Severidad |
| --- | --- | --- |
| Cadena de audit rota | Verificación fallida (sección 5.5). | Crítica |
| Llamada externa con clasificación elevada | Evento `llm.dispatch` con `provider=openrouter` y `classification > PUBLIC`. | Crítica |
| Intentos de login fallidos | > 10 fallos por cuenta en 5 minutos. | Alta |
| Latencia Ollama | p95 > 30 s durante 10 minutos. | Media |
| Disco | < 15 % libre en cualquier volumen. | Alta |
| Backup ausente | No hay backup completado en últimas 24 h. | Alta |

---

## 7. Incident Response

### 7.1 Reporte de vulnerabilidad

Canal: `gustavolobatoclara@gmail.com`. Se recomienda envío cifrado
con GPG (clave pública por solicitud). Incluir reproductor mínimo,
versión afectada y propuesta de mitigación si procede.

Política. Divulgación responsable: 90 días desde la notificación al
mantenedor, ampliables si la mitigación requiere coordinación.

### 7.2 Sospecha de compromiso

1. Aislamiento.

   ```bash
   docker compose stop backend frontend celery_worker celery_beat
   ```

   Mantener Postgres y Redis activos en lectura para forensics.

2. Revocación masiva de tokens. Rotar `SECRET_KEY` y
   `REFRESH_SECRET_KEY`; al reinicio se invalidan todos los tokens
   en circulación.

3. Snapshot forense de volúmenes Docker antes de cualquier
   reparación.

4. Verificación integridad audit log:

   ```bash
   docker compose run --rm backend python -m app.tools.audit_verify --full
   ```

5. Cierre selectivo de cuentas potencialmente comprometidas:

   ```sql
   UPDATE users SET is_active = FALSE
   WHERE id IN (...);
   ```

6. Reset MFA forzado a todas las cuentas privilegiadas.

7. Análisis forense con el audit log y los registros centralizados.

8. Notificación a la autoridad competente según marco legal del
   operador (CNI / CCN-CERT, INCIBE-CERT u homólogo nacional).

### 7.3 Forensics con audit log

El audit log conserva, por evento:

- `event_id`, `event_type`, `timestamp` (UTC ISO 8601).
- `actor_id`, `actor_clearance`, `source_ip`, `user_agent`.
- `target_object`, `target_classification`.
- `metadata` (JSONB con detalles específicos).
- `prev_hash`, `entry_hash` (cadena SHA-256).

Consultas tipo:

```sql
-- Accesos clasificados por un usuario sospechoso
SELECT timestamp, event_type, target_object, target_classification
FROM audit_events
WHERE actor_id = '<uuid>' AND target_classification >= 2
ORDER BY timestamp DESC LIMIT 200;

-- Dispatch externos con clasificación elevada
SELECT *
FROM audit_events
WHERE event_type = 'llm.dispatch'
  AND metadata->>'provider' = 'openrouter'
  AND (metadata->>'classification')::int > 0;
```

---

## 7.4 BYPASSRLS maintenance role

La migración `0002_mfa_audit_chain` crea un rol Postgres
`app_bypass_rls` con los flags:

```
NOLOGIN BYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
```

Casos de uso autorizados (siempre fuera del runtime de la aplicación):

- Dumps forenses de solo lectura sobre `audit_events`.
- Migraciones de esquema que deben atravesar políticas RLS.
- Procedimientos GDPR/data-subject revisados por el área legal.
- Investigaciones sobre sospecha de corrupción de la cadena.

NUNCA usar `app_bypass_rls` para:

- Tráfico HTTP de la aplicación.
- Workers Celery, ETL programados, jobs operativos rutinarios.
- Scripts puntuales que "corrigen un valor" en producción sin
  análisis previo.

`app_bypass_rls` es `NOLOGIN`. Para realizar tareas puntuales se crea
un rol operador efímero que herede el bypass:

```sql
CREATE ROLE ops_alice LOGIN PASSWORD '<vault>' IN ROLE app_bypass_rls;
-- ... trabajo ...
REVOKE app_bypass_rls FROM ops_alice;
DROP ROLE ops_alice;
```

El trigger `audit_events_no_update_delete_trg` lee
`pg_roles.rolbypassrls` del rol conectado, por lo que el privilegio se
revoca atómicamente al hacer `REVOKE`.

## 7.5 Verificación remota del audit log

El endpoint admin protegido por MFA expone la verificación de la
cadena:

```bash
curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN_CON_MFA" \
     https://api.example.gov/api/v1/classified/admin/audit/verify
```

Respuesta esperada:

```json
{ "valid": true, "total_events": 134521, "broken_at": null, "last_hash": "9b3...e8a" }
```

Si `valid=false`, aplicar el procedimiento de la sección 7.2 (aislar
el backend y conservar Postgres en lectura para forensics).

Cron diario recomendado (3:15 UTC):

```cron
15 3 * * *  curl -fsS -H "Authorization: Bearer $OPS_TOKEN" \
            https://api.example.gov/api/v1/classified/admin/audit/verify \
            | jq -e '.valid == true' \
            || /usr/local/bin/alert-soc "AUDIT CHAIN BROKEN"
```

`OPS_TOKEN` debe pertenecer a una cuenta admin que haya completado un
intercambio MFA reciente (claim `mfa_verified=true`). Emitirlo y
rotarlo desde un bastión con hardware token.

## 8. Tareas periódicas resumidas

| Periodicidad | Tarea |
| --- | --- |
| Continua | Healthchecks por reverse proxy y orquestador. |
| Cada 6 h | Backup PostgreSQL cifrado. |
| Diaria | Verificación integridad audit log. |
| Semanal | Revisión de cuentas activas y privilegios. |
| Mensual | Test de restauración en entorno aislado. |
| Trimestral | Rotación de `SECRET_KEY` y `REFRESH_SECRET_KEY`. |
| Anual | Auditoría de dependencias y pen-test interno. |
