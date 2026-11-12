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

## Pendiente

| Decisión | Recomendación inicial | Estado |
|---|---|---|
| Nombre | OIF como nombre de trabajo | Propuesto |
| Repositorio remoto | Crear en `jackspolski1103` con el nombre y visibilidad elegidos | Creación pendiente |
| Visibilidad inicial | Privado durante el arranque; publicación deliberada después | Propuesto |
| Distribución de ejecución y persistencia | Definir responsabilidades de CLI y servicio para el recorrido compartido | Pendiente; el foco colaborativo ya se decidió en [0004](0004-colaboracion-como-nucleo-del-producto.md) |
| Login | Proveedor OIDC personal para el piloto | Propuesto; proveedor pendiente |
| Conexiones externas | OAuth por usuario cuando el proveedor lo permita | Propuesto |
| Modelos posteriores y consumo compartido | Mantener contratos independientes del proveedor | Pendiente; el primer acceso personal OpenAI ya está elegido |
| Primera integración | Elegir una herramienta y comenzar en lectura | Pendiente |
| Persistencia y gestor de secretos | Elegir después del alcance del primer incremento | Pendiente |
| Licencia | Apache-2.0 según la visión | Propuesto |
| Roles y reglas detalladas de aprobación y publicación | Precisar quién puede aprobar/publicar y si se exige un revisor distinto del autor | Pendiente; el consumo habitual ya se decidió en [0003](0003-consumo-de-conocimiento-compartido.md) |
| Captura y retención de memoria privada; frecuencia de sugerencias | Concretar en el recorrido conversacional | Pendiente |

## Orden del próximo incremento

1. Construir el corte aprobado en [0005](0005-primer-corte-capacidad-compartida-mcp.md): reutilización operativa de una capacidad entre dos agentes, conectada por MCP y con autorización en el servicio.
2. Verificar la conexión con el modelo usando la API personal de OpenAI configurada fuera del chat.
3. Elegir autenticación y persistencia productivas e integración externa cuando el siguiente incremento las requiera. El flujo editorial completo permanece en la visión y no es condición para usar cada herramienta autorizada.

Nombre, visibilidad del remoto y licencia se consultan antes de crear o publicar el repositorio remoto; no bloquean la documentación local.

## Formato de una decisión

- [0001 — CLI, Python y documentación primero](0001-cli-python-docs-first.md)
- [0002 — Conversación natural como experiencia principal](0002-conversacion-natural.md)
- [0003 — Consumo de conocimiento compartido aprobado y publicado](0003-consumo-de-conocimiento-compartido.md)
- [0004 — Colaboración como núcleo del primer producto](0004-colaboracion-como-nucleo-del-producto.md)
- [0005 — Primer corte: dos agentes y una capacidad compartida mediante MCP](0005-primer-corte-capacidad-compartida-mcp.md)
- [0006 — Memoria como repositorio con permisos](0006-memoria-como-repositorio-con-permisos.md)

La propuesta inicial de una web y TypeScript fue reemplazada por la elección explícita de CLI y Python; nunca fue una decisión aceptada.

Cada decisión importante tendrá contexto, alternativas, elección del autor, consecuencias y criterio de verificación. El silencio ante una pregunta no se registra como aprobación.
