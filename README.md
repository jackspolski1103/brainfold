# OIF — cerebro compartido para agentes

Proyecto personal e independiente, con intención open source. **OIF es un nombre provisional.** Todavía no hay repositorio remoto ni licencia elegida.

OIF es un servidor MCP que convierte una carpeta en el cerebro compartido de un equipo: archivos con permisos que cualquier harness (Claude Code, Codex u otro) lee y escribe. El alcance completo, incluido lo que deliberadamente no hace, está en [docs/scope.md](docs/scope.md).

## Estado

Implementación de desarrollo. Funcionan el servidor MCP sobre una carpeta en disco, los permisos de lectura y escritura por carpeta, el descubrimiento de skills, las cuentas con email y contraseña, los tokens por persona, los grupos, el registro de actividad y la API del panel. **La interfaz web todavía no existe**; por ahora la API se usa con `curl`. El servidor solo escucha en loopback. Los datos de ejemplo son sintéticos.

## Probarlo

```bash
uv sync
uv run oif serve --root examples/brain        # cuentas y actividad en ./oif.db

# En otra terminal: crear el administrador, un grupo y un token de harness.
J='Content-Type: application/json'; U=http://127.0.0.1:8020
curl -c cookies.txt -H "$J" -d '{"email":"vos@ejemplo.com","password":"una-clave-larga"}' $U/api/setup
curl -b cookies.txt -X PUT -H "$J" -d '{"members":["vos@ejemplo.com"]}' $U/api/groups/costs
curl -b cookies.txt -H "$J" -d '{"name":"claude code"}' $U/api/tokens   # muestra el token una vez

claude mcp add --transport http oif $U/mcp --header "Authorization: Bearer <token>"
```

Herramientas MCP: `listar_memoria`, `leer_memoria`, `escribir_memoria`, `buscar_memoria`, `listar_skills`.

## Formato del cerebro

Cada carpeta puede tener un `.oif.toml`:

```toml
description = "Proceso y aprendizajes del equipo de costos."
start_here = ["/proyectos/costos/proceso.md"]
read = ["@costs"]     # emails, @grupo o "*"
write = ["@costs"]
```

- **Leer** se deniega salvo que alguna carpeta del camino lo conceda; cada carpeta que declara `read` restringe a las que cuelgan de ella.
- **Escribir** lo decide la carpeta más cercana que declare `write`; sin declaración, se deniega.
- Los grupos y sus miembros se administran en la base de cuentas, por la API del panel.
- Un administrador ve la estructura y los accesos de todas las carpetas, pero no lee contenido que no tenga concedido.
- Los archivos que empiezan con punto y los enlaces simbólicos nunca son visibles para el agente.
- Si la raíz es un repositorio git, cada escritura queda como commit a nombre de quien escribió.
- Una skill es una carpeta con un `SKILL.md`. Véase `examples/brain/`.

## Verificación

```bash
uv run pytest -q
uv run ruff check src tests
```

## Documentación

- [Alcance](docs/scope.md)
- [Registro de decisiones](docs/decisions/README.md)
- [Modo de colaboración](AGENTS.md)
- Antecedentes históricos: [visión original](docs/vision.md), [panorama](docs/research/landscape-2026-11-11.md) y [comparación ejecutada](docs/research/comparison-atlas/README.md)
