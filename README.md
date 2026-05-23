# EcoSeek Client

Cliente local para EcoSeek — scientific agent environment for ecology.

EcoSeek es un agente AI que ejecuta flujos de trabajo ecologicos (SDM,
modelado de nicho, analisis filogenetico, diversidad) con trazabilidad
completa. El cliente se conecta a un AgenticPlug gateway que enruta
tareas a Hermes (orquestador central con skills, memoria y multi-provider)
corriendo en un servidor remoto.

---

## Verificacion del contrato

| Item | Estado |
|------|--------|
| `pip install -e .` | OK |
| `ecoseek doctor` | OK — diagnostico completo |
| `ecoseek agenticplug whoami` | OK — identidad del connector |
| `ecoseek agenticplug clusters` | OK — lista de clusters |
| `ecoseek smoke remote` | OK — 5-step health check |
| `ecoseek hermes whoami` | OK — conectividad con Hermes |
| `ecoseek hermes orchestrate` | OK — tarea orquestada completa |
| Conexion laptop → Hermes en reumanlab | OK — via AgenticPlug (:3100) |

---

## Arquitectura

```
Laptop / WSL / workstation
└── ecoseek-client (MIT)
    ├── CLI (hermes, aar, smoke, agenticplug, doctor)
    ├── AgenticPlugClient → AgenticPlug (:3100)
    │   └── GitHub Device Flow auth
    │       └── Hermes (:8642)
    │           ├── DeepSeek v4 Pro (primary)
    │           ├── OpenCode Go (fallback)
    │           ├── Skills (SDM, connectivity, niche, climate)
    │           ├── Memory (ecosystem knowledge)
    │           └── Tools (terminal, web, GitHub, delegate_task)
    └── AAR Loop (observe→reason→act→evaluate→update)
```

### ¿Por que Hermes via AgenticPlug y no directo?

| Sin AgenticPlug | Con AgenticPlug |
|----------------|-----------------|
| API key en cada laptop | Una sola API key en el server |
| Sin control de acceso | GitHub Device Flow auth |
| Sin rate limiting | Rate limiting por sesion |
| Sin trazabilidad | Audit log completo |
| Hermes expuesto directamente | Hermes detras del gateway |

---

## Instalacion

### Requisitos

- Linux (WSL2, Ubuntu) o macOS
- Python 3.11+
- Git
- Acceso a un AgenticPlug gateway (reumanlab o local)

### Instalacion rapida

```bash
git clone https://github.com/alrobles/ecoseek-client
cd ecoseek-client
pip install -e .
```

### Configuracion

Copiar y editar el archivo de entorno:

```bash
cp .env.example .env
```

Variables minimas:

```env
AGENTICPLUG_URL=http://127.0.0.1:3100
AGENTICPLUG_SESSION=<tu-session-id>
```

Para usar con el gateway de reumanlab via Cloudflare tunnel, contactar
al administrador para obtener credenciales.

### Verificar instalacion

```bash
ecoseek doctor
```

Debe mostrar:

```
AgenticPlug
  connector: http://127.0.0.1:3100 (healthy)
  auth: configured
Hermes
  provider: hermes (connected)
```

---

## Comandos

### Diagnostico

```bash
ecoseek doctor                 # Diagnostico completo del entorno
ecoseek smoke remote           # Health check de toda la cadena
```

### AgenticPlug

```bash
ecoseek agenticplug whoami     # Verificar identidad
ecoseek agenticplug clusters   # Listar clusters disponibles
ecoseek agenticplug task ...   # Enviar tarea al gateway
```

### Hermes (orquestador)

```bash
ecoseek hermes whoami                      # Conectividad con Hermes
ecoseek hermes orchestrate "tarea"         # Tarea orquestada completa
ecoseek hermes chat "pregunta"             # Chat directo con Hermes
```

### Skills cientificos

```bash
ecoseek skill list              # 5 skills ecologicos disponibles
ecoseek skill show sdm          # Pipeline de SDM completo
```

### AAR Loop (Adaptive Agentic Retrieval)

```bash
ecoseek aar run "pregunta"      # Ejecutar loop AAR
ecoseek aar status              # Capacidades del loop
```

---

## Estructura del proyecto

```
ecoseek-client/
├── src/ecoseek_client/
│   ├── providers/          # AgenticPlug, Hermes clients
│   ├── aar/                # Adaptive Agentic Retrieval loop
│   ├── skills/             # Definiciones de skills ecologicos
│   ├── workflows/          # Remote smoke + diagnosticos
│   ├── cli.py              # CLI entrypoint
│   ├── config.py           # Configuracion (.env)
│   ├── doctor.py           # Diagnostico del entorno
│   └── session.py          # Manejo de sesiones
├── tests/                  # Test suite (11/12 pasando)
├── docs/                   # Documentacion
├── pyproject.toml          # Package metadata (MIT)
├── LICENSE                 # MIT License
└── CHANGELOG.md            # Historial de versiones
```

---

## Estado del proyecto

**Version actual:** 0.1.0 (pre-alpha)
**Estado del prototipo:** Funcional — el cliente se conecta a Hermes via AgenticPlug

### Lo que funciona

- CLI completa con 6 grupos de comandos
- Conexion a AgenticPlug con GitHub Device Flow
- Orquestacion via Hermes (skills, memoria, multi-provider)
- Loop AAR (observe→reason→act→evaluate→update)
- Smoke test de 5 pasos
- 5 skills ecologicos (SDM, conectividad, nicho, clima)

### Backend pendiente (pre-piloto)

Ver [docs/audit-2026-05-22.md](docs/audit-2026-05-22.md) para el backlog
completo del backend. Los gaps criticos identificados por Devin:

1. Session lifecycle hardening
2. Audit logging con correlation IDs
3. Secret handling at rest
4. Role model documentation
5. Rate limiting per-identity
6. TLS posture review

---

## Documentacion

- [Guia de instalacion (WSL)](docs/install-wsl.md)
- [Conectar a AgenticPlug](docs/agenticplug.md)
- [Primer tarea](docs/hello-world.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Arquitectura](docs/architecture.md)
- [Plan de migracion](docs/migration-inventory.md)
- [Auditoria completa](docs/audit-2026-05-22.md)
- [CHANGELOG](CHANGELOG.md)

---

## Licencia

MIT License. Ver [LICENSE](LICENSE).

EcoSeek Client es un proyecto independiente. Agradecemos al proyecto
[AgenticSeek](https://github.com/Fosowl/agenticSeek) (GPLv3) como
inspiracion para el diseno del agente local. EcoSeek Client no contiene
codigo derivado de AgenticSeek y tiene licencia MIT.
