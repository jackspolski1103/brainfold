# 0005 — Primer corte: dos agentes y una capacidad compartida mediante MCP

Fecha: 11 de noviembre de 2026.

Estado: alcance aceptado por el autor con «dale» ante la propuesta del primer corte.

## Contexto

El autor aclaró que necesita agentes que trabajen con herramientas conectables mediante
MCP y reutilicen capacidades, convenciones y conocimiento operativo entre soluciones.
Compartir aprendizajes es parte de la visión; no agota el recorrido principal. La
consulta de los proyectos existentes sirvió para comprender el problema, sin importar
código, datos o credenciales laborales al proyecto personal.

## Alcance confirmado

1. Servicio compartido en Python con contexto, capacidades y permisos.
2. CLI conversacional con herramientas conectables mediante MCP.
3. Dos agentes de ejemplo con tareas diferentes que reutilicen una capacidad de consulta
   y sus convenciones.
4. Corrección versionada en un solo lugar, verificada en ambos agentes, con comportamiento
   consistente ante errores y denegaciones.

Los ejemplos utilizan datos sintéticos. La conexión MCP debe ser real. Un servidor MCP
de ejemplo no equivale a una integración productiva con correo o Databricks.

## Orden de construcción

Se implementan primero los contratos, el servicio y la interoperabilidad MCP con pruebas
de aislamiento y revocación. El CLI consume ese servicio; no tiene un modo personal
autónomo. El runtime integra un modelo mediante un adapter configurable.

El autor eligió API personal de OpenAI para el primer acceso real al modelo. El adapter
recibe el nombre del modelo y la credencial desde el entorno del servicio; la clave no
se pide por chat ni se comparte con los MCP. Los modelos programados de tests solo
verifican el ciclo del runtime, no su razonamiento ni la utilidad de una conversación real.

## Límites del incremento

La primera implementación de desarrollo puede mantener estado en memoria y usar
credenciales de prueba explícitas para verificar aislamiento del servicio. No constituye
un proveedor de identidad productivo ni persistencia durable. La ubicación de alojamiento,
el proveedor de identidad y la custodia productiva siguen pendientes.

No incluye integración laboral, envío real de correos, shell del usuario, alertas
programadas ni publicación automática. Las especializaciones de los dos ejemplos no
obligan a implementar todos los comportamientos posibles de los proyectos que inspiraron
la discusión.

## Verificación

- Dos agentes consumen la misma versión de capacidad por el servicio.
- Un cambio de versión se refleja en ambos sin copiar lógica por agente.
- Las reglas particulares y permisos de cada proyecto se conservan.
- El servicio impide acceso a otra organización o proyecto, a otra sesión y a una
  audiencia sin permiso.
- La revocación bloquea nuevas recuperaciones y usos, incluidas sesiones ya abiertas.
- El protocolo MCP se ejercita contra un servidor sintético con transporte real.
- El runtime no puede convertir texto de herramientas o mensajes del cliente en permisos.

Esta decisión concreta [0004](0004-colaboracion-como-nucleo-del-producto.md): el primer
recorrido prueba reutilización operativa entre agentes especializados. La política de
conocimiento aprobado y publicado de [0003](0003-consumo-de-conocimiento-compartido.md)
se conserva; el flujo editorial completo se desarrollará en otro incremento.
