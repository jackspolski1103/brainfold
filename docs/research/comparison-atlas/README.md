# Un mismo caso: Team Memory, cq y Markdown con revisión por PR

**Fecha:** 11 de noviembre de 2026.  
**Caso:** `atlas-webhook-001`, exclusivamente sintético.  
**Objetivo:** comparar publicación y reutilización controladas, no calidad de modelos.  
**Estado:** experimentos locales y revisión de código/documentación; no piloto con usuarios ni auditoría integral.

## 1. Conclusión

**De estas tres alternativas, Team Memory es la más cercana al gobierno que buscamos; Git es un baseline de producto serio; el servidor OSS de cq probado no ofrece el aislamiento por proyecto/persona exigido por este caso.** Esto no clasifica su calidad general: sus objetivos y contratos son diferentes.

El hallazgo más útil es que **contenido visible, contenido revisado y contenido autorizado para reutilización no son la misma cosa**:

- Team Memory protege ámbitos privados y promoción, pero su búsqueda puede devolver memorias `unverified`, incluso después de editar una lección previamente aprobada.
- cq mantiene propuestas fuera de la consulta normal hasta aprobarlas, pero el servidor abierto probado no representa los roles Atlas/Boreal; permite consultar conocimiento aprobado sin autenticación.
- Git puede distribuir únicamente una versión publicada, pero proteger `main` no oculta las ramas candidatas a lectores del mismo repositorio. Un repositorio de distribución separado resuelve esa parte de la exposición.

Por eso, antes de construir un motor nuevo, conviene decidir qué significa «compartido»: ¿todo lo visible para un equipo, indicando su confianza, o únicamente versiones explícitamente publicadas para consumo por agentes?

**No se eligió ninguna dependencia ni cambió la arquitectura del proyecto.** La comparación aporta evidencia para esa decisión.

## 2. Caso común y condiciones de comparación

Ana trabaja en privado y descubre una regla para evitar procesamiento duplicado de webhooks. Su conversación incluye un cliente ficticio, una hora de incidente y un marcador que parece un secreto, pero no es válido. La propuesta compartida elimina esos detalles y conserva la lección.

| Actor | Autoridad del caso |
| --- | --- |
| Ana | Mantiene su ámbito privado; puede proponer compartir una versión |
| Bruno | Mantiene el destino Atlas; puede revisar el texto propuesto, pero no el historial privado de Ana |
| Carla | Solo pertenece a Boreal; no puede leer Atlas |
| Diego | Puede opinar sobre exactitud; no puede publicar |
| Elena | Consume publicaciones de Atlas; no es revisora de borradores |

La lección v1 conserva `event_id` como clave de idempotencia y limita el entorno sintético a cinco reintentos. La v2 corrige el límite a tres. Una skill derivada conserva inicialmente el valor cinco. **Estos valores son material de prueba, no recomendaciones técnicas universales.**

Recorrido:

1. Conservar el origen privado y preparar un candidato saneado.
2. Consultar antes de aprobación.
3. Revisar una versión y luego editarla.
4. Promover y recuperar la lección como otro usuario.
5. Intentar acceso de Carla y publicación de Diego.
6. Intentar ampliar la audiencia de proyecto a organización.
7. Revocar una pertenencia.
8. Corregir la lección y observar su procedimiento derivado.
9. Retirar contenido y distinguir futuras lecturas de copias ya entregadas.

El [fixture común](case-atlas.json) contiene los textos y actores. La preparación del candidato fue manual e idéntica en significado; los adapters lo traducen al formato de cada sistema. **No evaluamos extracción automática, anonimización semántica, calidad de respuesta del LLM, ahorro de tiempo humano ni mejora de tareas.**

### Tres controles distintos

- **Confidencialidad del origen:** Bruno no obtiene la conversación de Ana.
- **Confidencialidad del candidato:** solo ciertos revisores pueden ver el borrador. Puede ser necesaria o no si el contenido ya está saneado.
- **Consumo aprobado:** el agente no trata borradores o correcciones sin revisar como procedimientos autorizados.

No consideramos toda visibilidad de un borrador una filtración. Lo que importa es si viola la audiencia elegida o si el consumidor lo usa como aprobado. El ensayo identifica esas diferencias; no presupone que los tres productos prometan la política más estricta.

## 3. Qué se ejecutó realmente

| Alternativa | Superficie ejercitada | Límites de la evidencia |
| --- | --- | --- |
| Team Memory | Servicios Go y PostgreSQL/pgvector aislado; caso propio y tests de seguridad upstream | Los principales y la condición de sesión de portal los construye el fixture; no login OIDC ni navegador humano extremo a extremo |
| cq | API FastAPI real en proceso con SQLite efímero, usuarios/contraseñas/API keys sintéticos; tests upstream y pruebas del almacenamiento local | No se desplegó el servicio hospedado, ni se probó un cliente de agente completo |
| Markdown + PR | Git real con repositorios y clones locales; ocho aserciones, incluidas dos configuraciones de distribución | Sin servidor GitHub, cuentas, ACL remotas ni un PR real; protecciones de revisión se contrastaron documentalmente |

Resultados de ejecución: **5 tests de Team Memory** —uno propio y cuatro upstream— pasaron; **78 tests upstream de cq** pasaron, además del recorrido propio API y la prueba local; **8 aserciones Git** pasaron. Las cantidades no son comparables como puntuación de seguridad o de producto.

Versiones fijadas:

- Team Memory: `6a537166b7cff7b5198d86f0c1167df0dc34b836`.
- cq: `2e538ec61b3f136d8aca6dd95db522118dda64eb`.
- Git: `2.51.0`; Node del baseline: `v22.22.1`.

Team Memory se probó con Go 1.27.3 y PostgreSQL 16.14/pgvector disponible localmente; el proyecto recomienda PostgreSQL 17. No se ejecutó detector de carreras. cq se probó con SQLite y sin embeddings. Las diferencias de entorno impiden convertir esto en una certificación del despliegue recomendado.

**E** = ejecutado; **C** = trazado en código; **D** = documentado; **NV** = no verificado aquí. Una aserción que pasa puede confirmar una limitación: no es una puntuación de requisitos satisfechos.

## 4. Resultado comparativo

| Paso o propiedad | Team Memory | cq OSS probado | Markdown + PR |
| --- | --- | --- | --- |
| Origen privado de Ana | **E:** otras identidades no lo obtienen | El origen se mantuvo fuera del servidor; aislamiento de su almacenamiento privado multiusuario **no probado** | **E:** se mantuvo fuera de los repos compartidos; ACL entre personas **no probada** |
| Candidato antes de aprobación | **E:** privado no se filtra; si se crea en Atlas es visible como `unverified` para sus lectores | **E:** no aparece en consulta normal; otras cuentas autenticadas pueden verlo por la superficie de revisión | **E:** rama candidata accesible en el mismo repo; no se distribuye en variante de repos separado |
| Edición tras revisión | **E:** aprobación anterior invalidada; revisión vieja rechazada | **E/C:** el endpoint probado no ofrece revisión esperada/audiencia; no tiene edición equivalente por PATCH | **E:** cambia el commit; **D:** GitHub puede invalidar aprobaciones con configuración adecuada |
| Consentimiento origen/destino | **E:** Ana solicita, Bruno acepta, sin lectura del historial privado | No es representable con los roles del servidor probado | Proceso y permisos de dos repos pueden construirlo; **no ejecutado** como workflow remoto |
| Carla fuera de Atlas | **E:** lectura denegada | **E:** consulta aprobada accesible a Carla y anónimos; no frontera Atlas/Boreal | **D:** depende de permisos del repositorio; ACL no ejercitadas localmente |
| Diego no publica | **E:** lector no finaliza; no rol nativo independiente de verificador editorial | **E:** otra cuenta autenticada aprueba; no rol de publicador por proyecto | **D:** Read/Triage puede comentar, sin fusionar; su opinión no cuenta como aprobación obligatoria con Write |
| Ampliar a organización | **E:** requiere autoridad en el siguiente destino | No hay audiencia de proyecto equivalente en el contrato probado | Cambiar audiencia requiere distribución/permisos separados; no está vinculado automáticamente al PR |
| Revocación | **E:** la siguiente lectura del miembro retirado se deniega | **E:** API key revocada no escribe; las lecturas públicas siguen disponibles | Acceso remoto futuro depende del servidor; **E:** clones anteriores siguen conteniendo el texto |
| Corrección y skill derivada | **E:** no hay actualización automática de una memoria independiente; edición pública queda visible `unverified` | **E:** registrar corrección y marcar error no retira automáticamente la versión anterior | **E:** cambiar `lesson.md` no cambia `skill.md`; puede añadirse proceso/CI |
| Recuperación de lección publicada | **E:** búsqueda con identidad autorizada | **E:** consulta API; no se demostró aislamiento del equipo | **E:** búsqueda lexical desde otro checkout |
| Retirada de la lección | **E:** archivar la excluye de búsqueda predeterminada; conserva historial autorizado | **E:** revoke local elimina del store; la ruta remota intentada no existe en el servidor probado | **E:** eliminar del árbol actual no elimina historial ni clones |
| Copias ya entregadas | Persisten fuera del control de próximas lecturas | Snapshot JSON previo persiste | Historial y clones previos persisten |

No se evaluó latencia comparable ni rendimiento semántico. Los tests no son equivalentes en cobertura: en especial, no se deben comparar controles reales de PostgreSQL con ACL de GitHub que aquí solo se leyeron en documentación.

## 5. Team Memory: lo que resolvió y lo que habría que cambiar

### Comprobado en la prueba

El ámbito personal se configuró como hijo de Atlas, sin herencia que concediera a Bruno lectura del hijo. Ana almacenó el origen y, por separado, el candidato manualmente saneado. El lector Atlas no encontró el candidato privado. La promoción transfirió una instantánea autorizada; Bruno no obtuvo acceso al historial privado. Se denegaron intentos de finalizar sin autoridad de destino.

La aprobación está vinculada a revisión y el cambio de contenido la invalida. La ampliación hacia organización requiere autoridad allí. Revocar la membresía bloqueó la siguiente lectura. Los tests upstream seleccionados ejercitaron adicionalmente revisión ligada a versión, promoción obsoleta/cancelada y revocación.

Archivar la lección la excluyó de la búsqueda predeterminada, manteniendo dos revisiones consultables en su historial autorizado. No se probó exportación/importación ni borrado físico.

### Diferencia decisiva respecto de la política estricta

**`approved` es una clasificación de confianza, no un filtro obligatorio de visibilidad.** Una edición pública pasó a `unverified` y siguió apareciendo en búsqueda. También apareció un registro nuevo creado directamente en el ámbito compartido sin aprobación.

Esto concuerda con su contrato: el rechazo mantiene el conocimiento visible como no aprobado; archivarlo es una operación distinta. No es una vulnerabilidad deducida de una promesa inexistente. [Servicio de revisión fijado](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/internal/memory/review.go).

Si quisiéramos **solo versiones aprobadas para uso operativo**, un cliente podría filtrar por confianza, pero eso no constituye por sí solo una frontera de confidencialidad. Además, si la nueva edición reemplaza la versión corriente, filtrar `unverified` puede dejar al usuario sin la última versión aprobada. Conviene evaluar un modelo con borrador y publicación separados, o recuperación explícita de la última versión publicada. No está implementado por nuestro proyecto.

### Lo que no quedó resuelto

- No se probó extracción desde conversaciones ni redacción automática: el candidato ya estaba preparado.
- Diego fue modelado como lector. No existe en el ensayo una capacidad nativa de «certificar exactitud pero no autorizar publicación».
- La skill fue otra memoria independiente, sin vínculo causal genérico declarado. Que siguiera en cinco reintentos no demuestra que ninguna extensión pueda gestionarla; muestra el trabajo adicional necesario en esta configuración.
- Se ejercitó servicio y DB, no login, UX de navegador, dos dispositivos ni uso por personas reales.

**Lectura para nuestro proyecto:** fuerte referencia para permisos y promoción; no es un reemplazo inmediato del CLI ni del ciclo completo de aprendizaje.

## 6. cq: compartir aprendizajes no equivale a aislar una organización

### Comprobado en el servidor abierto

Se crearon cuentas sintéticas y se usaron login y API keys reales del código, en un cliente HTTP de pruebas sin puerto expuesto. La propuesta no apareció en la consulta normal antes de aprobar. Otras cuentas autenticadas pudieron verla mediante revisión; después de aprobar, fue consultable sin autenticación y por Carla.

Incluso un objeto devuelto con `tier: private` fue accesible por esa consulta del servidor. **El valor del campo no debe interpretarse como garantía de aislamiento de ese backend.** Esto describe la revisión fijada del servidor OSS, no el comportamiento de `cq.exchange` ni de namespaces hospedados.

La ruta de aprobación no implementó la audiencia y la revisión esperada que agregamos como datos de prueba. No presentamos eso como un bypass de una validación prometida: son campos fuera de ese contrato. El intento de edición vía PATCH tampoco representa un workflow de edición soportado.

Revocar una API key impidió la escritura posterior. La lectura permaneció disponible porque es pública en esa superficie. Registrar la corrección y marcar la lección anterior como incorrecta no la eliminó de la consulta.

La retirada local **sí funcionó**: con el SDK del checkout y un store en memoria, la consulta pasó de una unidad a cero después de `revoke`. La copia JSON anterior permaneció intacta. En cambio, la ruta remota de retirada intentada devolvió 404 en este servidor; no corresponde concluir que «cq no permite retirar recuerdos» en todas sus modalidades.

### Lectura para nuestro proyecto

Para una comunidad que comparte aprendizajes, esas decisiones pueden ser adecuadas. Para Atlas/Boreal haría falta otra frontera de autorización: instancias separadas, controles externos o implementación de ámbitos y revisores. Una instancia por equipo tampoco reproduce automáticamente el espacio privado de cada integrante ni toda la promoción entre niveles.

No recomendaría asumir que podemos agregar nombres de proyectos o `tier` y obtener el modelo de privacidad deseado. Antes de usarlo como núcleo, habría que probar esa composición explícitamente.

La experiencia de integración con agentes y su formato de conocimiento siguen siendo referencias útiles. [Servidor y contrato de cq](https://github.com/mozilla-ai/cq/tree/2e538ec61b3f136d8aca6dd95db522118dda64eb/server/backend), [documentación](https://docs.mozilla.ai/cq).

## 7. Markdown + PR: dos baselines, no uno artificialmente débil

### A. Un repositorio compartido

La conversación queda fuera del repositorio. Ana propone solo el texto saneado; Bruno revisa; los consumidores leen únicamente la rama o release publicada.

En Git local se comprobó que `main` no contenía el borrador, pero el clon tenía acceso a la rama candidata. Eso **no es un problema de confidencialidad si todos los lectores ya estaban autorizados a ver el candidato saneado**. Sí obliga a que el consumidor distinga borrador de versión publicada.

Esta configuración puede ser suficiente para un equipo pequeño. No requiere inventar un servicio de memoria para demostrar que una lección compartida ayuda.

### B. Revisión restringida y distribución separada

Si los candidatos deben permanecer restringidos:

1. La conversación original queda en el espacio privado de Ana.
2. El candidato saneado entra en un repositorio de revisión con acceso limitado.
3. Se revisa la versión exacta.
4. Una publicación copia solamente esa instantánea a un repositorio de distribución para Atlas.
5. No se espejan el historial ni las ramas del repositorio de revisión.

El experimento G8 comprobó la separación de contenido: el clon de distribución no contenía la rama candidata ni el commit de la versión no publicada. **No comprobó la autorización del publicador ni configuró los permisos remotos.** Esa automatización también debe verificar que la versión copiada es la aprobada.

### Qué aporta GitHub y qué no se probó

GitHub permite exigir revisiones, descartar aprobaciones cuando cambia el diff y evitar determinados bypass. Son opciones que hay que configurar; no vienen garantizadas por escribir un README que diga «requiere aprobación». La disponibilidad depende del plan y del tipo de repositorio. [Protecciones de ramas](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

En repositorios de organizaciones, Read/Triage permite aportar comentarios sin publicar; las aprobaciones obligatorias requieren permisos de escritura. No asumimos la misma granularidad para el futuro repo personal del usuario. `CODEOWNERS` gobierna revisiones, no lectura de carpetas. [Roles](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization), [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).

Una corrección no actualizó la skill automáticamente. Retirar un archivo no eliminó commits ni clones previos. Esto no vuelve inútil a Git: requiere metadatos, revisión manual o automatización para mantener dependencias. Ninguna alternativa puede prometer borrar copias externas ya entregadas. [Límites del borrado en GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

## 8. Qué aporta valor propio después de esta comparación

No aparece una razón para reconstruir todos los motores. Sí aparecen tareas concretas que un CLI podría facilitar:

1. **Preparar el candidato:** mostrar exactamente qué sale del espacio privado y qué detalles se omitieron.
2. **Separar publicación de edición:** conservar una versión utilizable mientras una corrección se revisa, o ponerla en cuarentena si corresponde.
3. **Aplicar audiencia y autoridad:** no confundir la identidad de quien pregunta con el conjunto de destinatarios.
4. **Mantener dependencias:** mostrar que una skill depende de una lección corregida y requiere revisión.
5. **Hacer visible el estado al agente:** distinguir consejo no verificado, procedimiento publicado y contenido retirado.

Son oportunidades de integración y experiencia, **no conceptos sin antecedentes**. Git ya tiene versiones y publicación; Team Memory ya tiene promoción autorizada. Nuestro valor tendría que ser que el recorrido completo resulte más fácil y útil que usar esas herramientas directamente.

### Recomendación provisional

- **Referencia de gobierno:** Team Memory.
- **Baseline mínimo de valor:** Markdown + PR, con una o dos superficies de distribución según la privacidad requerida.
- **Referencia de adopción por agentes:** cq, sin asumir que su servidor probado resuelve las ACL del caso.

No escogería ahora un framework definitivo. Primero definiría la semántica de publicación y escribiría el contrato del recorrido que nuestro CLI debería mejorar. Eso preserva Python y la experiencia terminal, sin comprometer un motor o una infraestructura.

## 9. Evidencia reproducible

- [Fixture canónico](case-atlas.json).
- [Experimento Git](git-baseline.mjs) y [resultados/operaciones](evidence/git/results.json).
- [Prueba y reproducción cq](evidence/cq/README.md).
- [Prueba y reproducción Team Memory](evidence/team-memory/README.md).

Para Git basta Node y Git; el script crea directorios nuevos y no usa red, cuentas, configuración global de Git ni hooks. No elimina los directorios generados. Las guías de cq y Team Memory fijan código, entorno y límites de las pruebas.

Los resultados de consulta usan búsquedas lexicales o filtros deterministas. No son evaluación de recuperación semántica ni de razonamiento. Los marcadores sintéticos ausentes demuestran únicamente que el texto preparado no los contenía, no que se hayan detectado automáticamente.

El contenedor PostgreSQL de la comparación y su volumen sintético fueron eliminados al terminar; esas bases eran descartables. Se conservan scripts, logs y resultados para reproducirlos. No quedó un servicio nuevo activo, no se publicó un repo/PR y no se usaron cuentas ni datos laborales. Los checkouts, entornos y caches de prueba permanecen localmente en `work/comparison/`; no forman parte de los entregables del repositorio.

## 10. Lo que falta antes de afirmar que una alternativa resuelve nuestro producto

- Ejecutar el recorrido con dos personas y clientes reales, incluyendo login y aprobación.
- Medir si una lección ayuda en una tarea nueva, comparada con documentación manual.
- Medir el esfuerzo humano de preparación, revisión y mantenimiento.
- Probar cambios de audiencia concurrentes con una consulta y la latencia de revocación.
- Probar dos harnesses con la misma política, no dos llamadas del mismo test.
- Definir linaje entre fuente, lección y skill y probar correcciones, retirada e importación.
- Evaluar inyección de instrucciones y filtraciones semánticas, no solo marcadores.
- Configurar y verificar una instancia remota solo después de acordar cuentas, permisos e infraestructura.

**Decisión posterior a la comparación:** el autor confirmó que el primer prototipo incorporará automáticamente solo versiones compartidas aprobadas, publicadas, vigentes y autorizadas, con los borradores en un circuito de revisión separado. La elección y sus criterios se registran en [0003](../../decisions/0003-consumo-de-conocimiento-compartido.md); los resultados de esta comparación se conservan como evidencia previa a esa decisión.
