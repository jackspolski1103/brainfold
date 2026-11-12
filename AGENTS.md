# Instrucciones del proyecto

## Contexto confirmado

- Este es un proyecto personal del usuario, independiente de su trabajo.
- La cuenta personal de GitHub elegida por el autor es `jackspolski1103`. Toda creación o publicación del proyecto debe usar esa cuenta; verificar la identidad autenticada antes de escribir en GitHub.
- No usar datos, cuentas, repositorios, servicios ni credenciales laborales para implementarlo.
- El alcance vigente está en `docs/scope.md` (decisión `0008`). Antes de proponer o construir algo, comprobar que no figura en su tabla «Lo que no es». `docs/vision.md` y `docs/research/` son antecedentes históricos, no el plan.
- El autor quiere participar en decisiones de producto y arquitectura durante la construcción.
- El producto es un cerebro compartido agnóstico al harness: carpetas y archivos con permisos expuestos por MCP para Claude Code, Codex u otros. No construir ni proponer un harness propio como producto. Python es la elección confirmada. Véase `docs/decisions/0007-cerebro-agnostico-al-harness.md`.
- La colaboración es el núcleo: un servidor por equipo al que cada persona conecta su harness. El autor rechazó el modo local por persona; no volver a proponerlo.
- La experiencia cotidiana es conversacional dentro del harness de cada persona; no exigir comandos ni administración manual de memoria.
- El panel web sigue el estilo de Infisical o Langfuse: React (Vite, shadcn/ui) sobre la API del servidor Python, con cuentas propias de email y contraseña (decisión `0009`). Su primera versión cubre accesos por carpeta, miembros y tokens, explorador de solo lectura y actividad. No construir editor web de contenido ni motor de revisión y aprobación.
- La memoria se concibe como un repositorio navegable de carpetas, subcarpetas y archivos con permisos. El agente puede explorar libremente dentro de su autorización, sin exigir gestión manual al usuario. Hay listado, lectura, escritura y búsqueda sobre disco (`src/oif/brain.py`); promoción y revisión siguen pendientes. Véase `docs/decisions/0006-memoria-como-repositorio-con-permisos.md`.

- Todo el contenido del repositorio debe estar en inglés: código, nombres de herramientas, mensajes de error, documentación, ejemplos y este archivo (instrucción explícita del autor, 12/11/2026). Lo existente en español se traduce como parte del plan del core; todo archivo nuevo se escribe en inglés. La conversación con el autor sigue en español.

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
