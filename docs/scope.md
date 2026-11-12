# Alcance

Confirmado por el autor el 12 de noviembre de 2026. Véanse [0008](decisions/0008-alcance-acotado.md) y [0009](decisions/0009-panel-y-cuentas.md).

**OIF es un servidor MCP que convierte una carpeta en el cerebro compartido de un equipo:
archivos con permisos que cualquier harness lee y escribe.**

## Lo que es

1. **Un formato.** Una carpeta con un `.oif.toml` por carpeta: `description`, `start_here`,
   `read`, `write`. Son archivos comunes: se abren, editan y versionan sin el servidor.
2. **Un servidor MCP** con cinco herramientas: listar, leer, escribir, buscar y listar skills.
3. **Permisos por carpeta**, con grupos, denegados por defecto.
4. **Skills dentro del árbol.** Una skill es una carpeta con un `SKILL.md`; el agente ve solo
   las de carpetas que puede leer. Ejecutarla es tarea del harness.
5. **Cuentas propias.** Email y contraseña; el primer usuario administra e invita al resto;
   cada persona genera el token con el que conecta su harness. Una organización por servidor.
6. **Un panel web** al estilo de Infisical o Langfuse (API lista, interfaz sin construir):
   accesos por carpeta, miembros y tokens, explorador de archivos de solo lectura y actividad.

Un equipo levanta su propio servidor y cada persona conecta su harness con su token.

## Lo que no es

| Fuera de alcance | Quién lo resuelve |
|---|---|
| Harness, runtime, adapters de modelos | Claude Code, Codex u otro |
| Conectores a correo, bases de datos, etc. | Los MCP que cada harness ya trae |
| Ejecutar skills | El harness; acá una skill es una carpeta con `SKILL.md` |
| Extraer memoria automáticamente de conversaciones | El agente decide qué escribir |
| Embeddings, RAG, búsqueda semántica | Búsqueda por texto y metadata de carpetas |
| Motor de borradores, revisión y aprobación | Permiso de escritura = puede publicar; quien quiera revisión usa PRs de git |
| Editor web de contenido, chat web | Editor de texto, git y el harness |
| Envío de emails de invitación | El administrador comparte el enlace de invitación |
| Google, GitHub u OIDC | Previsto para después de las cuentas propias |
| Alojamiento multiempresa | Cada equipo levanta el suyo |
| Modo local por persona sincronizado con git | Descartado: los permisos de lectura dejan de valer |

## Qué lo hace armable

- El cerebro es una carpeta: se combina con git, grep, un editor o un backup.
- El servidor es un MCP más y convive con los que el equipo ya tenga.
- Las carpetas y sus permisos viven en archivos; cuentas, grupos, tokens y actividad, en un
  único archivo SQLite.
- Dos puntos de extensión: dónde se guarda y cómo se identifica a la persona. No se crean
  interfaces de plugin hasta que exista una segunda implementación real.

## Criterios

- Denegar por defecto; lo denegado se ve igual que lo inexistente.
- Todo es un archivo; el historial es git.
- La metadata de cada carpeta guía al agente hacia lo importante.
- Antes de agregar algo, comprobar que no está en la tabla de «lo que no es».
