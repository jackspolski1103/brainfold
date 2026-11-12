# Especificación inicial del CLI y del harness

Estado: diseño general con un primer corte implementado. Existen `serve`, `chat`, `run`, `verify-example` y `example-mcp`; otras superficies de este documento siguen propuestas. CLI, Python, experiencia natural, servicio compartido, capacidad reutilizada por dos agentes y memoria navegable están confirmados. Véase [Desarrollo](development.md) para comandos ejecutables y límites actuales.

## 1. Experiencia buscada

La persona abre la terminal, inicia sesión en un espacio compartido y conversa con un agente capaz de trabajar con herramientas. Ve qué está haciendo, puede intervenir, aprobar una operación, cancelar y retomar una sesión. Si trabaja sobre archivos, el CLI muestra el directorio correspondiente.

El agente realiza tareas con herramientas y reutiliza capacidades, procedimientos y contexto entre soluciones. El primer corte aprobado demuestra una capacidad MCP común a dos especializaciones. La memoria se explora como carpetas y archivos con permisos; el agente puede listar y leer sin exigir búsquedas manuales. Véanse [0005](decisions/0005-primer-corte-capacidad-compartida-mcp.md) y [0006](decisions/0006-memoria-como-repositorio-con-permisos.md).

En el primer prototipo, las tareas habituales incorporan automáticamente solo versiones compartidas aprobadas, publicadas, vigentes y autorizadas para el solicitante y la audiencia. Los borradores se utilizan mediante una solicitud explícita de preparación o revisión con permisos suficientes; quedan fuera de la recuperación habitual, incluso para quien tenga rol de revisor. El material privado propio puede seguir utilizándose dentro de su alcance. Véase [0003](decisions/0003-consumo-de-conocimiento-compartido.md).

La interacción cotidiana debe sentirse como conversar con un asistente, no administrar un repositorio de memorias. La persona pide ayuda; el harness selecciona contexto autorizado y propone acciones relevantes. No necesita ejecutar `memory search`, declarar un scope o crear una propuesta formal para cada tarea. Los controles de permisos y versiones funcionan por detrás, con decisiones comprensibles cuando hacen falta. Véase [la decisión de conversación natural](decisions/0002-conversacion-natural.md).

El alcance del agente puede incluir investigación, documentación, procesos y código. Las primeras herramientas concretas se elegirán con el autor; no se asume que todo usuario necesitará acceso irrestricto al shell.

## 2. Tres piezas separables

| Pieza | Responsabilidad | Estado |
|---|---|---|
| Núcleo Python | Contratos, identidades, scopes, artefactos, policies y memoria | Diseño |
| Harness de referencia | Ciclo del agente, sesión, tools, presupuesto, cancelación y checkpoints | Diseño |
| Interfaz CLI | Conversación en terminal, comandos, previews, confirmaciones y estado | Punto de entrada confirmado |

El núcleo debe poder ser usado por otros runtimes. El harness propio demuestra la experiencia completa y consume las mismas interfaces públicas que un adapter externo. Un canal futuro puede entrar al runtime sin depender de cómo se dibuja la terminal.

## 3. CLI vinculado al servicio compartido

El primer producto requiere una identidad verificada y acceso a un espacio compartido. El modo personal autónomo con colaboración opcional fue descartado por el autor en [0004](decisions/0004-colaboracion-como-nucleo-del-producto.md).

El CLI autentica a la persona contra una instalación del framework. Esa instalación mantiene membresías, permisos, conocimiento publicado, revisiones y auditoría. El servidor verifica las operaciones compartidas; ni un archivo de configuración del cliente ni cambiar un nombre de perfil pueden conceder acceso.

La conversación y memoria privadas conservan su alcance. Conectarse no concede permiso para subir transcripciones completas ni transferir credenciales. La retención, la ubicación de persistencia y qué contexto se envía al modelo deben concretarse en el diseño.

La distribución de ejecución entre CLI y servicio, y el alojamiento de este último, siguen pendientes. El foco compartido no presupone ejecutar todo el agente en el servidor ni concede acceso al equipo de la persona.

## 4. Flujo visible de publicación futura

Ejemplo de interacción ficticia del flujo editorial, todavía no implementado. El primer corte permite conversar, navegar memoria y consultar herramientas; no requiere este flujo para cada tarea.

```text
$ oif

Ana · espacio Atlas · proveedor/modelo-elegido
Conversación privada · ./mi-proyecto

> Revisá estas notas y ayudame a convertirlas en un procedimiento.

Agente: Voy a revisar las notas que seleccionaste.
[Procedimiento propuesto, con referencias accesibles.]

> Esto podría servirle al equipo.

Agente: Preparé esta versión para Atlas, sin los datos del caso privado:
[Texto exacto de la propuesta.]
¿La envío a revisión del equipo?

> Sí.

Agente: La envié a revisión. Todavía no está publicada.
```

El ejemplo refleja la separación confirmada entre revisión y publicación. Los roles de aprobación y publicación, y si se exige un revisor distinto del autor, siguen pendientes. No se exige un panel separado ni un comando de promoción. El estado mostrado debe coincidir con el resultado real de la operación. Una versión aprobada aún sin publicar queda fuera de las consultas habituales. Las sugerencias no deben aparecer tras cada respuesta; su frecuencia se validará.

El directorio visible es contexto de trabajo, no una autorización implícita a todos sus archivos. Una llamada a herramienta se evalúa contra los permisos de su entorno de ejecución y las reglas aplicables del servicio compartido.

## 5. Comandos propuestos

Los comandos implementados son `oif serve`, `oif chat`, `oif run`, `oif verify-example` y `oif example-mcp`; sus argumentos están en [Desarrollo](development.md). La siguiente tabla conserva superficies futuras de inspección y automatización, todavía no implementadas salvo `run`. Después de configurar el acceso, el recorrido habitual es conversacional.

| Comando ilustrativo | Propósito |
|---|---|
| `oif` | Iniciar sesión interactiva vinculada al espacio autorizado |
| `oif run "tarea"` | Ejecutar una tarea no interactiva con permisos predefinidos |
| `oif sessions list` | Listar sesiones accesibles a la identidad autenticada |
| `oif resume <session>` | Retomar una sesión |
| `oif model configure` | Seleccionar proveedor, modelo y forma segura de autenticación |
| `oif auth status` | Mostrar cuentas y permisos sin secretos |
| `oif connect <provider>` | Autorizar una conexión personal |
| `oif disconnect <connection>` | Bloquear usos futuros y solicitar revocación cuando se admita |
| `oif login --server <url>` | Autenticarse en una instalación compartida |
| `oif spaces list` | Ver espacios autorizados |
| `oif memory list` | Inspeccionar memoria privada accesible |
| `oif knowledge propose <candidate> --space <space>` | Enviar una versión revisable al espacio elegido |
| `oif knowledge review <proposal>` | Revisar una propuesta con la identidad autorizada |
| `oif knowledge search "consulta"` | Consultar versiones aprobadas, publicadas, vigentes y autorizadas |

En modo no interactivo, una acción que requiere aprobación queda pendiente o falla con un estado claro. La ausencia de terminal nunca equivale a aprobar.

## 6. Ciclo del harness

```text
Entrada del usuario
  → construir contexto autorizado
  → solicitar siguiente paso al modelo
  → recibir texto o propuesta de herramienta
  → validar argumentos, presupuesto y permisos
  → solicitar aprobación cuando corresponda
  → ejecutar herramienta mediante gateway
  → registrar resultado y estado
  → continuar o finalizar
```

El evento de aprendizaje ocurre después como una propuesta dentro del scope privado. No se publica por el solo hecho de que una tarea haya terminado.

El contexto puede combinar instrucciones del sistema, solicitud del usuario, datos de archivos, resultados de tools y conocimiento autorizado. La recuperación habitual de conocimiento compartido aplica la política de [0003](decisions/0003-consumo-de-conocimiento-compartido.md) antes de entregar contenido al agente. Debe conservar su origen; un documento recuperado no se convierte en una instrucción con autoridad para cambiar permisos.

## 7. Contratos iniciales propuestos

| Contrato | Qué abstrae |
|---|---|
| `ModelPort` | Generación, eventos, tool calls y capacidades del modelo |
| `ToolExecutor` | Validación, autorización, ejecución y cancelación de operaciones |
| `SessionStore` | Historial permitido, checkpoints y metadatos de sesión |
| `MemoryStore` | Memorias privadas y su ciclo de vida |
| `KnowledgeClient` | Consulta, propuesta y revisión de conocimiento compartido |
| `IdentityProvider` | Identidad verificada y membresías del servicio |
| `CredentialBroker` | Selección y uso autorizado de conexiones |
| `SecretStorePort` | Referencias a secretos guardados fuera del conocimiento |
| `PolicyPort` | Decisiones sobre herramientas, contenido y destinos |
| `EventSink` | Eventos de ejecución sin contenido sensible innecesario |

Los nombres y firmas se acordarán antes de estabilizar un SDK. No hay una librería de agentes seleccionada todavía.

## 8. Permisos locales y compartidos

Los permisos de archivos y procesos son independientes de los permisos organizacionales. Pertenecer a un equipo no permite leer cualquier archivo de la computadora. Tener acceso local a un archivo no autoriza publicarlo en ese equipo.

Las herramientas iniciales pueden ser operaciones acotadas como leer archivos seleccionados, buscar texto y proponer cambios. Si se incorpora shell, deben definirse sandbox, acceso de red, entorno de subprocesos, procesos hijos y acceso al llavero. Una lista de comandos aprobados no demuestra por sí sola aislamiento del sistema.

El servicio compartido nunca debe confiar en que la CLI del usuario aplica correctamente todos los controles: verifica identidad y permisos en el servidor en cada operación relevante.

## 9. Sesiones, interrupción y recuperación

Cada sesión conserva perfil, directorio, modo de permisos, modelo, referencias a herramientas y estado. No conserva secretos. Se distinguen operaciones pendientes, aprobadas, en curso, completadas, fallidas y con resultado incierto.

Cancelar intenta detener el trabajo pendiente y los procesos controlados. No promete deshacer una escritura o acción externa ya completada. Retomar una sesión exige reevaluar autorizaciones y referencias que puedan haber vencido.

Una sesión abierta en otro directorio o perfil no hereda automáticamente permisos anteriores.

## 10. Relación con Slack, Teams y otras conexiones

La terminal es el primer canal. Un adapter de Slack o Teams puede recibir una solicitud autenticada y enviarla al mismo núcleo, pero no debería obtener acceso al shell de una computadora personal por el hecho de estar conectado.

Si se permite que una solicitud desde el servicio o un canal opere sobre herramientas de la computadora del usuario, habrá que diseñar un mecanismo autorizado de ejecución, por ejemplo un worker registrado con identidad y políticas propias. Ese acceso se acuerda por separado; no determina cómo se ejecuta el agente en el servicio.

## 11. Decisiones próximas

1. Probar la conversación real con la API personal OpenAI elegida, fuera del chat.
2. Elegir identidad y persistencia productivas después de evaluar el corte de desarrollo.
3. Elegir una integración externa personal por MCP y sus permisos.
4. Concretar escritura, corrección y promoción conversacional de archivos de memoria.
5. Definir roles y reglas del flujo editorial completo.

El primer punto de entrada, Python y el foco colaborativo ya están decididos. Estas preguntas concretan el siguiente incremento.
