# Desarrollo del primer corte

Estado: implementación inicial de desarrollo. El servicio mantiene estado en memoria;
reiniciarlo elimina sesiones y cambios realizados en ese proceso.

## Verificación sin cuentas ni gasto

Desde la raíz del repositorio:

```bash
uv sync
uv run oif verify-example
uv run pytest -q
uv run ruff check src/oif tests
```

La verificación usa sockets reales para el servicio HTTP y MCP Streamable HTTP.
Comprueba dos especializaciones, una corrección común, errores consistentes, aislamiento,
revocación y memoria navegable. Su modelo programado conduce llamadas conocidas: no
demuestra razonamiento ni una integración con correo o Databricks. Los servidores
temporales se cierran al terminar.

## Conversación con OpenAI

El autor eligió API personal de OpenAI. El adapter usa Responses API con funciones
ejecutadas por el servicio. La credencial queda fuera del protocolo del agente y de
los MCP. Las solicitudes usan `store: false` y conservan el estado opaco necesario para
continuar llamadas a herramientas en memoria del servidor. Esto no promete retención
cero en todos los sistemas del proveedor. Referencias: [function calling](https://developers.openai.com/api/docs/guides/function-calling),
[estado de Responses](https://developers.openai.com/api/docs/guides/migrate-to-responses).

Primero inicia el MCP del ejemplo en una terminal:

```bash
uv run oif example-mcp
```

En la terminal del servicio, configura estas variables mediante entrada oculta o tu
gestor de secretos. [`.env.example`](../.env.example) contiene nombres y valores vacíos;
la aplicación no carga archivos `.env` automáticamente.

| Variable | Uso |
|---|---|
| `OPENAI_API_KEY` | API key personal del adapter de modelo; nunca se pasa al MCP. |
| `OIF_OPENAI_MODEL` | Modelo disponible en tu cuenta, obligatorio y sin valor predeterminado. |
| `OIF_IDENTITY_ENV_MAP` | Mapa identidad → nombre de variable; ejemplo: `{"alice":"OIF_TOKEN_ALICE","bob":"OIF_TOKEN_BOB"}`. |
| `OIF_TOKEN_ALICE`, `OIF_TOKEN_BOB` | Tokens privados distintos para las identidades sintéticas. No son cuentas reales ni OIDC. |

No introduzcas credenciales como argumentos de comandos ni en el chat. Para recibir
la API key con entrada oculta y lanzar el servicio con el resto del entorno ya configurado:

```bash
uv run python -c 'import getpass, os; from oif.cli import main; os.environ["OPENAI_API_KEY"] = getpass.getpass("API key personal de OpenAI: "); raise SystemExit(main(["serve", "--config", "examples/atlas.json"]))'
```

Si la clave ya está disponible en el entorno del servicio:

```bash
uv run oif serve --config examples/atlas.json
```

El servicio escucha en `127.0.0.1:8765`; el MCP de ejemplo en `127.0.0.1:8011/mcp`.
Son componentes de desarrollo de la arquitectura compartida; no se ha elegido un
alojamiento ni desplegado servicios externos.

En otra terminal inicia el cliente:

```bash
uv run oif chat --server http://127.0.0.1:8765 --agent costs-agent
```

El CLI pide el token mediante entrada oculta si `OIF_ACCESS_TOKEN` no está configurado.
Usa el de Alice para costos y el de Bob para contratos; el servidor verifica identidad
y membresías, no un nombre elegido por el cliente.

Con el modelo configurado, puedes pedir: «Revisá las convenciones de nuestro proyecto
y resumí los costos disponibles» o «Explorá la memoria que podés consultar». Para
contratos usa `--agent contracts-agent` con su token.

El cliente muestra la sesión. `--session ID` la retoma mientras el proceso servidor
siga activo. `Ctrl+C` intenta cancelar el turno y `Ctrl+D` termina la conversación;
cancelar no deshace operaciones completadas.

## Memoria navegable

El manifiesto sintético define este árbol. El servicio calcula la visibilidad en cada
acceso; el modelo recibe solo las entradas autorizadas.

```text
/
├── comun/
│   └── convenciones.md
├── proyectos/
│   ├── costos/
│   │   ├── proceso.md
│   │   └── borrador.md      (fuera de la navegación habitual)
│   └── contratos/
│       └── proceso.md
└── personas/
    └── alice/
        └── preferencias.md
```

`listar_memoria` y `leer_memoria` son herramientas internas del servicio. El agente elige
cuándo navegar. Las rutas son nodos del repositorio virtual, no archivos del equipo.
Los permisos se restringen por ancestro, organización, proyecto e identidad y deben
admitir a solicitante y audiencia. Una denegación y una ruta inexistente dan el mismo error.

Este corte ofrece listado y lectura. `replace_node` es configuración interna de confianza,
usada en tests para cambiar contenido y permisos; no es una herramienta del agente.
Esos cambios incrementan la revisión y descartan el historial anterior antes de volver
a enviarlo al modelo. Se reevalúan también las membresías. Cambios durante una llamada
al modelo abortan la entrega de la respuesta anterior. No se eliminan copias ya entregadas.

## Componentes y límites

Los contratos independientes del proveedor están en `domain.py` y `ports.py`.
`service.py` y `registry.py` aplican autoridad y versiones; `memory.py` implementa el
repositorio; `mcp_client.py` conecta MCP; `runtime.py` conduce el ciclo; `models.py`
encapsula OpenAI; `api.py`, `auth.py` y `cli.py` componen servidor y cliente.

La API expone salud, agentes autorizados, creación/lectura de sesiones, mensajes y
cancelación. No hay rutas para conceder permisos, publicar versiones o cambiar credenciales.
El servicio fija `project_id` y `limit` del MCP desde el manifiesto confiable. Valida
schemas de entrada/salida; descripciones remotas no conceden autoridad. Una credencial
de conexión usa un nombre `OIF_MCP_*` autorizado en `OIF_MCP_TOKEN_ENVS`.

Faltan persistencia durable, login productivo, operación multiusuario de producción,
edición y publicación de memoria, conectores externos personales, alertas programadas
y evaluación del razonamiento con un modelo real. El manifiesto precargado no es un
workflow editorial. No se usaron sistemas ni credenciales laborales para implementar.
