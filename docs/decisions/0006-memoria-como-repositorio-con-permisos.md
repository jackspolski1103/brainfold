# 0006 — Memoria navegable como repositorio con permisos

Fecha: 11 de noviembre de 2026.

Estado: modelo de producto confirmado por el autor durante la construcción.

## Elección del autor

«Pienso la memoria como un sistema de archivos con permisos donde hay carpetas y
subcarpetas y permisos y el agente se pueda ir moviendo por el repositorio a gusto
siempre y cuando tenga permisos».

El agente puede explorar el repositorio por iniciativa propia para realizar una tarea.
La persona no necesita administrar memoria ni ejecutar una búsqueda manual en cada turno.

## Aplicación al primer corte

Se añaden carpetas y archivos de memoria con rutas y permisos, y herramientas para
listar directorios y leer archivos desde el servicio compartido. El repositorio es
virtual: el contrato de navegación no depende del sistema de archivos de la computadora
del usuario ni selecciona un almacenamiento persistente.

Como mecanismo inicial de implementación, se aplican restricciones de los ancestros
por intersección: un hijo puede restringir el acceso, y no puede ampliar el permiso de
su carpeta padre. Un nodo sin permisos propios hereda; sin ninguna concesión aplicable
el acceso se deniega. Se verifica a solicitante y audiencia y se ocultan entradas no
autorizadas antes de entregarlas al agente. Se bloquean rutas que intentan salir o
evadir el repositorio.

Los documentos de proyecto y personales conservan su alcance. Compartir un archivo
no se deduce de mover el contexto de una conversación. La navegación habitual de este
corte expone solo entradas publicadas y autorizadas; los borradores compartidos siguen
fuera del consumo habitual conforme a [0003](0003-consumo-de-conocimiento-compartido.md).

El primer almacenamiento es en memoria del proceso y usa contenido sintético. Cambiar
su revisión invalida el contexto anterior del runtime antes de seguir enviándolo al
modelo; revocar acceso bloquea nuevas lecturas. Esto no elimina respuestas ya entregadas.

## Pendiente

Escritura y corrección conversacional de archivos, promoción entre carpetas con
audiencias distintas, interfaces de administración de ACL, almacenamiento durable,
permisos por operación distintos de lectura y navegación y consulta histórica. No se
promete todavía un editor de archivos ni acceso irrestricto a repositorios del equipo.

Esta decisión complementa [0005](0005-primer-corte-capacidad-compartida-mcp.md) sin
cambiar el alcance aprobado de MCP, servicio compartido y capacidad reutilizada por
dos agentes.
