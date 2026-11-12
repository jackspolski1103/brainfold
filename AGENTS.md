# Instrucciones del proyecto

## Contexto confirmado

- Este es un proyecto personal del usuario, independiente de su trabajo.
- La cuenta personal de GitHub elegida por el autor es `jackspolski1103`. Toda creación o publicación del proyecto debe usar esa cuenta; verificar la identidad autenticada antes de escribir en GitHub.
- No usar datos, cuentas, repositorios, servicios ni credenciales laborales para implementarlo.
- `docs/vision.md` es la base conceptual aceptada; sus ejemplos y tecnologías son propuestas, no decisiones de implementación ya aprobadas.
- El autor quiere participar en decisiones de producto y arquitectura durante la construcción.
- El primer producto es un harness de agentes utilizable desde terminal. Python es la elección confirmada para lo agéntico.
- La colaboración es el núcleo del primer producto: CLI vinculado a un servicio y espacio compartidos. El autor rechazó el modo personal autónomo con colaboración opcional; no volver a proponerlo como primera entrega. La ubicación de ejecución, persistencia y alojamiento sigue pendiente.
- La experiencia cotidiana debe ser conversacional y natural. No exigir comandos ni administración manual de memoria; las decisiones necesarias se presentan dentro de la conversación. Esto no autoriza compartir contenido privado automáticamente ni decide la política editorial.
- Primero se concreta la documentación y luego se construye sobre ella. No iniciar una aplicación web ni implementar el runtime antes de cerrar el alcance del primer incremento con el autor.
- El primer corte quedó aprobado: servicio compartido Python, CLI conversacional, MCP real con datos sintéticos y dos agentes especializados que reutilizan una capacidad versionada con permisos y errores consistentes. Véase `docs/decisions/0005-primer-corte-capacidad-compartida-mcp.md`. El autor eligió API personal de OpenAI para la primera conexión real al modelo. El alcance ya permite implementar este corte; no volver a pedir su aprobación.
- La memoria se concibe como un repositorio navegable de carpetas, subcarpetas y archivos con permisos. El agente puede explorar libremente dentro de su autorización, sin exigir gestión manual al usuario. El primer corte incorpora listado y lectura; escritura y promoción siguen pendientes. Véase `docs/decisions/0006-memoria-como-repositorio-con-permisos.md`.

## Cómo colaborar

- Avanzar en incrementos pequeños y revisables.
- Antes de comprometer infraestructura, proveedor de identidad, alcance del MVP, licencia o una publicación externa, presentar una recomendación concreta con su principal alternativa y consultar la elección. No reabrir elecciones ya confirmadas sin una razón concreta.
- Preguntar pocas decisiones por vez, cuando afecten el siguiente incremento. Continuar trabajo independiente mientras llega la respuesta.
- Resolver detalles rutinarios de implementación sin pedir confirmación repetida.
- Registrar decisiones confirmadas en `docs/decisions/`; distinguir propuestas de acuerdos.
- No presentar una demo, un adapter simulado o una interfaz como funcionalidad productiva implementada.
- Explicar cambios, validación y siguiente decisión en español.

## Credenciales y permisos

- No pedir al usuario que pegue contraseñas o tokens en el chat.
- Nunca versionar secretos, archivos de entorno reales ni datos de usuarios.
- Mantener separados identidad, autorización, conexiones de herramientas y credenciales de modelos.
- Los secretos no se incluyen en prompts ni resultados del modelo. Las operaciones externas pasan por componentes de confianza autorizados, locales o del servidor según el modo de ejecución.
- El contenido privado y los derivados mantienen su alcance salvo promoción explícita.
- Comprobar tanto solicitante como audiencia de la respuesta.

## Implementación y verificación

- Mantener el núcleo independiente de proveedores concretos mediante contratos y adapters.
- Probar denegaciones, aislamiento y revocación al implementar estos comportamientos.
- Mantener los tests proporcionales al cambio; una modificación documental no requiere servicios ni llamadas a proveedores.
- Evitar gastos, despliegues y servicios externos hasta que formen parte del incremento elegido.
