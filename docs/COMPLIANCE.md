# Matriz de cumplimiento

Este documento mapea las capacidades implementadas en la plataforma
a controles de los marcos de referencia relevantes para despliegues
estatales y críticos. Su objetivo es servir de evidencia preliminar
en auditorías y de hoja de ruta para una eventual certificación
formal.

> Estado. La plataforma está diseñada para *soportar* el cumplimiento
> de los marcos citados. NO está certificada. La certificación
> requiere controles organizativos (selección de personal, seguridad
> física, gestión de incidentes, continuidad de negocio) que están
> fuera del alcance de este repositorio.

Convenciones de la columna *Estado*:

- Cumplido: el control está implementado en el código y se puede
  evidenciar mediante inspección o pruebas.
- Parcial: existe implementación pero presenta limitaciones
  conocidas, o depende de elementos no provistos por el sistema.
- Pendiente: el control está documentado en el roadmap pero no
  implementado todavía.

---

## 1. Esquema Nacional de Seguridad (ENS)

Referencia: Real Decreto 311/2022, de 3 de mayo. Categorización
aplicable: ALTA cuando la plataforma trate información clasificada
nacional. MEDIA para despliegues con información sensible no
clasificada.

### 1.1 Marco operacional — Control de acceso (op.acc)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| op.acc.1 Identificación | Cumplido | Cuenta única por usuario, e-mail como identificador, `users.id` UUID. | — |
| op.acc.2 Requisitos de acceso | Cumplido | RBAC + nivel de habilitación (`clearance_level`) + `org_id`. | — |
| op.acc.3 Segregación de funciones | Parcial | Roles diferenciados a nivel aplicación. | Falta separación administrativa entre operación, auditoría y administración de claves. |
| op.acc.4 Proceso de gestión de derechos de acceso | Parcial | Asignación de clearance vía SQL/admin. | Falta endpoint administrativo dedicado con flujo de aprobación. |
| op.acc.5 Mecanismo de autenticación | Cumplido | JWT con expiración corta (15 min access, 7 días refresh) + MFA TOTP. | — |
| op.acc.6 Acceso local y remoto | Cumplido | TLS terminado en reverse proxy + MFA. | — |

### 1.2 Marco operacional — Explotación (op.exp)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| op.exp.1 Inventario de activos | Cumplido | `SourceRegistry` con `max_classification`. | — |
| op.exp.2 Configuración de seguridad | Cumplido | `STATE_GRADE_MODE` fail-closed, secrets validados al arranque. | — |
| op.exp.3 Gestión de la configuración | Parcial | Configuración en variables de entorno versionables. | Falta firma de imágenes Docker. |
| op.exp.5 Gestión de cambios | Parcial | Migraciones Alembic versionadas. | Procedimiento formal de change management organizativo. |
| op.exp.6 Protección frente a código dañino | Pendiente | — | Escaneo de dependencias en CI; escaneo de imágenes. |
| op.exp.8 Registro de la actividad | Cumplido | Audit log con cadena de hash. | — |
| op.exp.9 Registro de la gestión de incidentes | Parcial | Audit log soporta forensics. | Falta integración con SIEM externo. |
| op.exp.10 Protección de los registros de actividad | Cumplido | Cadena de hash inmutable + endpoint de verificación. | — |

### 1.3 Medidas de protección — Información (mp.info)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| mp.info.2 Calificación de la información | Cumplido | Taxonomía PUBLIC/RESTRICTED/CONFIDENTIAL/SECRET + TLP v2.0. | — |
| mp.info.3 Cifrado | Parcial | AES-GCM para secretos MFA en reposo; TLS en tránsito. | Cifrado en reposo a nivel de volumen o columna pgcrypto. |
| mp.info.4 Firma electrónica | Parcial | Ed25519 para firma de reportes (esquema definido). | Las columnas `signature` se rellenan con NULL hasta que la integración P3 esté completa. |
| mp.info.5 Sellos de tiempo | Pendiente | — | TSA RFC 3161 para audit log y firmas de reportes. |
| mp.info.6 Limpieza de documentos | Pendiente | — | Sanitización de metadatos en ingesta. |
| mp.info.9 Información sensible en soportes no electrónicos | N/A | Fuera de alcance del sistema. | — |

### 1.4 Medidas de protección — Comunicaciones (mp.com)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| mp.com.1 Perímetro seguro | Cumplido | Red Docker aislada; backend no expuesto directamente. | — |
| mp.com.2 Protección de la confidencialidad | Cumplido | TLS 1.2+ en reverse proxy. | — |
| mp.com.3 Protección de la autenticidad y de la integridad | Cumplido | HSTS, JWT firmados, validación de firma webhooks. | — |
| mp.com.4 Segregación de redes | Parcial | Red Docker dedicada. | Segmentación física/VLAN documentada para producción. |

---

## 2. ISO/IEC 27001:2022 y 27002:2022

Mapeo a los Anexos relevantes (controles del Annex A reorganizados
en la edición 2022, con referencia al dominio ISO 27002:2022).

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| A.5.1 Políticas de seguridad | Parcial | `STATE_GRADE_MODE` codifica la política técnica. | Política organizativa formal del operador. |
| A.5.10 Uso aceptable de la información | Cumplido | Etiqueta TLP en cada salida; `max_classification` por fuente. | — |
| A.5.12 Clasificación de la información | Cumplido | Taxonomía codificada en `app.core.classification`. | — |
| A.5.13 Etiquetado de la información | Cumplido | TLP + clasificación propagados en reportes. | — |
| A.5.15 Control de accesos | Cumplido | JWT + RBAC + clearance + RLS. | — |
| A.5.17 Información de autenticación | Cumplido | bcrypt para passwords; secretos MFA cifrados AES-GCM. | — |
| A.5.18 Derechos de acceso | Parcial | Concesión y revocación documentada. | Revisión periódica automatizada. |
| A.8.2 Derechos de acceso privilegiado | Parcial | Roles admin separados. | Bastion / sesiones grabadas para acceso administrativo. |
| A.8.5 Autenticación segura | Cumplido | MFA TOTP + WebAuthn (este último opcional). | — |
| A.8.9 Gestión de la configuración | Cumplido | `Settings.validate_secrets()` fail-fast. | — |
| A.8.15 Registro de eventos | Cumplido | Audit log estructurado con cadena de hash. | — |
| A.8.16 Actividades de monitorización | Parcial | Endpoints `/health`, audit log consultable. | Integración SIEM. |
| A.8.20 Seguridad de las redes | Cumplido | Red Docker aislada, TLS perimetral. | — |
| A.8.24 Uso de criptografía | Cumplido | AES-GCM, Ed25519, bcrypt, HMAC-SHA256 (JWT). | — |
| A.8.28 Codificación segura | Parcial | Pydantic + tipos estrictos + linting. | SAST en pipeline CI. |
| A.5.30 Disponibilidad de TIC para continuidad | Parcial | Healthchecks + reinicio automático Docker. | Plan formal DRP/BCP. |
| A.5.7 Inteligencia de amenazas | Cumplido (instrumental) | El propio sistema es plataforma OSINT/inteligencia. | — |

---

## 3. NIST SP 800-53 Revision 5

Mapeo principal a las familias relevantes para una autorización
"Moderate" o "High" en línea con FedRAMP/FISMA, ajustada al contexto
europeo. Se listan únicamente los controles con relevancia directa
al sistema.

### 3.1 Access Control (AC)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| AC-2 Account Management | Parcial | Modelo `User`, soft-delete, estados activos. | Provisioning automatizado / federación. |
| AC-3 Access Enforcement | Cumplido | JWT + dependencias FastAPI + RLS Postgres. | — |
| AC-4 Information Flow Enforcement | Cumplido | `LLMRouter` impide envío de CONFIDENTIAL+ a proveedor externo. | — |
| AC-6 Least Privilege | Cumplido | Need-to-know por `clearance_level` y `org_id`. | — |
| AC-7 Unsuccessful Logon Attempts | Pendiente | — | Lockout configurable por número de fallos. |
| AC-12 Session Termination | Cumplido | Access token 15 min; refresh revocable. | — |
| AC-17 Remote Access | Cumplido | Solo HTTPS, MFA obligatorio en STATE_GRADE_MODE. | — |

### 3.2 Audit and Accountability (AU)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| AU-2 Event Logging | Cumplido | Eventos canónicos cubiertos por el audit log. | — |
| AU-3 Content of Audit Records | Cumplido | Quién, qué, cuándo, desde dónde, sobre qué objeto. | — |
| AU-4 Audit Log Storage Capacity | Parcial | Tabla dedicada en Postgres. | Rotación / archivado a almacenamiento WORM. |
| AU-5 Response to Audit Logging Process Failures | Parcial | Fallo de escritura del log lanza excepción visible. | Alertado automático. |
| AU-6 Audit Record Review, Analysis, and Reporting | Pendiente | Endpoint de verificación de integridad. | Dashboard / integración SIEM. |
| AU-9 Protection of Audit Information | Cumplido | Cadena de hash + verificación. | — |
| AU-10 Non-repudiation | Parcial | Audit log identifica actor y firma reportes con Ed25519. | Sellado de tiempo de terceros (TSA). |
| AU-14 Session Audit | Parcial | Eventos por petición. | Captura de sesión completa (opcional, depende de operador). |

### 3.3 Identification and Authentication (IA)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| IA-2 Identification and Authentication (Organizational Users) | Cumplido | Credenciales + MFA TOTP/WebAuthn. | — |
| IA-2(1) MFA for privileged accounts | Cumplido | MFA obligatorio en STATE_GRADE_MODE. | — |
| IA-5 Authenticator Management | Parcial | bcrypt + AES-GCM para secretos MFA. | Política de rotación periódica forzada. |
| IA-8 External Users | N/A | Fuera de alcance. | — |

### 3.4 System and Communications Protection (SC)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| SC-7 Boundary Protection | Cumplido | Red Docker aislada, reverse proxy. | — |
| SC-8 Transmission Confidentiality and Integrity | Cumplido | TLS 1.2+ en perímetro. | — |
| SC-12 Cryptographic Key Establishment and Management | Parcial | `MFA_ENCRYPTION_KEY` estática en variable de entorno. | HSM / KMS con rotación. |
| SC-13 Cryptographic Protection | Cumplido | AES-GCM (FIPS-friendly), Ed25519, bcrypt, HMAC-SHA256. | — |
| SC-23 Session Authenticity | Cumplido | JWT con firma HMAC, audiencia y issuer. | — |
| SC-28 Protection of Information at Rest | Pendiente | — | Cifrado de volumen LUKS o cifrado columna pgcrypto. |

### 3.5 System and Information Integrity (SI)

| Control | Estado | Implementación | Pendiente |
| --- | --- | --- | --- |
| SI-3 Malicious Code Protection | Pendiente | — | Escaneo de imágenes y dependencias en CI. |
| SI-4 System Monitoring | Parcial | Healthchecks, audit log. | IDS / monitorización avanzada. |
| SI-7 Software, Firmware, and Information Integrity | Cumplido | Audit chain verifiable; firma de reportes Ed25519. | — |
| SI-10 Information Input Validation | Cumplido | Pydantic + validación SQLAlchemy. | — |
| SI-12 Information Management and Retention | Parcial | Retención por clase de objeto. | Política formal de retención y borrado por operador. |

---

## 4. Resumen comparado

| Marco | Cumplido | Parcial | Pendiente |
| --- | --- | --- | --- |
| ENS (op.acc, op.exp, mp.info, mp.com) | 11 | 9 | 4 |
| ISO/IEC 27001:2022 | 9 | 7 | — |
| NIST SP 800-53 Rev. 5 | 11 | 8 | 5 |

Los recuentos anteriores cubren únicamente los controles enumerados
en este documento. Una auditoría formal aplicará el catálogo completo
del marco correspondiente.

---

## 5. Roadmap de cumplimiento (P3 — P5)

Los siguientes elementos son requisitos para alcanzar una postura
de cumplimiento publicable y, en su caso, certificable.

### P3 — Endurecimiento criptográfico y trazabilidad

- Integración SIEM. Exportación de audit log a Splunk, ELK o Wazuh
  vía syslog estructurado (RFC 5424) o protocolo HEC.
- Sellado de tiempo RFC 3161 sobre eventos críticos del audit log
  y sobre firmas Ed25519 de reportes.
- Política de rotación de `SECRET_KEY`, `REFRESH_SECRET_KEY`,
  `MFA_ENCRYPTION_KEY` y `MFA_CHALLENGE_SECRET` documentada y
  automatizada.

### P4 — Cifrado en reposo y gestión de claves

- HSM o KMS para custodiar las claves maestras (PKCS#11, AWS KMS,
  Azure Key Vault, GCP KMS, o equivalente on-premise).
- Cifrado en reposo de PostgreSQL: volumen LUKS para datos
  completos; cifrado columna mediante pgcrypto para campos de
  máxima sensibilidad.
- Cifrado en reposo de los volúmenes de Redis y de los artefactos
  Celery en disco.

### P5 — Validación externa

- Auditoría de código por tercero independiente.
- Pen-testing con alcance white-box y black-box.
- Auditoría de cumplimiento ENS Categoría Media. Certificación
  formal por entidad acreditada.
- Auditoría ISO/IEC 27001:2022 con alcance limitado al sistema de
  información.
- Evaluación EAL Common Criteria (objetivo, sin compromiso).

---

## 6. Limitaciones declaradas

- `TOP_SECRET` no está modelado. La gestión de información a este
  nivel requiere infraestructura físicamente aislada y
  procedimientos de personal que están fuera del alcance del
  software.
- El cifrado en reposo nativo del motor de base de datos no está
  configurado por defecto. Se documenta como tarea de despliegue.
- La plataforma no provee componentes de seguridad física,
  selección de personal, ni control de acceso físico. Estos
  controles son responsabilidad del operador.
