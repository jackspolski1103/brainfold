# 0003 — Consumo de conocimiento compartido aprobado y publicado

Fecha: 11 de noviembre de 2026.

Estado: aceptada por el autor para el primer prototipo.

## Contexto y elección del autor

La comparación de Team Memory, cq y Markdown con PR identificó la necesidad de separar la edición de la publicación. La decisión de [conversación natural](0002-conversacion-natural.md) dejó abierta la posibilidad de usar conocimiento no verificado en las respuestas habituales.

Se recomendó incorporar automáticamente solo versiones aprobadas y publicadas, con los borradores en un circuito de revisión separado. El autor confirmó esta recomendación con «sí» ante la pregunta «¿Confirmamos que el agente normal solo consume conocimiento aprobado/publicado?».

## Decisión

- En el primer prototipo, la recuperación habitual de conocimiento compartido entrega únicamente versiones aprobadas, publicadas, vigentes y autorizadas para el solicitante y la audiencia de la respuesta.
- Los candidatos, borradores y versiones pendientes de aprobación o publicación quedan fuera de esa recuperación. Pueden utilizarse para preparar o revisar una propuesta mediante una solicitud explícita y con permisos de revisión suficientes.
- La separación se aplica antes de entregar contenido al contexto del agente. Mostrar una etiqueta de «no verificado» después de recuperarlo no satisface esta regla.
- Enviar a revisión, aprobar y publicar tienen efectos distintos. Aprobar una versión no la hace consumible hasta que la publicación se completa; el sistema comunica el resultado real. Esto no exige tres pantallas ni tres operaciones manuales.
- La aprobación corresponde a una versión y audiencia identificables. Cambiar el contenido o la audiencia exige una nueva aprobación; una edición no hereda la aprobación de la versión publicada.
- Una corrección pendiente no reemplaza la última versión publicada y vigente. Esta continúa disponible mientras conserve vigencia y autorización, salvo que se retire o se revoque su acceso.
- Retirar una versión o revocar su acceso impide nuevas recuperaciones desde el servicio compartido. No promete eliminar textos o archivos ya entregados.

## Alcance y consecuencias

Esta política regula el conocimiento compartido que el agente incorpora a las tareas habituales. La persona puede seguir trabajando con sus notas, archivos, conversación y memoria privada autorizados, incluso para preparar un candidato. Sus políticas de captura y retención siguen pendientes. Ese trabajo no convierte el material en conocimiento publicado ni autoriza su divulgación.

El circuito de revisión puede ocurrir dentro de la misma experiencia conversacional. Su contenido conserva el alcance de revisión y no se reutiliza para una audiencia distinta sin autorización. Permitir revisar una propuesta tampoco concede acceso a la conversación privada o a sus fuentes.

El agente informa si una propuesta está en revisión, aprobada pero sin publicar, publicada o retirada. Que un contenido esté publicado expresa su estado editorial y su autorización; no garantiza su exactitud universal.

## Alternativa considerada

Permitir conocimiento no verificado en las respuestas habituales, claramente marcado. Podría ofrecer aprendizajes recientes antes de su aprobación, pero exigiría reglas adicionales para decidir cuándo y cómo usarlos. No se adopta para el primer prototipo; una ampliación futura requerirá una nueva decisión.

## Criterios de verificación

1. Una consulta normal no entrega borradores ni versiones pendientes de publicación al agente, aunque quien consulta también tenga rol de revisor.
2. Una solicitud explícita de revisión permite acceder a la propuesta únicamente a quien tenga permiso para revisarla y sin adjuntar implícitamente el chat privado.
3. Si existe una versión publicada y una corrección pendiente, la consulta habitual recupera la publicada mientras siga vigente y autorizada.
4. Cambiar el texto o la audiencia impide publicar la nueva versión usando la aprobación anterior.
5. Una versión aprobada pero aún no publicada no aparece en consultas habituales. La versión publicada coincide con el texto y la audiencia aprobados.
6. Retirar una versión o revocar acceso bloquea nuevas recuperaciones desde el servicio, sin afirmar que se borraron copias ya entregadas.
7. Una tarea privada puede usar material propio autorizado sin aprobación editorial; compartirlo sigue requiriendo una promoción explícita.

Estos criterios documentan el comportamiento a implementar; todavía no son garantías de un servicio existente.

## Pendiente

Quién puede aprobar y publicar, si se exige un revisor distinto del autor, cómo se acredita cada aprobación y las reglas de vigencia. También siguen pendientes la retención de memoria privada, el alcance del primer incremento y su distribución local/remota. Esta decisión no selecciona motor, almacenamiento, proveedores ni infraestructura.

Esta decisión complementa [0001](0001-cli-python-docs-first.md) y [0002](0002-conversacion-natural.md).
