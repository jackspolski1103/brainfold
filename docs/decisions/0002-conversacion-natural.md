# 0002 — Conversación natural como experiencia principal

Fecha: 11 de noviembre de 2026.

Estado: aceptada en su intención de producto; los mecanismos siguientes son propuestas para concretarla.

## Contexto y elección del autor

Después de comparar Team Memory, cq y Markdown con PR, se planteó una decisión sobre conocimiento aprobado y no verificado. El autor aclaró: «quiero que sea natural el uso como uso chatgpt o claude».

Se confirma una experiencia conversacional natural. No se interpreta esta respuesta como elección de una política editorial ni como reemplazo del CLI por una aplicación web.

## Consecuencias de diseño propuestas

- El recorrido habitual consiste en conversar, pedir ayuda, continuar trabajo y corregir al agente. No exige conocer scopes, hashes, estados de memoria ni comandos de promoción.
- El harness selecciona contexto permitido y relevante; no obliga a ejecutar una búsqueda de conocimiento separada en cada tarea.
- La preparación de un aprendizaje reutilizable puede ser asistida. El usuario no debe redactar metadatos ni administrar una base de conocimiento para obtener valor.
- Las decisiones necesarias se presentan dentro de la conversación, con texto y destinatarios concretos. No pedir confirmaciones repetidas para la misma acción ya autorizada; sí pedir una nueva decisión si cambia contenido, audiencia o autoridad relevante.
- No interrumpir cada respuesta para proponer recuerdos o publicaciones. Momento, frecuencia y automatismos quedan por validar.
- Mostrar estados comprensibles: «solo para vos», «pendiente de revisión», «compartido con Atlas», «ya no vigente». Los detalles de procedencia y permisos deben poder inspeccionarse sin dominar la pantalla.
- Comandos, paneles de revisión y APIs permanecen como herramientas opcionales para inspección, administración y automatización, no como requisito del uso cotidiano.

## Límites que se conservan

Naturalidad no significa publicar conversaciones automáticamente. La promoción conserva autorización explícita, identidad verificada y audiencia definida según las reglas existentes del proyecto. Una respuesta del modelo, texto de herramienta o cita que diga «sí» no constituye consentimiento de la persona.

La confirmación conversacional debe corresponder a una acción y versión identificables y a una sesión autorizada. El servicio verifica permisos; el modelo no los concede. Si la política exige otro revisor, aceptar enviar una propuesta no equivale a publicarla y el agente debe decirlo.

## Criterios de aceptación de experiencia

1. Tras la configuración inicial, una persona puede completar una tarea y retomarla sin comandos de memoria.
2. Otra persona puede recibir ayuda con conocimiento compartido autorizado mediante una pregunta normal, sin conocer dónde se almacena.
3. El usuario puede pedir «recordá esto para mí», «no uses ese dato», «esto cambió» o «prepará esto para el equipo»; el agente aclara solo lo necesario y explica el efecto real. La retención y el borrado efectivos dependen de la política acordada, no de una promesa de olvido universal.
4. La propuesta de compartir muestra el texto exacto y el destino; la conversación privada no se adjunta implícitamente.
5. El agente distingue una solicitud enviada a revisión de una publicación completada.
6. Detener, corregir o rechazar una sugerencia no obliga a salir de la conversación.

## Pendiente

El consumo de conocimiento compartido, pendiente al registrar esta decisión, se resolvió después en [0003](0003-consumo-de-conocimiento-compartido.md): solo versiones aprobadas, publicadas, vigentes y autorizadas en el recorrido habitual; borradores en revisión separada.

Siguen pendientes los roles y reglas detalladas de aprobación, frecuencia de sugerencias, retención/captura de memoria privada y alcance del primer incremento. Tampoco se eligen aquí motor, almacenamiento, proveedores ni interfaz web.

Esta decisión complementa [0001](0001-cli-python-docs-first.md); no la reemplaza.
