# Primer incremento: dos agentes, una capacidad compartida y memoria navegable

Estado: alcance aprobado en [0005](decisions/0005-primer-corte-capacidad-compartida-mcp.md)
y ampliado con el modelo de memoria confirmado en
[0006](decisions/0006-memoria-como-repositorio-con-permisos.md).

## Resultado del corte

Un servicio compartido Python mantiene contexto, agentes especializados, capacidades
versionadas y permisos. Un CLI conversacional se conecta a ese servicio. Dos agentes
de ejemplo reutilizan una capacidad de consulta por MCP y navegan un repositorio
de memoria dentro de sus permisos.

El criterio principal es corregir una capacidad una sola vez y comprobar su aplicación
en ambos agentes conservando sus reglas particulares y aislamiento. Usar herramientas
ya autorizadas no exige publicar un aprendizaje en cada tarea.

## Recorrido de aceptación

1. Alice se autentica en el servicio de desarrollo y accede al agente de costos;
   Bob accede al de contratos.
2. Cada persona delega una tarea conversando desde el CLI. El servicio combina contexto
   publicado de la organización e instrucciones de la especialización.
3. El agente puede listar carpetas y leer archivos de memoria autorizados por iniciativa
   propia, respetando los permisos de cada ancestro y de la audiencia.
4. El modelo propone una consulta. El servicio fija el proyecto y los límites, valida
   los argumentos y ejecuta la capacidad mediante MCP.
5. Una nueva versión de la capacidad se registra en un solo lugar. Ambos agentes usan
   la corrección conservando sus propios datos y tareas.
6. Fallas de herramientas producen errores clasificados consistentes. Denegaciones,
   revocaciones y cambios de contexto se verifican antes de entregar datos o volver a
   enviarlos al modelo.

## Implementación y verificación

| Parte | Implementación | Verificación |
|---|---|---|
| Servicio | API HTTP, registro compartido y membresías de desarrollo. | Denegaciones por organización, proyecto, audiencia y sesión; revalidación tras esperas. |
| MCP | Cliente SDK oficial y servidor HTTP sintético. | Sockets reales y corrección común aplicada a ambos agentes. |
| Memoria | Árbol virtual con listado/lectura y herencia restrictiva. | Ocultamiento, traversal, aislamiento, revocación e invalidación de historial. |
| Runtime y CLI | Ciclo acotado, sesiones, cancelación y cliente conectado. | Tests con modelo programado y API HTTP. |
| OpenAI | Adapter Responses con credencial personal fuera de prompts. | Contrato HTTP con transporte de prueba; conversación real pendiente de configuración. |

## Estado de desarrollo

Registro, sesiones y memoria están en el proceso del servicio y se pierden al
reiniciarlo. Los tokens de desarrollo permiten comprobar aislamiento del servidor con
identidades diferentes; no son un login productivo ni seleccionan un proveedor de identidad.

Los datos y documentos son sintéticos. El modelo programado conduce llamadas conocidas
y no demuestra razonamiento. El servidor MCP no es correo ni Databricks; conectar esos
sistemas requiere otro incremento con cuentas personales autorizadas. El CLI no tiene
un modo personal autónomo.

El primer repositorio de memoria permite listar y leer. Escribir, corregir o promover
archivos conversacionalmente queda pendiente. La configuración precargada es de confianza
y no implementa el workflow editorial completo.

## Siguiente incremento

Probar conversación con la API personal OpenAI elegida y evaluar el recorrido. Luego
elegir identidad, almacenamiento e integración externa. La visión conserva memoria
corregible y el ciclo de candidatos, revisión, publicación y retirada.

Los comandos reales y la configuración están en [Desarrollo](development.md).
