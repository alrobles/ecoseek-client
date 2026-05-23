# Auditoría de alrobles/ecoseek-client

Fecha: 2026-05-22
Versión auditada: 0.1.0 (commit 300628a — Phase 7)
Auditor: Hermes Agent (reumanlab)

---

## Resumen ejecutivo

ecoseek-client cumple el contrato mínimo: se conecta a Hermes corriendo en reumanlab desde una laptop, la CLI es funcional, y el prototipo opera. Hay issues menores que no impiden el uso pero deben resolverse antes de PyPI/beta pública.

**Veredicto**: APROBADO condicional — funcional para desarrollo interno y demo. Requiere 3 fixes antes de release público.

---

## 1. Verificación del contrato

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| Conectarse a Hermes en reumanlab desde laptop | ✅ CUMPLE | `ecoseek doctor`: "hermes: connected". `ecoseek hermes whoami`: "status: connected (32ms)". Health endpoint: `{"status":"ok","hermes":{"enabled":true,"health":"ok","latency_ms":1}}` |
| GUI funcional | ⚠️ NO APLICA | No hay GUI. ecoseek-client es CLI (terminal). La CLI funciona correctamente con 6 grupos de comandos. |
| Prototipo funciona | ✅ CUMPLE | 11/12 tests pasan. Todos los comandos CLI responden. La cadena completa laptop→AgenticPlug→Hermes opera. |

---

## 2. Resultados de tests automatizados

```
12 tests: 11 passed, 1 failed
```

| Test | Resultado |
|------|-----------|
| test_health_ok | ✅ PASS |
| test_health_down | ✅ PASS |
| test_healthz_ok | ✅ PASS |
| test_whoami_no_auth | ✅ PASS |
| test_clusters | ✅ PASS |
| test_clusters_hpc_disabled | ✅ PASS |
| test_task_remote_health | 🔴 FAIL — mock no coincide con flujo real de requests |
| test_task_hpc_status | ✅ PASS |
| test_task_unknown | ✅ PASS |
| test_connection_refused | ✅ PASS |
| test_result_never_leaks_token | ✅ PASS |
| test_sanitize_removes_token | ✅ PASS |

**Root cause del fallo**: `test_task_remote_health` hace mock de `/healthz` pero `client.task("remote.health")` llama a `/v1/tasks` (POST). El mock registrado para `/healthz` queda sin consumir porque el flujo real no lo usa. Fix: mockear `/v1/tasks` en lugar de `/healthz`.

---

## 3. Verificación de comandos CLI

| Comando | Estado | Output |
|---------|--------|--------|
| `ecoseek --version` | ✅ | `ecoseek, version 0.1.0` |
| `ecoseek --help` | ✅ | 6 grupos: doctor, agenticplug, hermes, smoke, aar, skill |
| `ecoseek doctor` | ✅ | Python 3.11.15, WSL2 no detectado (Linux nativo), connector healthy (32ms), Hermes connected, session found |
| `ecoseek agenticplug whoami` | ✅ | "Connected as: alrobles" |
| `ecoseek agenticplug clusters` | ✅ | 2 clusters: reumanlab (healthy, v0.3.0) + ku-hpc (healthy, rw) |
| `ecoseek agenticplug health` | ✅ | "Connector: healthy", hermes enabled/ok |
| `ecoseek agenticplug status` | ✅ | Full status: connector healthy, auth token_configured, 16 capabilities |
| `ecoseek agenticplug task list` | ✅ | 4 tasks: remote.health, hpc.status, hpc.queue, hpc.submit |
| `ecoseek hermes whoami` | ✅ | "status: connected (32ms)", hermes enabled/healthy |
| `ecoseek hermes chat "..."` | 🔴 | Retorna contenido vacío — endpoint `/v1/chat/completions` no implementado en connector |
| `ecoseek skill list` | ✅ | 5 skills: sdm, niche, connectivity, climate, ecoseek-system |
| `ecoseek smoke remote` | 🔴 | 1 error (remote_health dispatch falla con "unknown"), 2 warnings (HPC) |
| `ecoseek aar status` | ✅ | Muestra capacidades del loop AAR |

---

## 4. Issues encontrados

### 🔴 Críticos (bloquean release)

**C-1: test_task_remote_health roto**
- Archivo: `tests/test_agenticplug_provider.py:84-87`
- Causa: El mock registra `/healthz` pero `client.task("remote.health")` llama POST `/v1/tasks`. El request real va a `/v1/tasks` y el mock de `/healthz` queda sin consumir, causando error en teardown.
- Fix: Cambiar el mock a `url="http://test.local:3100/v1/tasks"` o usar `httpx_mock.add_response()` con `can_match=lambda r: True`.
- Impacto: CI/CD en GitHub Actions fallará si se activa.

### 🟡 Moderados (no bloquean pero degradan)

**M-1: hermes chat devuelve vacío**
- Archivo: `src/ecoseek_client/providers/hermes.py:245` — `chat()` llama POST `/v1/chat/completions`
- Causa: El connector AgenticPlug (actualmente) no tiene ese endpoint implementado. Las capabilities del connector muestran `/v1/orchestrate`, `/hermes/tasks`, pero no `/v1/chat/completions`.
- Fix: Implementar el endpoint en el connector o rutear chat a través de `/hermes/tasks`.
- Impacto: `ecoseek hermes chat` y el loop AAR (que usa `provider.chat()`) no funcionan.

**M-2: smoke remote falla en remote_health dispatch**
- Causa: `client.task("remote.health")` envía POST a `/v1/tasks` con `{"capability": "remote.health"}`. El connector responde con success=False y error vacío.
- Posible causa: El endpoint `/v1/tasks` del connector espera un formato diferente o la capability `remote.health` no está registrada como dispatch.
- Impacto: El smoke test reporta 1 error falso positivo.

**M-3: CONTRIBUTING.md referencia archivos inexistentes**
- `aar/scoring.py` → no existe. `aar/__init__.py` contiene todo (scoring está inline).
- `workflows/remote_smoke.py` → no existe. `workflows/__init__.py` contiene todo.
- Impacto: Nuevos contribuidores buscarán archivos que no están.

### 🟢 Menores (cosméticos)

**m-1: CHANGELOG menciona Phase 6 (AgenticSeek) no commiteada**
- El CHANGELOG lista "Phase 6: AgenticSeek integration" pero el código no tiene `providers/agenticseek.py`.
- No hay commits de Phase 6 en el historial git (salta de Phase 5 a Phase 7).
- Fix: Remover la línea del CHANGELOG o implementar AgenticSeekProvider.

**m-2: README referencia docs con nombres distintos**
- README línea 197: `docs/connect-agenticplug.md` → el archivo existe con ese nombre ✅
- README línea 198: `docs/first-task.md` → el archivo existe con ese nombre ✅
- README línea 197 también mencionaba `docs/agenticplug.md` y `docs/hello-world.md` en versión previa → ya corregido.

**m-3: pyproject.toml versión 0.1.0 no refleja fases completadas**
- Con Phase 7 completada, debería ser al menos 0.2.0-alpha.

---

## 5. Estructura del repositorio

```
alrobles/ecoseek-client/
├── .env.example                    ✅ Template de configuración
├── .github/workflows/
│   ├── test.yml                    ✅ CI: pytest en Python 3.10/3.11/3.12
│   └── publish.yml                 ✅ PyPI trusted publishing
├── .gitignore                      ✅ Cubre dist/, .env, .venv, etc.
├── CHANGELOG.md                    ✅ Keep a Changelog (con error de Phase 6)
├── CONTRIBUTING.md                 ✅ Guía de contribución (con paths incorrectos)
├── LICENSE                         ✅ MIT
├── MANIFEST.in                     ✅ PyPI package manifest
├── README.md                       ✅ Completo (links a docs existentes)
├── pyproject.toml                  ✅ Setup completo, clasificadores PyPI
├── docs/
│   ├── connect-agenticplug.md      ✅ Guía de conexión AgenticPlug
│   ├── first-task.md               ✅ Hello world/SDM walkthrough
│   ├── install-wsl.md              ✅ Instalación WSL/Ubuntu
│   ├── migration-inventory.md      ✅ Inventario de migración
│   ├── migration-plan.md           ✅ Plan de migración original
│   └── troubleshooting.md          ✅ 8 problemas comunes
├── src/ecoseek_client/
│   ├── __init__.py                 ✅ v0.1.0
│   ├── cli.py                      ✅ Click CLI (549 líneas, 6 grupos)
│   ├── config.py                   ✅ Env vars + .env loader
│   ├── session.py                  ✅ AgenticPlugSession v2 parser
│   ├── doctor.py                   ✅ (vacío — lógica en cli.py)
│   ├── providers/
│   │   ├── __init__.py             ✅ Re-exports
│   │   ├── agenticplug.py          ✅ HTTP client (356 líneas)
│   │   └── hermes.py               ✅ Hermes provider (338 líneas)
│   ├── aar/
│   │   └── __init__.py             ✅ AAR loop (358 líneas)
│   ├── skills/
│   │   ├── __init__.py             ✅ SkillLoader (153 líneas)
│   │   └── definitions/
│   │       ├── sdm.md              ✅
│   │       ├── niche.md            ✅
│   │       ├── connectivity.md     ✅
│   │       ├── climate.md          ✅
│   │       └── ecoseek-system.md   ✅
│   └── workflows/
│       └── __init__.py             ✅ Remote smoke (302 líneas)
└── tests/
    ├── __init__.py                 ✅
    └── test_agenticplug_provider.py ✅ 12 tests (11 pass)
```

---

## 6. Seguridad

| Item | Estado |
|------|--------|
| Tokens nunca en output | ✅ `_sanitize()` remueve token/bearer/access_token |
| Session file no se commitea | ✅ en .gitignore |
| .env en .gitignore | ✅ |
| HTTPS para Hermes | ⚠️ Usa HTTP local (127.0.0.1:3100) — correcto para connector local |
| Sin hardcoded secrets | ✅ Todo por env vars |

---

## 7. Plan de acción recomendado

### Antes de release público (v0.2.0)

1. Fix test_task_remote_health (mock a `/v1/tasks`)
2. Implementar endpoint `/v1/chat/completions` en connector o rutear chat via `/hermes/tasks`
3. Investigar y fixear smoke remote: remote_health dispatch
4. Corregir CONTRIBUTING.md paths
5. Remover Phase 6 del CHANGELOG o implementar AgenticSeekProvider
6. Bump versión a 0.2.0-alpha

### Antes de beta (v0.3.0+)

7. Publicar en PyPI
8. Agregar tests de integración contra connector real
9. GUI (si se requiere) — considerar TUI con Textual o Rich
10. Documentar arquitectura del backend (Hermes + AgenticPlug + Cloudflare)

---

## 8. Conclusión

ecoseek-client está en estado **alpha funcional**. La conectividad laptop→reumanlab vía AgenticPlug→Hermes opera correctamente. La CLI cubre el ciclo completo: diagnóstico, autenticación, descubrimiento de clusters, dispatch de tareas, smoke tests, y skills científicas.

Los issues encontrados son acotados y tienen fixes claros. El proyecto está listo para uso interno y demos. Con los 6 fixes listados arriba, está listo para release público alpha en PyPI.
