# Registro de decisiones

Las propuestas se registran antes de implementar y pasan a aceptadas cuando el autor confirma la elección. Un cambio posterior conserva la historia e indica qué decisión reemplaza.

## Confirmado por el autor

| Decisión | Estado | Origen |
|---|---|---|
| Proyecto personal, independiente del trabajo | Aceptada | Conversación del 11 de noviembre de 2026 |
| Usar el documento de visión como base | Aceptada | Conversación del 11 de noviembre de 2026 |
| Crear un repositorio y comenzar el desarrollo | Aceptada | Conversación del 11 de noviembre de 2026 |
| Consultar decisiones durante la construcción | Aceptada | Conversación del 11 de noviembre de 2026 |
| Primer producto: harness utilizable desde terminal | Aceptada | Corrección del autor al enfoque web |
| Python para la parte agéntica | Aceptada | Elección explícita del autor |
| Documentar primero y construir encima después | Aceptada | Elección explícita del autor |
| Cuenta personal de GitHub: `jackspolski1103` | Aceptada | Cuenta indicada explícitamente por el autor |
| Uso conversacional natural, sin administración manual de memoria en el recorrido habitual | Intención aceptada | «quiero que sea natural el uso como uso chatgpt o claude» |
| Consumo habitual de conocimiento compartido: solo versiones aprobadas, publicadas, vigentes y autorizadas; borradores en revisión separada | Aceptada para el primer prototipo | Confirmación explícita del autor; [0003](0003-consumo-de-conocimiento-compartido.md) |
| Colaboración como núcleo del primer producto: CLI vinculado a servicio y espacio compartidos; sin modo personal autónomo inicial | Aceptada | Rechazo explícito del autor al enfoque local; [0004](0004-colaboracion-como-nucleo-del-producto.md) |
| Primer corte: servicio Python, CLI, MCP y dos agentes que reutilizan una capacidad versionada | Aceptada | «dale» ante el alcance concreto; [0005](0005-primer-corte-capacidad-compartida-mcp.md) |
| Primer acceso real a modelos: API personal de OpenAI mediante adapter | Aceptada | Elección explícita durante el inicio de construcción |
| Memoria navegable como repositorio de carpetas, subcarpetas y archivos con permisos | Aceptada | Aclaración explícita del autor; [0006](0006-memoria-como-repositorio-con-permisos.md) |
| Producto: cerebro compartido agnóstico al harness, expuesto por MCP; sin harness propio como producto | Aceptada; reemplaza el harness propio de 0001 | «agnóstico al harness. quiero hasta poder conectar cc»; [0007](0007-cerebro-agnostico-al-harness.md) |
| Alcance acotado: formato, servidor MCP, permisos, identidad enchufable y panel de accesos; un servidor por equipo; sin motor editorial ni harness | Aceptada; reemplaza 0003 y 0005 | «sí a las tres, borrá el harness»; [0008](0008-alcance-acotado.md) |
| Panel React sobre API Python; cuentas propias con email y contraseña; panel con accesos, miembros y tokens, explorador y actividad | Aceptada | Respuestas explícitas a tres preguntas; [0009](0009-panel-y-cuentas.md) |

## Pendiente

| Decisión | Recomendación inicial | Estado |
|---|---|---|
| Login con Google, GitHub u OIDC | Después de las cuentas propias | Pendiente |
| Nombre | OIF como nombre de trabajo | Propuesto |
| Licencia | Apache-2.0 | Propuesto |
| Repositorio remoto y visibilidad | Crear en `jackspolski1103`; privado al inicio | Pendiente |

## Orden del próximo incremento

1. Interfaz React del panel sobre la API existente.
2. Contenedor y `docker compose` para instalarlo en un paso.
3. Nombre, licencia y publicación.

## Formato de una decisión

- [0001 — CLI, Python y documentación primero](0001-cli-python-docs-first.md)
- [0002 — Conversación natural como experiencia principal](0002-conversacion-natural.md)
- [0003 — Consumo de conocimiento compartido aprobado y publicado](0003-consumo-de-conocimiento-compartido.md)
- [0004 — Colaboración como núcleo del primer producto](0004-colaboracion-como-nucleo-del-producto.md)
- [0005 — Primer corte: dos agentes y una capacidad compartida mediante MCP](0005-primer-corte-capacidad-compartida-mcp.md)
- [0006 — Memoria como repositorio con permisos](0006-memoria-como-repositorio-con-permisos.md)
- [0007 — Cerebro compartido agnóstico al harness](0007-cerebro-agnostico-al-harness.md)
- [0008 — Alcance acotado](0008-alcance-acotado.md)
- [0009 — Panel web y cuentas propias](0009-panel-y-cuentas.md)

La propuesta inicial de una web y TypeScript fue reemplazada por la elección explícita de CLI y Python; nunca fue una decisión aceptada.

Cada decisión importante tendrá contexto, alternativas, elección del autor, consecuencias y criterio de verificación. El silencio ante una pregunta no se registra como aprobación.
