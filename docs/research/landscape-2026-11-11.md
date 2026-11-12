# Inteligencia organizacional colaborativa: panorama, antecedentes y oportunidad

**Fecha de corte:** 11 de noviembre de 2026.  
**Proyecto:** personal, nombre provisional OIF.  
**Cobertura:** 49 entradas comparativas de productos/proyectos, 9 trabajos académicos y 128 enlaces únicos a fuentes primarias; distinta profundidad por alternativa.  
**Pregunta:** ¿ya existe algo parecido al harness propuesto, qué queda por resolver y dónde podría aportar valor?

**Seguimiento:** después de esta investigación documental se ejecutó una [comparación del mismo caso en Team Memory, cq y Git](comparison-atlas/README.md). Aporta evidencia nueva y distingue aprobación, visibilidad y publicación; las limitaciones de ejecución declaradas en este panorama corresponden a esta primera investigación, no a ese seguimiento.

## Resumen ejecutivo

**Sí: existen alternativas muy parecidas, y algunas cubren partes que inicialmente parecían distintivas.** No encontramos solamente RAG, chatbots o bases vectoriales. Encontramos aprendizaje entre usuarios, memoria privada y compartida, propuestas de conocimiento, aprobación por versión, promoción entre ámbitos, skills que mejoran desde conversaciones, agentes de terminal, permisos y trabajo explícito sobre interoperabilidad.

Los antecedentes más importantes para nuestra decisión son:

- **Mozilla `cq`:** aprendizaje compartido entre agentes y revisión de unidades de conocimiento. Su visión conceptual se parece mucho a la nuestra. [Documentación](https://docs.mozilla.ai/cq).
- **Team Memory:** servicio autohospedado con ámbitos jerárquicos, autorización, revisión de versiones y promoción con consentimiento de origen y destino. Es una prueba de concepto, no una solución de producción auditada. [Repositorio](https://github.com/team-memory/team-memory).
- **TeamAgentMemory:** aprendizaje desde conversaciones de varias personas, capas privadas/compartidas y skills aprobadas. [Repositorio](https://github.com/hsuanshao/TeamAgentMemory).
- **Dust:** mejora de skills a partir del uso conversacional, aprobación del editor y CLI interactivo. [Mejora de skills](https://docs.dust.tt/docs/user-documentation/agents/self-improving-skills), [CLI](https://docs.dust.tt/docs/developer-platform/dust-cli/dust-cli.md).
- **Caura y Buzz:** Caura ofrece memoria gobernada entre agentes y extracción de sesiones; Buzz aporta colaboración e identidades separadas para humanos/agentes. La integración específica entre ambos está propuesta, no construida. [Caura](https://github.com/caura-ai/caura), [Buzz](https://block.github.io/buzz/support.html), [estado de la integración](https://caura.ai/blog/buzz-agents-get-an-identity/).
- **OpenClaw, Letta y Hermes:** obligan a descartar como diferenciación suficiente «un agente de terminal que recuerda y aprende». OpenClaw además documenta conocimiento compartido y retirada de memoria con procedencia. [OpenClaw Knowledge](https://docs.openclaw.ai/plugins/knowledge/stores-and-access), [Letta](https://github.com/letta-ai/letta-code), [Hermes](https://github.com/NousResearch/hermes-agent).
- **Collaborative Memory, AIM y MixUA:** antecedentes de investigación muy directos sobre aprendizaje multiusuario, privacidad y ámbitos de memoria. [Collaborative Memory](https://arxiv.org/abs/2505.18279), [AIM](https://arxiv.org/abs/2609.12320), [MixUA](https://arxiv.org/abs/2611.10439).
- **Open Memory Protocol Initiative:** ya trabaja en un contrato abierto de intercambio de memoria, procedencia y ciclo de vida. Su especificación sigue siendo un borrador; no es un estándar adoptado. [Estado actual](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol).

**Conclusión estratégica:** hay antecedentes claros y una necesidad plausible que debemos validar, no un territorio conceptual vacío. La oportunidad sería construir una experiencia más útil, sencilla, portable y comprobable para un usuario concreto. No está demostrada todavía la necesidad de otro framework general ni la superioridad de nuestra propuesta.

**Recomendación:** mantener la intención de un CLI propio en Python, pero comparar primero un recorrido pequeño contra alternativas existentes. Si una extensión resuelve ese recorrido, extender o contribuir puede aportar más valor que reconstruir un harness completo. Esta es una recomendación, no una decisión de arquitectura ya aceptada.

## Índice

1. [Alcance y calidad de la evidencia](#1-alcance-y-calidad-de-la-evidencia)
2. [Qué estamos comparando realmente](#2-qué-estamos-comparando-realmente)
3. [Los antecedentes más próximos](#3-los-antecedentes-más-próximos)
4. [Inventario comparativo ampliado](#4-inventario-comparativo-ampliado)
5. [Investigación académica y benchmarks](#5-investigación-académica-y-benchmarks)
6. [Protocolos y piezas que conviene reutilizar](#6-protocolos-y-piezas-que-conviene-reutilizar)
7. [Qué existe, qué no verificamos y qué no debemos prometer](#7-qué-existe-qué-no-verificamos-y-qué-no-debemos-prometer)
8. [Dónde podría aportar valor el proyecto](#8-dónde-podría-aportar-valor-el-proyecto)
9. [Diferencia frente a RAG, memoria y un coding agent](#9-diferencia-frente-a-rag-memoria-y-un-coding-agent)
10. [Credenciales y privacidad: implicaciones](#10-credenciales-y-privacidad-implicaciones)
11. [Construir, extender o integrar](#11-construir-extender-o-integrar)
12. [Validación antes de desarrollar demasiado](#12-validación-antes-de-desarrollar-demasiado)
13. [Riesgos y defensibilidad](#13-riesgos-y-defensibilidad)
14. [Impacto sobre nuestra documentación y decisiones pendientes](#14-impacto-sobre-nuestra-documentación-y-decisiones-pendientes)
15. [Trazabilidad de la inspección y límites](#15-trazabilidad-de-la-inspección-y-límites)

## 1. Alcance y calidad de la evidencia

Se investigaron cuatro capas en paralelo: harnesses de terminal, motores de memoria, productos empresariales y proyectos pequeños centrados en aprendizaje compartido. Se añadió literatura académica, protocolos y componentes de identidad/autorización. El inventario incluye más de cuarenta productos/proyectos, además de componentes y trabajos de investigación; no todos recibieron la misma profundidad.

La búsqueda usó términos como `shared agent learning`, `multi-user memory`, `private shared memory`, `knowledge promotion`, `revision-bound review`, `collective skill evolution`, `organizational agents`, `permission-aware memory` y `memory interoperability`, además de nombres específicos. Las reseñas y resultados de búsqueda se utilizaron para descubrir proyectos, no como evidencia final de sus capacidades.

### Niveles de evidencia

| Marca | Qué significa | Qué no significa |
| --- | --- | --- |
| **D** | Documentado en una fuente primaria efectivamente consultada | Probado independientemente o garantizado en toda edición |
| **C** | Se inspeccionó estáticamente código relevante | Auditoría completa, ausencia de vulnerabilidades o prueba ejecutada |
| **P** | Propuesta, borrador, roadmap o primitiva que permite construirlo | Función lista para usar |
| **NV** | No verificado con suficiente evidencia en esta investigación | Que la función no exista |
| **I** | Interpretación o recomendación propia | Hecho demostrado de mercado |

No se instalaron estos productos ni se ejecutaron sus suites. No se contrataron planes, usaron datos laborales, abrieron cuentas ni enviaron información privada. Los resultados de pruebas citados por los autores siguen siendo resultados de los autores.

Una documentación extensa demuestra intención y superficie de diseño; no demuestra confiabilidad operativa. Un repositorio pequeño puede contener un antecedente importante sin estar preparado para producción. Y un producto comercial puede resolver el problema aunque no encaje con nuestra preferencia open source.

## 2. Qué estamos comparando realmente

La propuesta no es únicamente «un bot con memoria». El recorrido deseado sería:

1. Una persona trabaja en privado desde la terminal, con su identidad y herramientas autorizadas.
2. El agente identifica una lección potencialmente útil.
3. Se prepara un candidato con contenido, evidencia protegida y audiencia propuesta.
4. Personas o políticas autorizadas validan exactitud y legitimidad de publicación.
5. Otra persona utiliza el aprendizaje desde su propio agente, sin recibir la conversación ni las credenciales originales.
6. El sistema gestiona correcciones, cambios de permisos y retirada del conocimiento que controla.

La tabla muestra por qué ya no alcanza con agregar características a una lista:

| Capacidad buscada | Antecedentes concretos | Lo que todavía debemos comprobar |
| --- | --- | --- |
| CLI y modelos intercambiables | Hermes, Deep Agents, OpenCode, goose | Que nuestra experiencia aporte algo por encima del runtime |
| Memoria personal y compartida | Letta, Basic Memory, Cognee, TeamAgentMemory | Semántica de privacidad, administradores y cada derivado |
| Aprender desde interacciones de varias personas | Dust, SkillClaw, TeamAgentMemory, MixUA | Utilidad, consentimiento y ausencia de divulgación indebida |
| Revisión y promoción | cq, Team Memory, Agent Memory System, TeamBrain, Guru | Identidad del revisor, versión y audiencia exactas |
| Permisos de fuentes y contexto | Onyx, Glean, Zep, Hindsight, OpenClaw | Revocación real, resultados derivados y audiencia final |
| Skills compartidas y evolución | Dust, Hermes, SkillClaw, Cognee, Skiva | Separar conocimiento aprobado de autoridad para ejecutar |
| Portabilidad entre harnesses | MCP, cq, memU, TeamBrain, COGX, OMPI | Preservar significado y restricciones, no solo transportar texto |
| Memoria con procedencia y retirada | OpenClaw, Agent Memory System, Collaborative Memory | Cobertura de derivados, copias y trabajos en curso |

Las fuentes y matices de cada fila están en las secciones siguientes. No es una tabla de equivalencia funcional: cada nombre cubre una parte distinta.

## 3. Los antecedentes más próximos

### 3.1 Mozilla cq: la visión general ya tiene un antecedente explícito

**D/P.** La propuesta de marzo de 2026 plantea conocimiento aprendido que circula entre agentes y niveles locales, privados y comunes. Expone revisión, confianza y procedencia como problemas centrales. Ese documento está marcado exploratorio; no se debe tratar toda su visión como código entregado. [Propuesta original](https://github.com/mozilla-ai/cq/blob/main/docs/CQ-Proposal.md).

**D.** La herramienta actual se integra con varios coding agents, consulta experiencias previas, propone descubrimientos y puede revisar una sesión para presentar aprendizajes. Tiene almacenamiento local y servidor. La documentación del servicio hospedado todavía coloca los namespaces organizacionales en roadmap. [Guía actual](https://docs.mozilla.ai/cq).

**C.** En el backend público revisado, la dependencia de sesión valida JWT; el servicio de revisión registra al revisor y cambia el estado de la unidad. Esas rutas no demuestran por sí solas una política granular de revisores por equipo/proyecto. No extrapolamos esta observación a la infraestructura del servicio hospedado. [Dependencias de autenticación](https://github.com/mozilla-ai/cq/blob/2e538ec61b3f136d8aca6dd95db522118dda64eb/server/backend/src/cq_server/api/deps.py), [servicio de revisión](https://github.com/mozilla-ai/cq/blob/2e538ec61b3f136d8aca6dd95db522118dda64eb/server/backend/src/cq_server/services/reviews.py).

**I.** Es una comparación obligatoria. No podríamos presentarnos honestamente como los primeros en proponer aprendizaje compartido agnóstico con revisión. Podría ser una base, un complemento o un proyecto al que aportar.

### 3.2 Team Memory: promoción gobernada implementada, aunque como prueba de concepto

**D.** `team-memory/team-memory` ofrece servicio MCP, ámbitos jerárquicos, memorias versionadas y portal de revisión. Declara explícitamente que es una prueba de concepto personal, sin revisión externa de seguridad y no recomendable para datos sensibles en producción. [README](https://github.com/team-memory/team-memory).

**C.** El código de promoción exige revisión habilitada para navegador, una revisión aprobada vigente y autoridad en origen. Publica una instantánea hacia el ámbito padre; el flujo contempla aceptación en destino sin abrir el historial privado de origen. Si una persona tiene autoridad en ambos lados, puede completar ambos pasos: no implica necesariamente dos humanos independientes. [Implementación de promoción](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/internal/memory/promotion.go), [comportamiento del portal](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/docs/portal.md).

**D.** Su modelo de amenazas documenta RLS, aprobación ligada a revisión, prevención de autoaprobación vía MCP y revocación de acceso sin caché de autorización en Go. Las pruebas nombradas no se ejecutaron en este trabajo. [Modelo de amenazas](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/docs/security/threat-model.md).

**I.** Es uno de los antecedentes más importantes: incluso «promover con permisos, consentimiento y versión exacta» ya tiene implementación pública. Queda por medir madurez, ergonomía, aprendizaje desde sesiones privadas, portabilidad y gestión integral de dependencias. No basta con agregar esas palabras a nuestro README.

### 3.3 TeamAgentMemory: personas distintas, aprendizaje compartido y límites explícitos

**D.** Este servicio en Rust conecta distintos harnesses y destila conversaciones en capas. Conversaciones y hechos individuales se mantienen por usuario; escenas y perfiles del agente compartido se construyen desde los hechos de sus participantes. También documenta skills de equipo con aprobación humana. [README](https://github.com/hsuanshao/TeamAgentMemory).

**D.** La guía precisa que los administradores del sistema pueden acceder a capas privadas y que usar el mismo agente implica aceptar que los hechos alimenten una representación común. Los agentes privados ofrecen otra configuración. [Modelo de colaboración](https://github.com/hsuanshao/TeamAgentMemory/blob/main/docs/COLLABORATION.md).

**I.** Es un solapamiento muy directo. Pero ocultar el transcript no prueba que una escena derivada no revele su contenido. Nuestro posible valor estaría en controlar cada transición de divulgación y hacerla comprensible, no simplemente en ocultar los originales.

### 3.4 Agent Memory System: evidencia, redacción y promoción como pasos separados

**D.** `rrrrrredy/agent-memory-system` conserva evidencia local, reconstruye candidatos y exporta memoria promovida a Git privado. Separa candidatos, validación y contenido utilizable. Su contrato aclara que la identidad del revisor es una declaración del caller, no una identidad humana autenticada. [Contrato del producto](https://github.com/rrrrrredy/agent-memory-system/blob/main/docs/product-contract.md).

**D.** La promoción vincula hashes, alcance, validación, redacciones y revisión previa; contempla supersesión y revocación. Autorizar una memoria no autoriza automáticamente cambiar una skill, hook o instrucciones del agente. [Promoción](https://github.com/rrrrrredy/agent-memory-system/blob/main/docs/promotion.md).

**I.** Aporta un antecedente especialmente útil para diseño y pruebas. También ilustra una frontera: un ledger local y una etiqueta `human` no sustituyen autenticación, autorización ni separación entre personas.

### 3.5 TeamBrain y MEX: la alternativa sencilla de Git ya existe

**D.** TeamBrain propone memoria Markdown compartida mediante PR, extracción a partir de sesiones, redacción local y consumo por MCP. Su flujo evita escribir directamente en la memoria de la rama principal; la protección efectiva también depende de las políticas y permisos del repositorio. [TeamBrain](https://github.com/donatienmigue/TeamBrain).

**D.** MEX organiza conocimiento de proyecto, propuestas revisables y traspasos de trabajo entre personas; distribuye archivos mediante Git y mantiene índices locales. Su identidad local y controles de integridad no equivalen a autenticación central de empleados. [MEX](https://github.com/mex-memory/mex).

**I.** Para equipos pequeños que ya comparten un repositorio, estos enfoques podrían resolver suficiente del problema con mucha menos infraestructura. Son baselines que debemos intentar superar, no descartar por parecer simples.

### 3.6 Dust: aprendizaje colectivo de skills como función de producto

**D.** Dust analiza conversaciones y correcciones, propone cambios a skills y exige que sus editores los acepten. El análisis se puede desactivar por workspace o skill. No verificamos qué puede ver un editor cuando la evidencia proviene de conversaciones de otras personas. [Self Improving Skills](https://docs.dust.tt/docs/user-documentation/agents/self-improving-skills).

**D.** Además ofrece CLI interactivo y una integración para invocarlo desde otros coding agents. Por tanto, tampoco sería correcto diferenciarse diciendo «lo nuestro sí funciona desde terminal». [Dust CLI](https://docs.dust.tt/docs/developer-platform/dust-cli/dust-cli.md).

**I.** Es un competidor funcional fuerte aunque no se haya verificado una distribución OSS equivalente al servicio. La comparación relevante es la tarea que resuelve, no si tiene el mismo lenguaje o forma de despliegue.

### 3.7 OpenClaw: más que un asistente con archivos de memoria

**D.** Knowledge tiene almacenes privados/compartidos, particiones por conversación, grants y autoridad de audiencia emitida por el host. Recomprueba permisos durante operaciones asíncronas. No convierte automáticamente un gateway compartido en aislamiento entre personas con confianza distinta. [Stores and access](https://docs.openclaw.ai/plugins/knowledge/stores-and-access), [multiusuario](https://docs.openclaw.ai/concepts/multi-user).

**D.** `memory-core` rastrea origen de entradas gestionadas, lo conserva al consolidar y permite retirar derivados identificables evitando reingestión. La cobertura excluye, entre otros casos, texto libre sin origen y copias fuera de los almacenes controlados. [Procedencia y borrado](https://docs.openclaw.ai/concepts/memory-provenance).

**I.** Esto refuta una supuesta novedad genérica de «lineage + revocación». La comparación pendiente es el flujo completo entre personas, ámbitos de negocio y harnesses, dentro de límites de seguridad expresamente probados.

### 3.8 Letta y Hermes: el aprendizaje personal ya se ofrece como producto

**D.** Letta Code es un runtime actual de terminal con memoria persistente y skills. La memoria compartida documentada es un repositorio de organización para agentes Cloud. Su dreaming puede pedir revisión a otro agente, pero esa modalidad no solicita aprobación humana. [Runtime](https://github.com/letta-ai/letta-code), [shared memory](https://docs.letta.com/concepts/shared-memory), [dreaming](https://docs.letta.com/configuration/memory).

**D.** Hermes puede generar y actualizar skills y dispone de aprobación de cambios pendientes. Los perfiles y proveedores externos de memoria permiten distintas configuraciones, pero un perfil no equivale por sí solo a una identidad humana aislada. [Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), [perfiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles).

**I.** Rehacer estas experiencias implica mucho trabajo que no prueba nuestra hipótesis colaborativa. Ambos deberían poder ser consumidores o comparadores, aunque mantengamos un CLI propio.

### 3.9 SkillClaw: aprendizaje entre usuarios sin necesidad de entrenar pesos

**D.** SkillClaw incorpora un proxy local y un evolver opcional para actualizar skills desde experiencias de varias personas. Soporta diferentes harnesses y almacenamiento local/S3/OSS. [Proyecto](https://github.com/AMAP-ML/SkillClaw).

**D.** Su documentación aclara que `group_id` es un namespace, no una frontera de autorización; el entorno compartido descrito no ofrece redacción automática de privacidad. La publicación directa es la configuración predeterminada y existe un flujo validado alternativo. [Guía y límites](https://raw.githubusercontent.com/AMAP-ML/SkillClaw/main/README.md).

**I.** El aprendizaje colectivo de procedimientos ya existe. Una contribución útil podría fortalecer su gobierno o integrarlo bajo una política, en vez de recrear el mecanismo de evolución.

### 3.10 Motores con controles reales: Cognee, Hindsight y OpenViking

**D.** Cognee aplica permisos por dataset y distingue lectura, escritura, borrado y compartición. Hindsight ofrece extensiones que fuerzan scopes de lectura/escritura en servidor, con tratamiento separado de hechos y evidencia. OpenViking documenta cuentas, usuarios y ACL de recursos; sus defaults requieren atención, porque las ACL no están activadas inicialmente. [Cognee](https://docs.cognee.ai/core-concepts/multi-user-mode/permissions-system/overview), [Hindsight](https://github.com/vectorize-io/hindsight/blob/main/hindsight-docs/docs/developer/extensions.md), [OpenViking](https://docs.openviking.ai/en/concepts/15-acl).

**I.** No sería justo reducir toda la competencia a filtros `user_id`. Estas bases ahorran implementación, aunque todavía hay que evaluar su composición con publicación, consentimiento y el modelo de amenaza de nuestro producto.

### 3.11 Caura: memoria gobernada y extracción desde sesiones de distintos harnesses

**D.** Caura, antes MemClaw, publica un motor Apache-2.0 separado del runtime, con interfaces MCP/REST, cliente Python, scopes de agente/equipo/organización, auditoría y consolidación. Distingue detección de datos personales de anonimización. [Repositorio](https://github.com/caura-ai/caura).

**D.** The Interviewer extrae recuerdos estructurados desde transcripciones existentes: documenta captura para OpenClaw, Claude Code y Cursor; Codex figura pendiente. La captura requiere opt-in; no verificamos una aprobación humana obligatoria de cada recuerdo antes de recuperarlo. [The Interviewer](https://caura.ai/docs/interviewer/).

**D.** Su guía distingue credenciales vinculadas a agentes en la plataforma administrada del despliegue self-hosted, que recibe un `agent_id` explícito y no ofrece la misma ruta de aprovisionamiento. También documenta correcciones que preservan linaje. Esto exige evaluar la frontera de confianza de cada despliegue, no atribuir automáticamente las garantías del servicio a la edición abierta. [Fleet Memory Guide](https://github.com/caura-ai/caura/blob/main/docs/agent-fleet-memory.md).

**I.** Es otro antecedente central contra una diferenciación basada solo en «memoria OSS gobernada, agnóstica y extraída de sesiones». Quedan por probar revisión de divulgación, identidad humana y retirada transitiva; no afirmamos que sean imposibles ni que nunca estén disponibles.

### 3.12 Buzz y SageOx: colaboración, identidades y memoria entre agentes

**D.** Buzz permite trabajar a humanos y agentes con identidades criptográficas distintas y acceso por comunidad/canal. Los relays no están federados y los mensajes/DM del servicio hospedado no tienen cifrado de extremo a extremo. Identidad firmada no significa por sí sola privacidad del contenido. [Soporte oficial](https://block.github.io/buzz/support.html).

**D.** El repositorio inicial corresponde a Buzz 0.X y remite a `buzz-app` para 1.0. La documentación de este último contempla Claude, Codex, goose y Pi, acceso externo con consentimiento revocable y exportación de definiciones sin memoria ni credenciales. No mezclamos capacidades entre versiones. [Repositorios](https://github.com/block/buzz), [agentes en 1.0](https://github.com/block/buzz-app/blob/main/docs/agents.md).

**P.** Caura publicó una investigación para combinar identidad de Buzz con memoria gobernada. Plantea exactamente problemas como promoción, procedencia y traducción de permisos/revocación. Aclara expresamente que la integración no está construida. Es un antecedente conceptual directo, no una alternativa integrada ya probada. [Buzz × Caura](https://caura.ai/blog/buzz-agents-get-an-identity/).

**D.** SageOx Agent Toolkit ofrece CLI, Slack/Buzz, runtimes ACP y memoria Markdown privada/compartida. Es MIT y pre-1.0; su integración de team brain usa el servicio SageOx, cuya apertura no se deduce de la licencia del toolkit. [Repositorio](https://github.com/sageox/agent-toolkit).

**D.** Su guía aclara que los scopes de participantes no sustituyen permisos del filesystem y que una herramienta de escritura autorizada no exige una segunda confirmación. No verificamos promoción editorial privada→equipo. [Memoria y herramientas](https://github.com/sageox/agent-toolkit/blob/main/docs/guide/memory-and-tools.md).

**I.** Estos proyectos refuerzan la necesidad de comparar el resultado completo: varias piezas de nuestra experiencia deseada ya conviven en software abierto, aunque sus fronteras de confianza y publicación sean diferentes.

## 4. Inventario comparativo ampliado

Las tablas son un mapa para decidir qué probar. «No verificado» refiere exclusivamente a esta revisión. Las características de Cloud/Enterprise no se atribuyen automáticamente a los repositorios abiertos.

### 4.1 Aprendizaje compartido y gobierno editorial

| Proyecto | Evidencia relevante | Límite o comparación pendiente |
| --- | --- | --- |
| [cq](https://github.com/mozilla-ai/cq) | CLI/MCP, unidades de conocimiento y revisión | Separar propuesta conceptual, OSS y namespaces del servicio |
| [Team Memory](https://github.com/team-memory/team-memory) | Jerarquía, revisión y promoción autorizada | PoC; no auditoría ni soporte productivo |
| [TeamAgentMemory](https://github.com/hsuanshao/TeamAgentMemory) | Capas privadas/compartidas; destilación y skills | Compartir derivados puede revelar datos aunque oculte transcript |
| [Agent Memory System](https://github.com/rrrrrredy/agent-memory-system) | Evidencia, validación, redacción y revisiones | Atestación local no autentica al aprobador |
| [TeamBrain](https://github.com/donatienmigue/TeamBrain) | Memoria por PR; MCP y redacción local | La frontera de distribución es principalmente el repositorio |
| [MEX](https://github.com/mex-memory/mex) | Conocimiento y handoffs revisables, Git | No confundir selección local de miembro con identidad autenticada |
| [Kindred / MoltSchool](https://github.com/p-vbordei/MoltSchool) | Playbooks firmados, grupos privados, procedencia y feedback | Modelo de confianza de grupos pequeños; revisar identidad humana detrás de firmas |
| [OPAL](https://github.com/omniharmonic/opal) | Conversaciones/documentos hacia un commons con revisión Git | Toolkit centrado en Claude; licencia y garantías operativas no verificadas |
| [Basic Memory](https://docs.basicmemory.com/teams/about) | Memoria compartida entre humanos y herramientas MCP; historial | Colaboración Cloud no equivale al programa local; escritura compartida no es promoción |
| [SkillClaw](https://github.com/AMAP-ML/SkillClaw) | Evolución colectiva y validación de skills | Grupo lógico no es autorización; modos direct/validated distintos |
| [Skiva](https://github.com/LingHeChen/skiva) | Releases de skills, snapshots, acceso y rollback | Distribución de capacidades, no extracción completa de conocimiento privado |

Kindred publica una revisión propia de autorización que distingue correcciones ya incorporadas de seguimiento pendiente. Sirve para aprender del diseño, no para declarar vulnerabilidades actuales sin reproducirlas. [Revisión del proyecto](https://github.com/p-vbordei/MoltSchool/blob/main/docs/superpowers/specs/2026-07-20-authorization-posture.md).

Basic Memory documenta roles y permisos de miembros: su uso compartido no es un simple directorio sin identidad. Tampoco se verificó que toda esa oferta Cloud esté incluida en el paquete local. [Roles](https://docs.basicmemory.com/teams/members-and-roles).

### 4.2 Harnesses, agentes de terminal y runtimes

| Proyecto | Solapamiento | Implicación para nosotros |
| --- | --- | --- |
| [Hermes](https://github.com/NousResearch/hermes-agent) | CLI, memoria, skills que evolucionan, proveedores | Referencia de UX personal y posible adapter |
| [OpenClaw](https://docs.openclaw.ai/concepts/agent-runtimes) | Canales, runtimes intercambiables, memoria y gobierno | Competidor integral; validar capacidades por runtime |
| [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) | Python, memoria, skills, herramientas y HITL | Candidato a motor sustituible; no decisión tomada |
| [LangGraph](https://docs.langchain.com/oss/python/concepts/memory) | Checkpoints, namespaces, stores y flujos | Biblioteca: identidad y política de negocio requieren aplicación |
| [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk) | Python, workspaces y confirmación de acciones | Separar SDK abierto de Enterprise comercial |
| [goose](https://github.com/aaif-goose/goose) | CLI/desktop, MCP, recetas y proveedores ACP | Buen segundo consumidor para demostrar interoperabilidad |
| [Pi](https://github.com/earendil-works/pi) | Harness mínimo, extensiones, skills y RPC | Integración atractiva; core TypeScript |
| [OpenCode](https://opencode.ai/docs/) | Terminal, modelos, skills y políticas de ejecución | Permiso de herramienta no equivale a permiso de divulgar conocimiento |
| [Aider](https://github.com/Aider-AI/aider) | Terminal, modelos y Git | Baseline de simplicidad para trabajo con código |
| [nanobot](https://github.com/HKUDS/nanobot) | Python, terminal, canales y memoria consolidada | Revisar versión estable y separación real de workspaces |
| [Claude Code](https://code.claude.com/docs/en/memory) | Auto memory e instrucciones por niveles | No competir suponiendo que carece de aprendizaje o conocimiento de equipo |
| [Codex](https://learn.chatgpt.com/docs/customization/memories) | Memoria local y reglas de equipo versionadas | Consumidor posible mediante superficies oficiales |
| [Buzz](https://github.com/block/buzz-app) | Colaboración humano/agente, identidades y varios harnesses | Separar releases, mensajes y memoria; no inferir E2E de identidad criptográfica |
| [SageOx Agent Toolkit](https://github.com/sageox/agent-toolkit) | CLI, canales, vaults y gateway de herramientas | Scopes locales no equivalen a auth; toolkit abierto ≠ backend compartido abierto |

Deep Agents documenta memoria por usuario, agente y organización, y recomienda controles y aprobación humana para escrituras compartidas. Por tanto, tampoco es nueva la receta de combinar ámbitos e intervención humana en Python. [Memoria de Deep Agents](https://docs.langchain.com/oss/python/deepagents/memory).

OpenHands tiene memoria de usuario/proyecto y un registro de secretos; no debe confundirse con las funciones de su backend Enterprise, distribuido bajo licencia comercial source-available. [Memoria](https://docs.openhands.dev/sdk/guides/persistent-memory), [Secret Registry](https://docs.openhands.dev/sdk/guides/secrets), [Enterprise](https://github.com/OpenHands/enterprise/blob/main/README.md).

### 4.3 Motores de memoria y contexto

| Proyecto / edición | Capacidad documentada | Matiz decisivo |
| --- | --- | --- |
| [Letta Code / Teams](https://docs.letta.com/teams/permissions) | Agentes/conversaciones privados, roles y memoria | Admin tiene visibilidad amplia; Cloud no equivale a local |
| [Cognee OSS](https://docs.cognee.ai/core-concepts/multi-user-mode/data-isolation-and-multi-tenancy) | Aislamiento de datasets, extracción y permisos | Granularidad del dataset no implica política de cada derivado |
| [OpenViking](https://docs.openviking.ai/en/concepts/11-multi-tenant) | Memoria, recursos y skills por cuenta/usuario | Configuración y defaults de ACL importan |
| [Hindsight OSS/Cloud](https://github.com/vectorize-io/hindsight) | Hechos, observaciones, modelos mentales y extensiones | Separar hooks configurables, producto Cloud y workflow humano |
| [Zep](https://help.getzep.com/v4/attribute-based-access-control) | ABAC sobre acciones, atributos y grafos | Funciones Enterprise y restricciones por tipo de grafo |
| [Graphiti OSS](https://github.com/getzep/graphiti) | Grafos temporales, evidencia e invalidación | El integrador construye tenancy, acceso y operación |
| [Honcho](https://honcho.dev/docs/v3/documentation/features/advanced/scopes) | Peers, sesiones y JWT con scope obligatorio | Scope con clave amplia es filtrado cooperativo; clave restringida es distinto |
| [Mem0](https://docs.mem0.ai/cookbooks/integrations/supabase) | Receta explícita de Company Brain personal/equipo/org | Es receta de aplicación, no garantía automática por usar IDs |
| [Supermemory](https://supermemory.ai/docs/recall/memory-review) | Memoria, inferencias y revisión approve/decline/undo | Inferencias pueden recuperarse antes de aprobarlas |
| [MemOS](https://memos-docs.openmem.net/open_source/modules/mos/users/) | MemCubes compartidos y roles | Binding entre auth HTTP y cada operación no auditado aquí |
| [memU](https://github.com/NevaMind-AI/memU) | Wiki personal y skills entre harnesses | Compartir entre agentes propios no equivale a compartir entre empleados |
| [MemMachine](https://github.com/MemMachine/MemMachine) | Episodios, perfiles y scopes org/proyecto/usuario | Enforcement asociado a identidad no verificado en esta revisión |
| [LangMem](https://github.com/langchain-ai/langmem) | Extracción de memoria y optimización de prompts | Primitivas reutilizables; no producto institucional completo |
| [Caura](https://github.com/caura-ai/caura) | Memoria de agentes/equipos, auditoría y extracción de sesiones | Distinguir credenciales de managed/self-hosted; revisión editorial no verificada |

Dos límites de edición especialmente importantes:

- Supermemory tiene repositorio público MIT, pero su documentación aclara que el servidor del motor local no está publicado allí; distingue binario lite y Enterprise. [Local versus Enterprise](https://supermemory.ai/docs/self-hosting/local-vs-enterprise).
- Revocar una API key de Hindsight Cloud es control de acceso; no equivale por sí mismo a retirar todos los conocimientos derivados de una fuente. [API keys](https://docs.hindsight.vectorize.io/cloud/api-keys/).

### 4.4 Plataformas organizacionales y gestión de conocimiento

| Producto | Solapamiento importante | Qué no debemos inferir |
| --- | --- | --- |
| [Onyx](https://docs.onyx.app/overview/onyx_anywhere/cli) | CLI/TUI, búsqueda empresarial y agentes | El CLI no prueba runtime autónomo ni paridad Community/Enterprise |
| [Glean](https://docs.glean.com/user-guide/assistant/team-chat) | Hilo privado y publicación selectiva en colaboración | Texto ya publicado al grupo puede seguir visible aunque falte acceso al original |
| [Microsoft Copilot / Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/configuration-end-user-authentication) | Identidad, conocimiento y canales corporativos | Autenticar al solicitante no resuelve toda divulgación a terceros |
| [Dust](https://docs.dust.tt/docs/user-documentation/agents/tools/agent-memory.md) | Memoria personal, espacios, skills y terminal | Aislar workspaces no demuestra aislamiento entre todos sus miembros |
| [Dify](https://docs.dify.ai/en/cloud/use-dify/monitor/annotation-reply) | Respuestas convertidas en anotaciones reutilizables | Corregir respuestas no equivale al ciclo completo de promoción |
| [RAGFlow](https://ragflow.io/docs/guides/team/resource_sharing/resource_sharing_and_permissions) | Recursos y memorias privadas/de equipo | Documentación DEV no garantiza disponibilidad en una release estable |
| [AnythingLLM](https://docs.anythingllm.com/features/security-and-access) | Multiusuario, workspaces y proveedores sustituibles | Memoria individual de workspace no pasa a ser memoria colectiva |
| [Atlassian Rovo](https://support.atlassian.com/rovo/docs/using-rovo-for-microsoft-teams/) | Elaboración privada y publicación al chat; páginas desde discusiones | Confirmación del solicitante no equivale a comprobación de cada receptor |
| [Guru](https://help.getguru.com/docs/setting-up-a-publishing-workflow) | Borradores, revisores y publicación editorial | Revisión editorial y permiso de divulgar la evidencia son distintos |
| [Slite](https://slite.com/help/WZXHFySavM6T0-/Enable-Self-Maintaining-Documentation) | Propone actualizaciones documentales al responsable | Las garantías de ACL dependen del conector |

Onyx documenta diferencias de ACL y sincronización entre ediciones; los permisos externos no deben suponerse instantáneos. [Access controls](https://docs.onyx.app/security/architecture/access_controls.md).

Guru tiene verificación de conocimiento, pero su guía editorial advierte que el borrador pendiente puede cambiar sin versionado entre solicitud y revisión. Dify ofrece intervención humana por email donde cualquiera con el enlace puede responder. Son elecciones de producto concretas, no equivalentes a una aprobación con identidad y contenido inmutables. [Guru](https://help.getguru.com/docs/setting-up-a-publishing-workflow), [Dify Human Input](https://docs.dify.ai/en/cloud/use-dify/nodes/human-input).

Microsoft documenta revisión en Channel Agent —public preview— y también limitaciones sobre permisos de toda la audiencia y determinadas protecciones. Hay que evaluar la superficie exacta, no asignar una garantía a toda la marca Copilot. [Channel Agent](https://learn.microsoft.com/en-us/microsoftteams/set-up-channel-agent-teams), [consideraciones Purview](https://learn.microsoft.com/en-us/purview/ai-m365-copilot-considerations).

## 5. Investigación académica y benchmarks

La evidencia académica importa por dos razones: evita atribuirnos conceptos existentes y ofrece escenarios para evaluar algo más que recuperación de texto. Un paper no equivale a un producto desplegable, y sus resultados no son una garantía sobre nuestro entorno.

| Trabajo | Antecedente o resultado relevante | Qué no demuestra |
| --- | --- | --- |
| [Collaborative Memory, 2025](https://arxiv.org/abs/2505.18279) | Memoria privada/compartida, procedencia y políticas dinámicas entre usuarios, agentes y recursos | Producto empresarial endurecido o ausencia absoluta de filtraciones |
| [AIM / MUMBench, septiembre 2026](https://arxiv.org/abs/2609.12320) | Marco interoperable multiusuario y evaluación de crear, consultar, actualizar y borrar | Que clasificación automática privado/público sea suficiente para autorizar difusión |
| [MixUA / CrossLearnBench, noviembre 2026](https://arxiv.org/abs/2611.10439) | Lecciones con ámbitos usuario, agente, pareja y global; pruebas de privacidad | Gobierno humano completo o soporte de toda jerarquía organizacional |
| [Org-Agent, septiembre 2026](https://arxiv.org/abs/2609.34392) | Identidad, autoridad, permisos, vigencia y decisiones multiusuario como restricciones | Un CLI/framework productivo equivalente a toda la visión |
| [GroupMemBench, mayo 2026](https://arxiv.org/abs/2605.14498) | Memoria de grupos, atribución, actualización, ambigüedad y abstención | Rendimiento universal de los productos actuales |
| [Multi-User LLM Agents / MUSES, revisión noviembre 2026](https://arxiv.org/abs/2604.08567) | Conflictos de objetivos, privacidad y coordinación entre principales | Que el modelo pueda sustituir autorización determinista |
| [FederatedSkill, junio 2026](https://arxiv.org/abs/2606.03143) | Intercambio de cambios de skills en lugar de trayectorias completas | Que un patch no pueda contener información sensible |
| [FedSkillGit, octubre 2026](https://arxiv.org/abs/2610.21348) | Parches, filtros de privacidad y validación distribuida antes de publicar | Seguridad fuera de las condiciones experimentales |
| [GroupAssistBench, noviembre 2026](https://arxiv.org/abs/2611.04867) | Diferencia entre recordar y ayudar usando recuerdos distribuidos o contradictorios | Que mejorar recall por sí solo produzca valor para un equipo |

### Tres aprendizajes especialmente relevantes

**La procedencia con permisos dinámicos no es una idea nueva.** Collaborative Memory ya lo formulaba en 2025. Sus propias limitaciones reconocen escenarios controlados, escala moderada y riesgos asociados al comportamiento probabilístico. [Texto y limitaciones](https://arxiv.org/html/2505.18279v1).

**Los ámbitos de grupos siguen siendo difíciles incluso en propuestas muy recientes.** MixUA reconoce que su modelo de uno/todos no expresa adecuadamente equipos intermedios; también indica que consentimiento, inspección y retirada necesitan más evaluación. Esto es un hueco explícito de ese trabajo, no prueba de un hueco en todo el mercado. [Limitaciones de MixUA](https://arxiv.org/html/2611.10439v1).

**No deberíamos medir solamente cuántos recuerdos encuentra el sistema.** Necesitamos medir si la siguiente persona resuelve mejor su tarea, si atribuye correctamente cada afirmación, si detecta cambios y si respeta permisos. La utilidad y la privacidad deben evaluarse juntas; no se compensan con un único promedio.

## 6. Protocolos y piezas que conviene reutilizar

### 6.1 Open Memory Protocol Initiative: no empezar inventando otro estándar

**D/P.** OMPI está alojada en AI Disclosures Project y co-convocada con IBM y Mozilla. Trabaja hacia una primera versión; no demuestra una implementación de referencia completa de todas sus garantías. Hay prototipos parciales, como COGX, que su propuesta denomina workbench/reference implementation. El borrador editorial v0.5 fue incorporado el 6 de noviembre de 2026. [Repositorio y estado](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol), [iniciativa](https://ai-disclosures.org/ompi), [alcance del prototipo Cognee](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/blob/main/early-draft-specs/draft-v0.1-cognee.md).

**P.** El borrador distingue metadatos, cuerpo, origen, revisión, procedencia, evidencia, ámbitos e intercambio. Deja aspectos abiertos y no impone algoritmos ni almacenamiento. Tampoco implementa el enforcement de políticas, el aislamiento de recuperación ni la mecánica de olvido: esas responsabilidades siguen en los sistemas participantes. Su existencia contradice la idea de que nadie esté definiendo un contrato portable con esas preocupaciones. [Borrador v0.5](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/blob/main/working-group/exchange-and-runtime/2026-11-06-working-spec-v0.5.md).

**P.** La contribución de Cognee ya propone rechazo o staging restringido cuando no puedan trasladarse identidades/reglas, tratamiento de tombstones y separación entre permiso para conocer y permiso para actuar. Declara expresamente que muchas garantías propuestas todavía no están implementadas. [Propuesta de Cognee](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/blob/main/early-draft-specs/draft-v0.1-cognee.md).

**I.** Una contribución posible sería implementar y probar un perfil concreto para promoción organizacional sobre esas ideas. No llamarlo estándar nuevo ni compatibilidad certificada. Primero hay que demostrar que una extensión es necesaria y mantener el adapter versionado ante cambios del borrador.

Hay proyectos distintos con nombres parecidos a «Open Memory Protocol». Este informe se refiere específicamente a la iniciativa de AI Disclosures Project; no atribuye a esa iniciativa las promesas de sitios homónimos.

### 6.2 Formatos y protocolos complementarios

| Pieza | Qué resuelve | Qué queda fuera de esa garantía |
| --- | --- | --- |
| [MCP](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) | Acceso interoperable a herramientas/recursos; autorización HTTP | El modelo editorial y la legitimidad de divulgar un derivado |
| [ACP](https://github.com/agentclientprotocol/agent-client-protocol) | Conexión entre clientes/editores y agentes | Equivalencia de memoria, políticas y capacidades entre runtimes |
| [Agent Skills](https://agentskills.io/specification) | Formato portable de instrucciones y recursos | Seguridad del código, autenticidad o autoridad institucional |
| [COGX](https://docs.cognee.ai/core-concepts/further-concepts/cogx) | Importación/exportación de memoria entre formatos | Preservación demostrada de toda política entre cualquier par de motores |

COGX ya transporta tipos, scopes y metadatos de origen; desde 0.2 admite cabeceras opcionales relacionadas con OMP. Por tanto, tampoco «tener formato de exportación» constituye diferenciación suficiente. Campo opcional significa información potencialmente ausente; no debe reconstruirse por conjetura. [Formato COGX](https://docs.cognee.ai/core-concepts/further-concepts/cogx).

### 6.3 Identidad, permisos y conexiones

| Componente | Uso potencial | Responsabilidad que sigue siendo nuestra |
| --- | --- | --- |
| [OpenFGA](https://openfga.dev/docs/modeling/parent-child) | Relaciones de usuario, grupo, proyecto y objeto | Modelo de acciones, sincronización y enforcement en cada operación |
| [SpiceDB](https://authzed.com/docs/spicedb/concepts/consistency) | Autorización con revisiones/consistencia causal | Propagar cambios a caches, publicaciones y trabajos pendientes |
| [Nango](https://nango.dev/docs/guides/auth/auth-guide) | Conectar cuentas, custodiar y renovar credenciales | Asociar conexión a identidad legítima y autorizar su uso |
| [Composio](https://docs.composio.dev/docs/authentication) | Herramientas y cuentas conectadas por usuario | Autorización del documento devuelto y de su eventual publicación |

No necesitamos construir cuatro sistemas completos de infraestructura para probar una lección compartida. La elección de componentes depende del alcance, operación y licencia; no está resuelta por esta investigación.

### 6.4 Licencias: evitar equivalencias falsas

Esto identifica licencias declaradas de componentes concretos; no es un dictamen de compatibilidad jurídica ni una auditoría de dependencias.

- `cq` y Team Memory: Apache-2.0. [cq LICENSE](https://github.com/mozilla-ai/cq/blob/main/LICENSE), [Team Memory LICENSE](https://github.com/team-memory/team-memory/blob/main/LICENSE).
- Agent Memory System: MIT. [LICENSE](https://github.com/rrrrrredy/agent-memory-system/blob/main/LICENSE).
- Letta Code: Apache-2.0; eso no convierte toda función Cloud en autohospedable. [LICENSE](https://github.com/letta-ai/letta-code/blob/main/LICENSE).
- Cognee: Apache-2.0; Hindsight: MIT. [Cognee](https://github.com/topoteretes/cognee/blob/main/LICENSE), [Hindsight](https://github.com/vectorize-io/hindsight/blob/main/LICENSE).
- OpenViking y Honcho: AGPLv3 en los archivos consultados. [OpenViking](https://github.com/volcengine/OpenViking/blob/main/LICENSE), [Honcho](https://github.com/plastic-labs/honcho/blob/main/LICENSE).
- Onyx distingue código MIT y directorios Enterprise. Dify utiliza una licencia modificada, no Apache-2.0 sin condiciones adicionales. [Onyx](https://github.com/onyx-dot-app/onyx/blob/main/LICENSE), [Dify](https://github.com/langgenius/dify/blob/main/LICENSE).
- Nango declara Elastic License 2.0; repositorio público no equivale a licencia permisiva. [LICENSE](https://github.com/NangoHQ/nango/blob/master/LICENSE).

Antes de adoptar o redistribuir código: fijar versión, revisar licencia del paquete exacto, dependencias, plugins, assets y modalidad de uso. No se decidió la licencia de nuestro proyecto.

## 7. Qué existe, qué no verificamos y qué no debemos prometer

### 7.1 Lo que ya existe y no usaría como afirmación de originalidad

- Agente de terminal en Python o con varios modelos.
- Memoria persistente entre sesiones.
- Memoria personal, de equipo y organizacional.
- Aprendizaje de experiencias sin modificar pesos del modelo.
- Generación y mejora de skills desde conversaciones.
- Revisión humana antes de publicar conocimiento.
- Aprobación ligada a versión y promoción entre ámbitos.
- Procedencia, invalidación y determinados tipos de retirada de memoria.
- Acceso a herramientas con credenciales por usuario.
- Integraciones con múltiples canales y harnesses.
- Exportación de memoria y propuestas de protocolos abiertos.

Las secciones 3–6 aportan antecedentes para todos esos puntos. Algunos existen en productos comerciales, otros en OSS, otros como investigación o borradores; no se afirma que una sola alternativa los entregue todos con idénticas garantías.

### 7.2 Lo que no quedó establecido como solución integrada y probada

En la evidencia revisada **no quedó demostrada una alternativa que reúna y verifique todo nuestro recorrido**, simultáneamente, con:

1. CLI útil y sencillo para trabajo diario de personas distintas.
2. Recopilación privada con consentimiento y minimización configurables.
3. Candidatos sanitizados, con fuentes que no se revelan a revisores no autorizados.
4. Permisos separados para leer, aprender, proponer, verificar, publicar y ejecutar.
5. Revisión de una versión y audiencia exactas, incluyendo cambios concurrentes.
6. Consumo desde más de un harness sin eludir la política.
7. Corrección y revocación de los derivados gestionados, con límites declarados.
8. Cambio de backend que preserve las propiedades anteriores.
9. Evidencia independiente de utilidad y seguridad en un equipo real.

Esto es una **brecha de verificación y de composición**, no una demostración de inexistencia ni una lista de invenciones. Team Memory ya cubre una parte sustancial del gobierno; OpenClaw cubre autoridad/retirada; OMPI propone parte del contrato. Una evaluación práctica podría reducir todavía más el espacio para un producto nuevo.

### 7.3 Promesas que serían incorrectas también en nuestro producto

**«Privado» sin aclarar frente a quién.** Puede significar privado ante compañeros, administradores, operador, proveedor de modelos o todos ellos. Son amenazas diferentes.

**«Anonimizado» porque quitamos nombres.** Una descripción puede reidentificar por detalles, relaciones o contexto. Un detector de secretos reduce accidentes; no prueba ausencia de información sensible.

**«Revocación total» tras entregar el contenido.** Podemos bloquear futuras lecturas y gestionar copias bajo nuestro control. No hacer olvidar a un humano ni recuperar toda copia externa.

**«Model-agnostic» como equivalencia de resultados.** Poder cambiar proveedor no garantiza igual calidad de extracción, límites de contexto o uso de herramientas.

**«Storage-agnostic» porque hay una interfaz.** Concurrencia, transacciones, filtrado, búsquedas y consistencia de revocación necesitan pruebas por backend.

**«Agent-harness-agnostic» porque exportamos Markdown.** Si el otro harness puede copiarlo, ignorar sus límites o ejecutar una skill sin controles, la política no es portable.

**«Aprende solo y de forma segura».** Aprobación automática exige un dominio y riesgos acotados; un modelo que valida su propia inferencia no constituye evidencia independiente.

## 8. Dónde podría aportar valor el proyecto

Esta sección contiene hipótesis propias a validar, no afirmaciones de ausencia de competencia.

### 8.1 Resultado deseado, expresado sin vender infraestructura

> Cuando una persona descubre cómo resolver un problema, la siguiente puede aprovecharlo desde su agente habitual, sin releer toda la conversación ni recibir información que no debe conocer.

Ese resultado es más importante que tener más adapters o una base vectorial distinta.

### 8.2 Cinco posibles aportes

| Aporte potencial | Ejemplo concreto | Cómo demostrarlo |
| --- | --- | --- |
| Menos trabajo repetido | Un error resuelto por Ana no exige la misma investigación a Bruno | Tiempo, intentos y calidad frente a la alternativa existente |
| Compartición comprensible | Ana ve exactamente qué texto se publicará, a quién y desde qué evidencia | Errores de publicación y tiempo de revisión |
| Gobierno portable | El mismo aprendizaje se usa desde nuestro CLI y otro harness | Misma suite de denegaciones y lifecycle en ambos |
| Mantenimiento confiable | Una corrección marca qué guía y skill quedaron obsoletas | Cobertura y latencia de invalidación/revalidación |
| Adopción accesible | Un equipo pequeño prueba el flujo sin plataforma empresarial completa | Tiempo de instalación, dependencias y carga operativa |

Ninguno de estos aportes requiere ser una invención para ser valioso. Sí requiere una mejora observable frente a algo que la gente ya puede usar.

### 8.3 Usuario inicial recomendado

**I.** Un equipo técnico pequeño que ya usa agentes de terminal, comparte trabajo y redescubre convenciones o soluciones. No necesariamente una empresa: puede ser un proyecto open source, colaboradores independientes o un equipo personal de prueba.

Es un primer segmento coherente con el CLI elegido. Ofrece tareas observables y alternativas sencillas contra las que comparar: documentación versionada, PRs, cq, TeamBrain o Team Memory. No es una afirmación de tamaño de mercado ni demanda validada.

No empezaría por «toda la inteligencia de una organización». Eso mezcla onboarding, soporte, ventas, ingeniería, cumplimiento y conocimiento tácito con expectativas muy distintas.

### 8.4 La oportunidad más defendible hoy

**Una experiencia CLI para convertir experiencia privada en aprendizajes y procedimientos compartidos de forma controlada, compatible con herramientas existentes y acompañada de pruebas públicas de sus límites.**

El énfasis sería experiencia, integración y evidencia. No «primer framework multiusuario», «primer sistema con memoria gobernada» o «primer protocolo de conocimiento».

## 9. Diferencia frente a RAG, memoria y un coding agent

### RAG

RAG describe recuperar información para ayudar a generar una respuesta. No implica ausencia de ACL, citas, actualización o verificación. Onyx y Glean muestran por qué compararnos con un RAG ingenuo sería un contraste artificial. [Onyx ACL](https://docs.onyx.app/security/architecture/access_controls.md), [Glean access](https://docs.glean.com/user-guide/assistant/how-glean-accesses-info).

Nuestro flujo **podría usar RAG internamente**. El posible aporte estaría antes y después de recuperar: qué se convirtió en conocimiento autorizado, quién responde por ello, cuándo debe dejar de utilizarse y si realmente mejora la tarea.

### Memoria simple

Una lista de notas personales no resuelve por sí sola colaboración, pero tampoco representa toda la competencia. Los motores examinados ya contienen consolidación, temporalidad, feedback, scopes y controles.

La diferencia útil no sería «guardamos más memoria», sino «reutilizamos el aprendizaje correcto, para la persona y audiencia correctas, con un ciclo de mantenimiento manejable».

### Un coding agent como Claude Code o Codex

Resuelve trabajo individual y aporta memoria, instrucciones y herramientas. Nuestro producto solo justificaría añadirse si mejora la transmisión de conocimiento entre personas o proyectos sin exigir abandonar el agente habitual. No necesitamos superar su capacidad general de programar para probar esa hipótesis.

Esto también resuelve la aparente tensión entre CLI propio y harness-agnostic: el CLI puede ser una experiencia completa de referencia; la memoria compartida y su gobierno no deberían quedar inseparables de ese único cliente.

## 10. Credenciales y privacidad: implicaciones

La investigación refuerza la separación ya propuesta en [Identidad y credenciales](../credentials.md). Se necesitan cuatro conceptos diferentes:

| Concepto | Pregunta que responde | Ejemplo conceptual |
| --- | --- | --- |
| Identidad de persona | ¿Quién está operando? | Sesión autenticada de Ana |
| Pertenencia y permisos | ¿Qué puede hacer aquí? | Lector del proyecto; publicador del equipo |
| Conexión a herramienta | ¿Con qué autoridad accede al sistema externo? | Cuenta personal autorizada de GitHub |
| Credencial del modelo | ¿Quién puede invocar y pagar inferencia? | API key propia o presupuesto compartido |

Conectar una cuenta no debe copiar sus tokens a la memoria. Compartir una skill tampoco debe compartir las credenciales de quien la creó. El receptor ejecuta herramientas con su propia conexión o con una cuenta de servicio autorizada para esa acción.

Nango y Composio ya cubren parte de la custodia y renovación. MCP documenta separación entre el token de acceso al servidor y credenciales de APIs externas; no conviene improvisar token passthrough. [Nango](https://nango.dev/docs/guides/auth/auth-guide), [Composio](https://docs.composio.dev/docs/authentication), [seguridad de autorización MCP](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices).

Para el diseño propuesto:

- El servicio deriva identidad y conexiones permitidas desde credenciales verificadas, no desde un `user_id` que el modelo inventa.
- Leer una fuente no concede automáticamente permiso para retenerla, procesarla en background o publicar su resumen.
- El dueño de una conversación no necesariamente tiene autoridad sobre datos de terceros presentes allí.
- La revisión de exactitud puede corresponder a una persona y la aprobación de divulgación a otra.
- La audiencia de un canal incluye más que el usuario que pregunta: integrantes, invitados, bots y sistemas que conservan mensajes.
- Un aprobador sin acceso a la fuente puede revisar el texto propuesto, pero no debe recibir evidencia privada para «ayudarlo» a aprobar.
- Las sesiones de revisión necesitan una autoridad distinta de las llamadas autónomas del agente. Una pregunta en terminal no demuestra por sí sola que respondió un humano.

Estas son reglas de diseño pendientes de implementar. La investigación no configura credenciales ni elige un proveedor de identidad.

## 11. Construir, extender o integrar

| Opción | Ventaja | Costo/riesgo | Evaluación actual |
| --- | --- | --- | --- |
| Crear todo el harness, memoria, auth y conectores | Máximo control | Mucha infraestructura antes de probar valor; duplicación alta | No recomendado como primer paso |
| CLI propio pequeño + módulos reutilizados | Respeta la experiencia buscada y concentra esfuerzo | Integración y fronteras deben diseñarse con cuidado | Recomendación provisional |
| Extender cq, Team Memory u otro proyecto | Aporta sobre un antecedente cercano | Dependencia de arquitectura y decisiones ajenas | Alternativa seria; probar antes de descartarla |
| Producto encima de un servicio existente | Validación rápida de utilidad | Menor soberanía y dependencia comercial | Útil como baseline, no necesariamente destino |
| Solo protocolo o SDK | Alcance técnico claro | Difícil demostrar utilidad; OMPI ya trabaja ese espacio | No como apuesta inicial aislada |

La recomendación de CLI pequeño no significa un comando decorativo delante de una API. Puede tener sesión interactiva, herramientas y memoria privada. Significa no reconstruir de entrada todos los motores, conectores, sistemas de identidad y algoritmos de memoria.

Deep Agents u OpenHands SDK podrían servir de motor Python; Cognee, Hindsight u otra base podrían servir de memoria. **No se seleccionó ninguno.** El primer paso sería comprobar qué parte de nuestro flujo existe y cuánto cuesta extenderla.

Tampoco se recomienda adoptar un proyecto pequeño únicamente por cercanía conceptual: mantenimiento, seguridad, licencia, migraciones y facilidad para contribuir deben evaluarse antes.

## 12. Validación antes de desarrollar demasiado

### 12.1 Comparación mínima recomendada

Usar el mismo escenario y datos sintéticos contra:

1. **Baseline manual:** documentación Markdown con PR y acceso por repositorio.
2. **cq o TeamBrain:** aprendizaje compartido con baja fricción.
3. **Team Memory:** revisión y promoción con autorización explícita.
4. **OpenClaw Knowledge:** ámbito de audiencia y memoria con procedencia.
5. **Dust**, si se decide probar un servicio: aprendizaje de skills desde uso real.
6. **Nuestro prototipo**, solamente después de identificar un fallo o costo relevante que mejore.

Letta, TeamAgentMemory, Caura y un motor Python quedan como segundo grupo según el tipo de recorrido. Buzz/SageOx son comparadores relevantes si priorizamos colaboración en canales además de la terminal. No hace falta instalar todos para avanzar: primero seleccionar dos o tres comparadores fuertes, fijar versiones y registrar qué configuración adicional necesita cada uno.

### 12.2 Escenario de referencia

Ana y Bruno pertenecen al proyecto A. Carla pertenece al proyecto B. Diego puede verificar procedimientos, pero no publicar información de cierta fuente. Ana trabaja en una conversación privada usando una fuente restringida y descubre una solución reutilizable.

El material contiene deliberadamente una clave falsa, un nombre de cliente ficticio y un detalle que permitiría reidentificar el caso. La lección útil puede expresarse sin esos datos. La prueba recorre captura, candidato, revisión, publicación, consulta desde otro harness y retirada.

No se deben usar credenciales reales, conversaciones laborales ni datos de clientes para esta evaluación.

### 12.3 Suite de aceptación propuesta

| ID | Prueba | Resultado exigido |
| --- | --- | --- |
| A1 | Bruno solicita transcript privado de Ana | Denegado sin revelar contenido, títulos o referencias restringidas |
| A2 | Un candidato aún no publicado coincide con una búsqueda | No aparece en contexto compartido; revisores solo según su permiso |
| A3 | El LLM llama a la operación de aprobar | No adquiere la autoridad de revisión por declarar `human=true` |
| A4 | El candidato cambia después de revisado | La aprobación anterior no autoriza la nueva versión |
| A5 | Cambia la audiencia después de revisar | Revalidación antes de ampliar difusión |
| A6 | Diego verifica exactitud pero no puede divulgar la fuente | No puede completar la publicación por ese solo rol |
| A7 | Carla adivina IDs, busca términos o consulta historial | No obtiene datos del proyecto A ni metadatos restringidos |
| A8 | Ana pregunta en un canal con un invitado no autorizado | La respuesta no traslada automáticamente su acceso privado |
| A9 | Se elimina una pertenencia durante una consulta | Comprobación antes de la entrega; medir ventana real de revocación |
| A10 | Se corrige una fuente con memorias y skills dependientes | Identifica descendientes gestionados; bloquea o revalida según política |
| A11 | Se importa un export antiguo con una memoria retirada | No resucita silenciosamente contenido revocado |
| A12 | Se cambia de harness o backend | Conserva restricciones soportadas; rechaza o aísla pérdida de semántica |
| A13 | Un tercero propone una skill con instrucciones maliciosas | No gana autoridad por estar en memoria; revisión y ejecución separadas |
| A14 | Varias sesiones repiten la misma afirmación sin nueva evidencia | No se convierten automáticamente en confirmaciones independientes |
| A15 | La lección ya fue entregada y después se retira | Reporta futuros bloqueos y límites de recuperación; no promete borrado universal |
| A16 | Se aprueba una lección válida y autorizada | El segundo usuario la recibe y resuelve la tarea: controles positivos, no solo denegaciones |

No se afirma que los competidores fallen estas pruebas. Son el instrumento para averiguarlo. Algunas requerirán configuración o una extensión; registrar ese esfuerzo es parte de la comparación.

### 12.4 Política de revocación: una decisión que no debe ocultarse

Revocar acceso a una fuente, retirar consentimiento de procesamiento y retractar una afirmación son eventos diferentes. Una lección publicada puede seguir autorizada por una aprobación independiente, o requerir cuarentena si depende necesariamente del origen retirado.

El producto debe declarar esa semántica. «Borrar todos los descendientes siempre» puede eliminar conocimiento legítimo; «conservar todo porque ya fue resumido» puede divulgar información indebidamente. La elección depende del tipo de contenido y de quién tenía autoridad para publicarlo.

### 12.5 Métricas de valor

- Tiempo e intentos para que otra persona resuelva una tarea similar.
- Calidad del resultado frente a no usar memoria y frente a documentación manual.
- Tiempo humano de revisión por aprendizaje realmente reutilizado.
- Propuestas descartadas, duplicadas, incorrectas u obsoletas.
- Errores de atribución y conflictos no detectados.
- Divulgaciones no autorizadas y falsos bloqueos, por escenario.
- Latencia de revocación y porcentaje de derivados rastreables.
- Costo de extracción, mantenimiento y recuperación.
- Tiempo de configuración y carga de operación del servicio.
- Uso voluntario sostenido: si el equipo deja de revisar, el diseño no funciona aunque la demo sí.

No usar solamente «cantidad de memorias creadas» o «tokens ahorrados». Más recuerdos pueden producir más ruido y más riesgo.

### 12.6 Criterio para continuar o cambiar de dirección

Continuar si un recorrido frecuente mejora claramente en utilidad y control, y las personas aceptan el costo de revisión. Extender una alternativa si logra lo mismo con poca configuración. Reducir alcance si la gobernanza resulta demasiado costosa para el beneficio. No fijar porcentajes comerciales o plazos de retorno antes de medir una línea base.

## 13. Riesgos y defensibilidad

### Riesgos de producto

**No hay demanda validada todavía.** La existencia de muchos proyectos prueba interés y competencia, no que alguien vaya a adoptar el nuestro.

**Sobrecarga editorial.** Una bandeja con cientos de propuestas transforma aprendizaje automático en trabajo manual. Hay que priorizar candidatos por utilidad, deduplicar y permitir políticas según riesgo.

**Problema de arranque.** Sin conocimiento útil, nadie vuelve; sin uso, no aparece conocimiento. Importar documentación aprobada puede ayudar, pero no reemplaza validar el ciclo de aprendizaje.

**Percepción de vigilancia.** Aprender de interacciones privadas de empleados puede ser valioso o invasivo. Opt-in, transparencia y controles individuales son parte del producto, no solo textos de privacidad.

**Cambio de hábitos.** Pedir que todos abandonen su harness aumenta mucho la fricción. Interoperabilidad como experiencia real puede importar más que tener más funcionalidades propias.

### Riesgos técnicos

- Inyección de instrucciones a través de fuentes o memoria compartida.
- Confundir procedencia con veracidad: una cita demuestra origen, no exactitud.
- Credenciales o datos personales dentro de resúmenes y skills.
- Pérdida de permisos al exportar/importar.
- Caches, colas, procesos en background y sesiones abiertas que conservan autorización vieja.
- Conflictos entre políticas de equipos y conocimiento de alcance más amplio.
- Cambios de API y canales; una integración no mantiene automáticamente sus garantías.
- Pruebas sintéticas que no reflejan inferencias o relaciones entre personas reales.
- Proliferación de abstracciones antes de tener una segunda implementación que las justifique.

### Qué podría construir una ventaja sostenible

**I.** La ventaja más plausible no es un algoritmo secreto de memoria. Sería una combinación de buena experiencia, integraciones mantenidas, corpus de evaluación, confianza operativa, comunidad y un modelo claro de responsabilidades.

Publicar pruebas de interoperabilidad, escenarios de ataque y límites explícitos puede generar confianza. Pero esa ventaja requiere trabajo sostenido y se puede erosionar si un proyecto existente adopta las mismas mejoras.

Para un proyecto personal open source también existe valor sin una categoría comercial nueva: aprender, aportar una implementación excelente, resolver una necesidad propia y contribuir estándares o pruebas. Conviene distinguir ese objetivo de construir un negocio defendible.

## 14. Impacto sobre nuestra documentación y decisiones pendientes

La investigación **no reemplaza automáticamente** la [visión original](../vision.md). La conserva como intención y agrega evidencia para acotar implementación y posicionamiento. Tampoco cambia las decisiones confirmadas: proyecto personal, Python para lo agéntico, experiencia de terminal y documentación primero.

Antes de publicar el posicionamiento, recomendaría:

1. Quitar cualquier insinuación de ser el primero en memoria organizacional o aprendizaje multiusuario.
2. Reconocer antecedentes cercanos y explicar exactamente qué flujo queremos mejorar.
3. Definir «privado», «aprobado», «promovido», «revocado» y «agnóstico» con criterios comprobables.
4. Separar el harness de referencia del dominio de conocimiento y sus políticas.
5. Usar estándares/adapters existentes donde alcancen; no declarar un protocolo nuevo antes de probar necesidad.
6. Mantener el MVP fuera de datos laborales y con ejemplos sintéticos.

### Decisión recomendada para conversar con el autor

**¿Queremos que el primer aporte sea mejorar cómo un equipo transmite aprendizajes entre sus agentes, con un CLI propio como experiencia principal?**

Si la respuesta es sí, el siguiente documento debería describir un único recorrido y dos o tres alternativas contra las que medirlo. Si el interés principal es construir un agente personal completo, sigue siendo un proyecto válido, pero la diferenciación y el alcance serían otros.

Después vendrían decisiones sobre base reutilizada, modo local/servidor, identidad compartida y primera herramienta conectada. Nombre, licencia, publicación remota y proveedores siguen pendientes; este informe no los decide.

## 15. Trazabilidad de la inspección y límites

### Inspección estática más profunda

| Repositorio | Revisión consultada | Material relevante |
| --- | --- | --- |
| mozilla-ai/cq | `2e538ec61b3f136d8aca6dd95db522118dda64eb` | Auth/dependencias, rutas/servicio de revisión, schema, propuesta y docs |
| team-memory/team-memory | `6a537166b7cff7b5198d86f0c1167df0dc34b836` | Promoción, portal, modelo de amenazas y límites |
| rrrrrredy/agent-memory-system | `df99a112b61e5f304c26ac66c5fade8f7131f7e1` | Contrato, promoción, revisión y licencia |
| p-vbordei/MoltSchool | `9bbf5519fc2a02953cf746131c52e45f7640fe0a` | README y revisión de postura de autorización |

Los commits se resolvieron mediante la API pública de GitHub durante la consulta. Las demás referencias apuntan principalmente a documentación viva o ramas principales. Se debe fijar la versión exacta del paquete antes de una prueba reproducible.

### Lo que no se hizo

- Auditoría exhaustiva de seguridad de ningún repositorio.
- Ejecución de suites, benchmarks, migraciones o pruebas adversariales.
- Verificación contractual de todas las ediciones comerciales.
- Análisis exhaustivo de patentes o dictamen de novedad jurídica.
- Entrevistas, medición de disposición a pagar o validación de mercado.
- Comprobación de todos los plugins y proyectos no indexados.
- Demostración de que una ausencia documental es una ausencia real.

La búsqueda es amplia y profunda en los antecedentes más cercanos, pero no puede demostrar una inexistencia universal. El resultado útil es una decisión mejor informada: **el concepto tiene precedentes claros; el valor propio debe ganarse con una mejora concreta y medible.**
