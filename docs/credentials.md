# Credenciales e identidad por persona en el CLI

Estado: propuesta de arquitectura. Los comandos son ilustrativos y todavía no existen. La experiencia inicial será terminal y el núcleo agéntico se construirá en Python.

Actualización del primer corte: existen el servicio y el CLI con tokens explícitos de desarrollo, y el autor eligió API personal de OpenAI. La configuración ejecutable se explica en [Desarrollo](development.md). OIDC, OAuth y los comandos de configuración de este documento siguen propuestos; la implementación actual no los simula como login productivo.

El primer producto vincula el CLI a un servicio y espacio compartidos. El autor descartó el modo personal autónomo con colaboración opcional; la ubicación de ejecución y custodia se concretará para ese recorrido. Véase [0004](decisions/0004-colaboracion-como-nucleo-del-producto.md).

## 1. Qué necesita configurar una persona

La configuración tiene cuatro partes independientes:

| Parte | Ejemplo | Quién la configura | Dónde se utiliza |
|---|---|---|---|
| Configuración del cliente | Directorio y preferencias | La persona | En su CLI; no acredita identidad ni permisos |
| Identidad compartida | Cuenta y membresía en un espacio | La persona inicia sesión; el servicio valida membresías | En las operaciones compartidas |
| Conexiones personales | Autorización para una cuenta externa | Cada persona autoriza su cuenta | En herramientas que actúan en su nombre |
| Acceso al modelo | Clave API personal, endpoint o gateway autorizado | Persona o administrador de instalación | En las solicitudes de inferencia |

Una clave del modelo permite consumir ese servicio; no concede acceso al conocimiento de otras personas. Un login a la instalación del framework tampoco autoriza automáticamente cuentas externas.

## 2. Recorrido propuesto para una persona

Primero inicia sesión en el servicio y accede a un espacio autorizado:

```text
oif login --server <url>
oif spaces list
```

El servidor verifica la identidad y decide qué espacios y artefactos puede usar la persona. Esa sesión es distinta de la autorización de herramientas y del acceso al modelo.

El acceso al modelo se configura según la modalidad que se elija. Si requiere una credencial personal, el flujo propuesto es:

```text
oif model configure
```

El asistente permite seleccionar proveedor y modelo según la política acordada. Si hace falta una API key, la recibe mediante entrada oculta y la guarda en el almacén de secretos elegido; no se introduce como argumento del comando. La ubicación de custodia depende de dónde se invoque al proveedor, aún pendiente de decisión.

Después puede autorizar una herramienta cuando la tarea lo requiera:

```text
oif connect <provider>
oif auth status
```

El CLI abre el navegador para completar el permiso con el proveedor cuando ese flujo esté soportado. Al terminar muestra la cuenta, las operaciones concedidas y el estado de conexión. La contraseña de la cuenta no pasa por el agente.

## 3. Login y vinculación de identidades

Para una instalación compartida se propone OIDC. Las cuentas externas se identifican por emisor y sujeto estable; nombre o correo no bastan para unir automáticamente identidades. El servicio mantiene una identidad interna y sus membresías. [OpenID Connect Core, estabilidad de claims](https://openid.net/specs/openid-connect-core-1_0.html#ClaimStability).

Vincular posteriormente una cuenta de Slack, Teams u otro canal requiere prueba de control dentro de una sesión autenticada. Un número de teléfono, una dirección de correo o un argumento de la CLI nunca se aceptan como prueba suficiente de identidad.

Un perfil del cliente organiza preferencias; no sustituye la identidad verificada por el servicio. Dos perfiles bajo la misma cuenta del sistema operativo no constituyen una frontera de seguridad fuerte entre personas.

## 4. OAuth en terminal

Se propone Authorization Code con PKCE mediante el navegador del sistema y callback de loopback cuando el proveedor lo permita. Una CLI distribuida se trata como cliente público: no puede custodiar un secreto de aplicación común incluido en el paquete como si fuera confidencial. [OAuth para aplicaciones nativas, RFC 8252](https://www.rfc-editor.org/rfc/rfc8252.html).

En terminales sin navegador se podrá ofrecer Device Authorization si el proveedor lo implementa. El flujo muestra una URL y un código, respeta la caducidad y los intervalos de consulta indicados; no se sustituye por pedir la contraseña de la persona. [Device Authorization, RFC 8628](https://www.rfc-editor.org/rfc/rfc8628.html).

El callback se vincula al inicio de la operación y al proveedor esperado. Se aplican scopes mínimos y las protecciones de refresh que soporte el servidor; para clientes públicos, RFC 9700 exige protección de refresh tokens mediante rotación o restricción al cliente emisor. [OAuth Security BCP, RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html).

Si un proveedor solo admite clientes confidenciales, el adapter puede requerir un intermediario de servidor que custodie el secreto de aplicación. Esa limitación se declara; no se incrusta ese secreto en todas las instalaciones de la CLI.

## 5. Qué guarda el sistema

### Configuración sin secretos

Perfil activo, proveedor, modelo, endpoint, referencias a conexiones, preferencias y servidor compartido. Un archivo de proyecto puede sugerir configuración, pero no cambiar por sí solo la identidad activa, conceder permisos ni seleccionar credenciales ajenas.

### Registro de conexión

Un registro propuesto incluye:

```text
Connection
  id
  owner_principal_id
  tenant_id                 # ámbito del servicio compartido, según contrato
  provider
  external_account_ref
  execution_location        # local | server
  kind                      # delegated_user | installation | service_account
  granted_scopes
  status
  expires_at
  secret_ref
  created_at
  last_used_at
```

El registro identifica quién autorizó el uso y dónde se ejecuta. No contiene tokens en claro ni se incluye en la memoria del modelo.

### Secretos

API keys, access tokens y refresh tokens se guardan mediante un port de secretos. La custodia se define según dónde se ejecute cada operación: un llavero del sistema es una opción para secretos usados por el cliente y un gestor de secretos para los usados por el servidor. La configuración conserva referencias. Si no hay almacén adecuado, ofrecer una sesión efímera o una alternativa configurada explícitamente; no escribir en texto plano silenciosamente. Rotación, revocación y auditoría forman parte del ciclo de vida. [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html).

Ninguno de esos secretos debe aparecer en el repositorio, prompts, historial de la sesión, argumentos del shell, diagnósticos ni telemetría.

## 6. Quién usa la credencial

Se propone un CredentialBroker que resuelve la conexión autorizada para una operación. El modelo solicita una herramienta mediante un identificador; el gateway valida identidad, recurso, propósito y acción antes de invocarla.

```text
Solicitud del modelo
  → gateway de herramientas
  → comprobar identidad, recurso y permisos
  → broker selecciona conexión autorizada
  → adapter obtiene acceso temporal al secreto necesario
  → llamada al proveedor
  → resultado permitido y auditado
```

El broker y el adapter son componentes de confianza. La librería que envía la solicitud al proveedor necesariamente usa la credencial; el objetivo es que el contenido del prompt, el protocolo del harness y los resultados no la incluyan.

Un plugin ejecutado dentro del mismo proceso tiene capacidades del proceso y no está aislado por una interfaz de Python. Los plugins no confiables necesitan un límite de ejecución separado antes de recibir acceso a secretos.

## 7. Permisos efectivos

Para una operación delegada, el permiso efectivo es la intersección de:

- permisos vigentes de la persona;
- autorización concedida a esa conexión;
- reglas del recurso y del proveedor;
- restricciones del agente o skill;
- política del espacio y propósito;
- audiencia y destino de la salida.

Una conexión de Ana no se reutiliza para responder como Bruno. Una cuenta de bot con acceso amplio tampoco demuestra que Bruno pueda leer todos los recursos que el bot ve.

Una tarea de servicio puede usar su propia identidad y grants explícitas, sin simular que actúa como un usuario. Debe quedar distinguida de una operación delegada.

## 8. Herramientas locales

Leer archivos o ejecutar procesos usa permisos del sistema operativo y controles del ejecutor; no requiere OAuth por sí mismo. Deben definirse raíces de archivos permitidas, acceso de red, entorno heredado y procesos que el agente puede iniciar.

Un shell irrestricto con los permisos del usuario puede intentar acceder a sus secretos o a procesos autorizados para usarlos. Ocultar las claves en el prompt o guardarlas en un llavero no basta para afirmar aislamiento frente a ese shell. El MVP deberá describir exactamente su sandbox y límites.

## 9. Qué se comparte entre computadoras

La ubicación de las credenciales personales se acuerda junto con la ejecución de las herramientas y del modelo. Iniciar sesión en el espacio compartido no sube automáticamente tokens ni historial privado.

Un servidor no puede ejecutar usando un token que solo existe en la computadora del usuario. Para trabajos remotos habrá que elegir entre una conexión autorizada específicamente en el servidor, una identidad de servicio o un worker local registrado. Transferir una credencial a otro entorno requiere un flujo explícito y queda fuera de la conexión básica.

Para conocimiento compartido, el servidor debe reevaluar acceso antes de entregar resultados. Las copias que el usuario ya descargó no se vuelven inaccesibles mágicamente después de una revocación.

## 10. Modelos: quién aporta la clave

| Opción | Uso | Consecuencia |
|---|---|---|
| Clave personal | Cada usuario configura su proveedor | Consumo y credenciales propios |
| Endpoint configurado | Una persona o instalación ofrece acceso a un modelo | Requiere definir ubicación, capacidad y permisos del endpoint |
| Gateway compartido | La instalación centraliza inferencia | Puede aplicar cuotas; recibe el contexto enviado y requiere policy explícita |

La modalidad inicial se elige para el recorrido compartido, junto con la ubicación de inferencia y custodia. No se ha seleccionado una opción. Elegir el proveedor no modifica permisos sobre memoria o herramientas.

La compatibilidad con una suscripción de un producto de chat no se presupone. Cada adapter debe declarar el mecanismo de autenticación admitido por su proveedor.

## 11. Desconexión y revocación

`disconnect` bloquea nuevas operaciones de la conexión en el entorno que la administra, cancela trabajos pendientes cuando sea posible y solicita revocación al proveedor si tiene soporte. Debe distinguir entre desvincular la conexión o eliminar una copia de la credencial y revocar efectivamente el token ante el proveedor.

La baja de una persona del espacio compartido invalida acceso al servidor y nuevas delegaciones. Trabajos en curso y caches deben respetar la política de revocación.

Borrar una credencial, cerrar sesión y borrar conocimiento son acciones diferentes. Las fuentes importadas y sus derivados siguen la política de retención y procedencia. No se declara que se eliminó contenido solo porque expiró un token.

## 12. Decisiones a tomar durante la construcción

1. Precisar identidad, membresías y roles del primer recorrido compartido.
2. Definir dónde se ejecutan las operaciones y dónde se custodian sus credenciales.
3. Elegir autenticación del servicio y modalidad de acceso al modelo.
4. Elegir la primera herramienta necesaria para el recorrido y su aislamiento.
5. Concretar OAuth si la herramienta elegida lo requiere.

El usuario no necesita entregar ahora ninguna contraseña ni token para avanzar con esta documentación.
