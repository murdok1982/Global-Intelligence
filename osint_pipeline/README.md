# Pipeline OSINT Standalone — ATALAYA

> Generador autónomo de informes de inteligencia geopolítica semanal.
> Opera 100% en local con LLM propio (Ollama/Gemma 4B).

---

## Descripción

Este pipeline standalone complementa la plataforma web Global Intelligence
proporcionando un sistema de generación autónoma de informes estratégicos
bilingües (ES/EN) con metodología PMESII-PT.

### Capacidades

| Capacidad | Descripción |
|-----------|-------------|
| LLM Local | Motor Gemma 4B vía Ollama — sin API key, sin coste |
| OSINT RSS | 30 fuentes globales: Reuters, BBC, RAND, SIPRI, Jane's... |
| YouTube OSINT | 10 canales de analistas (CSIS, Stratfor, CFR...) |
| GDELT v2 | Base de datos de eventos globales |
| Informes bilingües | Markdown ES/EN con análisis + previsiones 6m/1a/3a |
| SSRF protegido | Bloqueo de IPs privadas en peticiones HTTP |

---

## Instalación rápida

```bash
# Clonar repositorio
git clone https://github.com/murdok1982/Global-Intelligence.git
cd Global-Intelligence/osint_pipeline

# Ejecutar instalador automático
chmod +x setup.sh
./setup.sh
```

El script `setup.sh` realiza:
1. Instalación de dependencias Python
2. Verificación/instalación de Ollama
3. Descarga del modelo gemma4:4b (~3.5 GB)
4. Creación del perfil ATALAYA (analista militar)

---

## Ejecución

```bash
# Activar entorno virtual (si no está activo)
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Generar informe
python main.py
```

Salida esperada:
```
Proveedor LLM: OLLAMA | Modelo: atalaya-geoint
Fuentes activas: gdelt, rss, youtube
Países a analizar: 23
Período: últimos 7 días

Recolectando y analizando países...
100%|████████████████████| 23/23 [12:34<00:00, 32.8s/país]

Informe generado: outputs/reporte_inteligencia_global_20260608.md
```

---

## Cobertura geográfica

### 23 países en 6 regiones estratégicas

| Región | Países |
|--------|--------|
| Norteamérica | US, CA |
| América Latina | MX, BR, AR |
| Europa Occidental | GB, FR, DE |
| Europa del Este | RU, UA |
| Asia Oriental | CN, JP, KR |
| Asia del Sur | IN, PK |
| Oriente Medio | SA, IR, IL, TR, EG |
| África | ZA, NG |
| Oceanía | AU |

---

## Fuentes OSINT

### 30 fuentes RSS clasificadas por fiabilidad NATO

| Fiabilidad | Fuentes |
|------------|---------|
| **A** (Completa) | Reuters, BBC, FT, RAND, SIPRI, Chatham House, CFR, Brookings, IISS, Jane's, Defense News, War on the Rocks, Lawfare, Foreign Affairs, Foreign Policy, AP News, El País, Al Jazeera, DW, France24, The Guardian, The Diplomat, ISS Africa |
| **B** (General) | Bellingcat, Middle East Eye, Real Vision |
| **C** (Moderada) | RT, Xinhua, TASS |

### 10 canales YouTube OSINT

CSIS, CFR, Chatham House, BBC Mundo, DW Español, France 24 ES, Stratfor, Real Vision, Al Jazeera EN, RAND Corporation

---

## Metodología PMESII-PT

El perfil ATALAYA aplica el marco analítico estándar NATO:

| Dimensión | Análisis |
|-----------|----------|
| **P**olítico | Gobierno, actores, estabilidad |
| **M**ilitar | FFAA, doctrina, capacidades |
| **E**conómico | PIB, comercio, sanciones, deuda |
| **S**ocial | Demografía, tensiones, cohesión |
| **I**nfraestructura | Energía, telecomunicaciones |
| **I**nformación | Medios, narrativas, desinformación |
| **T**iempo | Contexto histórico |
| **T**erreno | Geografía estratégica |

---

## Estructura del informe

```
INFORME DE INTELIGENCIA ESTRATÉGICA GLOBAL
Clasificación: ABIERTO | Período: últimos 7 días
Motor: OLLAMA / atalaya-geoint

VERSIÓN ESPAÑOL
├── Resumen Ejecutivo (10-14 líneas + riesgos/oportunidades)
├── Síntesis Regional (6 regiones)
├── Análisis por País (23 países)
│   ├── Economía
│   ├── Seguridad Interior
│   ├── Defensa
│   ├── Inteligencia & Diplomacia
│   └── Previsión 6m / 1a / 3a
└── Panorama Global y Previsiones

ENGLISH VERSION
├── Executive Summary
├── Regional Synthesis
├── Country Analysis (23 countries)
└── Global Outlook & Forecasts
```

---

## Configuración

### `.env`
```bash
LLM_PROVIDER=ollama          # ollama | openai | auto
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=atalaya-geoint  # o gemma4:4b para el modelo base
# OPENAI_API_KEY=sk-...      # opcional
```

### `config.yaml`
```yaml
run:
  days_back: 7               # Ventana temporal (días)
  per_country_limit: 20      # Artículos máx. por país
  providers: ["gdelt", "rss", "youtube"]

llm:
  temperature: 0.3           # Precisión analítica
  max_tokens: 2000

report:
  classification: ABIERTO    # ABIERTO | RESTRINGIDO | CONFIDENCIAL
```

---

## Docker

```bash
# Primera vez — descarga modelo (~3.5 GB)
docker compose --profile ollama-init up

# Ejecuciones sucesivas
docker compose --profile run up
```

---

## Seguridad

- Sin API keys obligatorias — Ollama corre completamente en local
- Protección SSRF — bloqueo de rangos RFC 1918
- Sin telemetría — cero datos enviados a terceros en modo Ollama
- Air-gap compatible — tras instalación inicial funciona sin internet

---

## Licencia

MIT License — ver [LICENSE](../LICENSE)
