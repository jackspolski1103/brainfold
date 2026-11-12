# OIF — inteligencia organizacional colaborativa

Proyecto personal e independiente. **OIF es un nombre provisional.**

Cuenta personal de GitHub elegida: [jackspolski1103](https://github.com/jackspolski1103). El repositorio remoto todavía no está creado.

Proyecto con intención open source para construir agentes de trabajo que reutilizan herramientas, procedimientos y contexto entre soluciones, con especialización y permisos por proyecto.

## Estado

Primera implementación de desarrollo: servicio HTTP compartido en Python, runtime acotado, CLI conversacional, adapter OpenAI Responses y conexión MCP Streamable HTTP con el SDK oficial. Dos agentes sintéticos de costos y contratos reutilizan una capacidad versionada.

La memoria se explora como un repositorio virtual de carpetas y archivos con permisos. El agente puede listar y leer por iniciativa propia; el servicio autoriza a solicitante y audiencia y conserva las restricciones de las carpetas padre.

La autenticación por tokens y el estado en memoria son mecanismos de desarrollo. Faltan identidad y persistencia productivas, escritura de memoria, integración real con correo o Databricks y el flujo editorial completo. La conversación real con OpenAI requiere configurar la API personal elegida y un modelo disponible; las pruebas automáticas no consumen inferencia.

## Ejecutar la verificación

```bash
uv sync
uv run oif verify-example
uv run pytest -q
```

`verify-example` levanta temporalmente un servicio HTTP y un servidor MCP, prueba una corrección común en ambos agentes y comprueba aislamiento, revocación y navegación de memoria. Cierra sus servidores al terminar.

El driver de modelo de esa verificación es programado: comprueba integración y permisos, no razonamiento ni calidad de respuestas. Los datos son sintéticos.

Para conversar con el modelo real, véase [la guía de desarrollo](docs/development.md). El CLI siempre se conecta al servicio compartido; los procesos de desarrollo en loopback no son un modo personal autónomo del producto.

## Documentación

- [Visión completa](docs/vision.md): documento base, conservado íntegramente.
- [Panorama y oportunidad — investigación del 11/11/2026](docs/research/landscape-2026-11-11.md): antecedentes, alternativas, límites de novedad y propuesta de validación antes de implementar.
- [Comparación ejecutada: Team Memory, cq y Markdown + PR](docs/research/comparison-atlas/README.md): un mismo caso sintético, resultados, límites y scripts reproducibles.
- [Identidad y credenciales](docs/credentials.md): propuesta para login, conexiones personales, permisos y secretos.
- [Especificación del CLI](docs/cli.md): experiencia de terminal, harness de referencia y conexión al servicio compartido.
- [Primer incremento](docs/first-increment.md): recorrido propuesto y criterios de aceptación.
- [Desarrollo y ejecución](docs/development.md): comandos reales, configuración y límites del primer corte.
- [Registro de decisiones](docs/decisions/README.md): decisiones confirmadas y pendientes.
- [Modo de colaboración](AGENTS.md): cómo construir el proyecto junto con su autor.

## Dirección confirmada

El producto empieza como **un harness de agentes que se usa desde la terminal**, con Python para lo agéntico. El autor aprobó el [primer corte de construcción](docs/decisions/0005-primer-corte-capacidad-compartida-mcp.md) después de concretar su alcance documental.

La colaboración es el núcleo del primer producto: el CLI se vincula a un servicio y espacio compartidos. El autor descartó el modo personal autónomo con colaboración opcional. La ubicación de ejecución del agente y el alojamiento del servicio siguen pendientes. Véase [foco colaborativo](docs/decisions/0004-colaboracion-como-nucleo-del-producto.md).

El uso cotidiano será conversacional y natural: pedir ayuda, continuar trabajo y corregir al agente, sin administrar memorias mediante comandos. Permisos, versiones y publicación se resuelven detrás de esa experiencia; las decisiones necesarias se piden dentro de la conversación. Véase [conversación natural](docs/decisions/0002-conversacion-natural.md).

Para el primer prototipo, el agente incorporará automáticamente solo conocimiento compartido aprobado, publicado, vigente y autorizado. Los borradores permanecerán en un circuito de revisión autorizado; la memoria y el material privados conservarán su alcance. Véase [consumo de conocimiento compartido](docs/decisions/0003-consumo-de-conocimiento-compartido.md).

La visión original se conserva íntegra. Las decisiones posteriores en `docs/decisions/` concretan su implementación: el primer punto de entrada será la terminal, y una web o los adapters de mensajería podrán añadirse después.

La [memoria como repositorio con permisos](docs/decisions/0006-memoria-como-repositorio-con-permisos.md) es el modelo de navegación confirmado. En este corte se implementan listado y lectura; edición y promoción siguen pendientes.

## Primer recorrido implementado

Una identidad de desarrollo accede al agente de costos y otra al de contratos. Cada agente usa sus instrucciones y su proyecto, explora la memoria autorizada y consulta la misma capacidad MCP con argumentos de alcance fijados por el servicio. Una corrección versionada se aplica a ambos sin copiar lógica.

Compartir aprendizajes, revisar y publicar permanece en la visión; no es un paso obligatorio para cada tarea con herramientas ya autorizadas. Los archivos y capacidades precargados en el manifiesto sintético son configuración confiable de desarrollo, no un workflow de aprobación implementado.

## Decisiones siguientes

1. Probar conversación con la API personal de OpenAI configurada fuera del chat.
2. Elegir autenticación, almacenamiento y custodia productivos para el siguiente incremento.
3. Elegir la primera integración externa personal y concretar escritura y publicación de memoria.

Nombre, visibilidad y licencia se decidirán antes de crear o publicar el repositorio remoto en `jackspolski1103`. El [registro de decisiones](docs/decisions/README.md) conserva el resto de las propuestas pendientes.

## Licencia

La visión sugiere Apache-2.0. La licencia definitiva permanece pendiente de elección; todavía no se incluye un archivo LICENSE ni se afirma que este repositorio esté publicado bajo esa licencia.
