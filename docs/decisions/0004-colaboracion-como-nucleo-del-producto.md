# 0004 — Colaboración como núcleo del primer producto

Fecha: 11 de noviembre de 2026.

Estado: aceptada por el autor.

Concreción posterior: [0005](0005-primer-corte-capacidad-compartida-mcp.md) define el primer corte como reutilización operativa de una capacidad entre dos agentes especializados. El recorrido editorial descrito aquí sigue en la visión; no es condición para cada tarea ni agota el foco colaborativo.

## Contexto y elección del autor

Se propuso un CLI personal autónomo con conexión opcional a un espacio compartido. El autor rechazó esa dirección: «nono no hagamos lo local. no nos desenfoquemos».

La propuesta local autónoma nunca fue una decisión aceptada. La corrección sitúa la colaboración en el recorrido principal desde el primer producto.

## Decisión

- El primer producto es un harness conversacional en terminal vinculado a un servicio y espacio compartidos.
- No se construye un modo personal autónomo como producto inicial ni se presenta la colaboración como un agregado opcional posterior.
- El recorrido que guía el diseño conecta el trabajo privado de una persona con un aprendizaje aprobado y publicado que otra persona puede utilizar con sus propios permisos.
- El CLI y Python siguen confirmados. La política de [0003](0003-consumo-de-conocimiento-compartido.md) sigue vigente: la consulta habitual usa conocimiento compartido aprobado, publicado, vigente y autorizado.

## Consecuencias

La identidad verificada, las membresías, la autorización y el ciclo de revisión y publicación forman parte del recorrido principal. Un perfil del cliente no sustituye la identidad verificada por el servicio.

Las etapas técnicas se ordenan alrededor de ese recorrido compartido. Una sesión individual o un modelo simulado pueden servir como componentes de desarrollo, pero no demuestran por sí solos el resultado del producto.

La conexión al servicio no concede permiso para subir transcripciones privadas completas, publicar sus derivados ni transferir credenciales. El contenido privado conserva su alcance y compartir exige la promoción explícita ya acordada.

## Alcance de esta elección

Se elige el foco y modo de uso del producto. La decisión no fija dónde se ejecuta cada componente del agente, dónde se conserva la sesión privada, quién aporta la credencial del modelo ni dónde se alojará el servicio. Tampoco autoriza desplegar infraestructura o contratar servicios.

## Criterios de verificación

1. El recorrido inicial incluye identidad verificada y un espacio compartido autorizado.
2. El recorrido objetivo permite preparar, revisar y publicar un aprendizaje que una segunda identidad autorizada utiliza desde su CLI sin recibir la conversación privada de origen.
3. El plan de implementación no ofrece un asistente personal autónomo como primera entrega de producto ni pospone toda la colaboración a una ampliación opcional.
4. Las pruebas del recorrido compartido comprueban denegación a otra identidad o audiencia y bloqueo de nuevas recuperaciones tras revocación.

Estos criterios orientan el diseño y la verificación futura; aún no hay un runtime ni un servicio implementados.

## Pendiente

Cerrar el alcance implementable del primer recorrido, los roles de aprobación y publicación, los contratos entre CLI y servicio, la distribución de ejecución y persistencia, el modelo y la autenticación. Los proveedores y el alojamiento se eligen cuando ese alcance los requiera.

Esta decisión complementa [0001](0001-cli-python-docs-first.md), [0002](0002-conversacion-natural.md) y [0003](0003-consumo-de-conocimiento-compartido.md).
