# Evidencia ejecutada: Team Memory y caso Atlas

Fecha: 2026-11-11. Solo datos sintéticos. Sin LLM, embeddings externos, cuentas, gastos ni servicios remotos.

## Qué se ejecutó

- Repositorio público: <https://github.com/team-memory/team-memory>.
- Commit fijado: `6a537166b7cff7b5198d86f0c1167df0dc34b836`.
- Toolchain portable oficial Go `1.27.3 darwin/arm64`; SHA256 del archivo `go1.27.3.darwin-arm64.tar.gz`: `dd3908cf20959d798c1e06ebe5b72213f0505ce01373b40ce3110975a6cd99c2`, contrastado con `https://go.dev/dl/?mode=json&include=all`.
- PostgreSQL `16.14`, imagen local preexistente `pgvector/pgvector:pg16`, image ID `sha256:131dcf7ff6a900545df8e7e092c270aa8c6db2f2c818e408cb45ec21316b74e6`. El proyecto recomienda PostgreSQL 17; esta prueba no demuestra paridad de versiones ni soporte oficial para 16.
- Contenedor nuevo, exclusivo, sin montar directorios del usuario, publicado solo en `127.0.0.1:55439`, con credenciales ficticias.
- Un test propio ([atlas_comparison_test.go](atlas_comparison_test.go)) consume el [caso canónico](../../case-atlas.json). Cuatro tests upstream ejercitan promoción, revisión exacta y revocación.
- Resultado final: **cinco tests PASS**, salida completa en [test-output.txt](test-output.txt), código de salida 0. No se utilizó `-race`.

Se probaron servicios de dominio Go sobre roles de aplicación de PostgreSQL y RLS. El test propio marca la sesión de revisión como `AuthPortal` para ejercitar el contrato del servicio: **no prueba autenticación humana ni la interfaz de navegador**. El test upstream de revocación sí usa MCP local con tokens de prueba, pero esto no es una prueba end-to-end de toda la experiencia de producto.

## Resultados importantes

1. La fuente privada y el candidato privado no aparecen a los lectores de Atlas. Bruno acepta una instantánea sin recibir historial privado ni marcadores sensibles del caso.
2. Una revisión nueva invalida la aprobación anterior. Se exige autoridad de origen y destino; publicar hacia organización necesita otra aprobación de destino.
3. **Una memoria escrita directamente en Atlas es visible a lectores aunque esté `unverified`. Editar la lección ya publicada también deja su nueva versión visible antes de reaprobar.** Para mantener el candidato oculto, este escenario usa el espacio privado y después promoción: `unverified` no es un control de visibilidad.
4. Diego se representa como lector: no puede finalizar y recibe `not found`. Esto no implementa su capacidad deseada de comentar/verificar candidatos; la API inspeccionada no ofrece un rol independiente de verificación con aprobación pero sin publicación. `maintainer` reúne ambas autoridades.
5. Eliminar la membresía de Elena bloquea la lectura siguiente. Una copia ya entregada sigue existiendo.
6. Corregir la fuente privada independiente no cambia la instantánea promovida. Cambiar la lección pública a tres reintentos no altera el procedimiento guardado separadamente, que sigue en cinco y aprobado. **No se suministró un vínculo causal genérico entre esos registros**: el resultado describe esta configuración, no demuestra ausencia universal de propagación posible.
7. Archivar retira la lección de la búsqueda predeterminada; conserva las dos revisiones para el historial autorizado. No se probó export/import ni borrado físico.

Los nombres T1–T10 son etiquetas locales de este test, no los identificadores de aceptación A1–A16 del informe de panorama.

## Reproducción

Requisitos: Go 1.27.3, Git y un Docker **local**. Revisar el contexto antes de ejecutar; no usar un daemon remoto ni un puerto ocupado. Fijar y revisar la imagen antes de usarla; el tag puede cambiar. El siguiente ejemplo usa valores de prueba, no credenciales reales.

```sh
git -c credential.helper= clone https://github.com/team-memory/team-memory.git team-memory-atlas
cd team-memory-atlas
git checkout --detach 6a537166b7cff7b5198d86f0c1167df0dc34b836
```

Leer `AGENTS.md`, `go.mod`, `internal/testdb/testdb.go` y los tests. Copiar el test adjunto a `integration/security/atlas_comparison_test.go`. No cambia la implementación. Establecer `ATLAS_CASE_FILE` al path absoluto de `case-atlas.json`.

```sh
docker context inspect
docker run --name tm-comparison-atlas-pg --rm -d --pull never \
  -e POSTGRES_USER=atlas_test -e POSTGRES_PASSWORD=atlas_synthetic_only \
  -e POSTGRES_DB=postgres -p 127.0.0.1:55439:5432 pgvector/pgvector:pg16
docker exec tm-comparison-atlas-pg pg_isready -U atlas_test

# Ajustar rutas: ambos caches pueden permanecer dentro del directorio de prueba.
export GOPATH="$PWD/.atlas-gopath"
export GOCACHE="$PWD/.atlas-gocache"
export GOTOOLCHAIN=local
export TEST_DATABASE_URL='postgres://atlas_test:atlas_synthetic_only@127.0.0.1:55439/postgres?sslmode=disable'
export ATLAS_CASE_FILE='/ruta/absoluta/case-atlas.json'
go test -count=1 -v \
  -run 'Test(AtlasComparison|PromotionConsentAndVisibility|PromotionStaleRejectedCancelled|ApprovalIsRevisionBound|RevocationIsImmediate)$' \
  ./integration/security/

# Detener solo el recurso creado para esta comparación, también si una prueba falla.
docker stop tm-comparison-atlas-pg
```

No usar `make test`: ese target levanta el compose predeterminado del repositorio. El comando anterior dirige las pruebas solo a la base nueva. El harness de tests crea y elimina bases aleatorias dentro de ese cluster.

## Incidencias y limpieza de esta ejecución

Antes de la ejecución final hubo dos errores del test propio, ambos corregidos: un tipo de literal Go incorrecto y una expectativa `forbidden` donde Diego recibe `not found` porque no puede ver la solicitud. No se corrigió ni modificó código upstream para conseguir el PASS.

El contenedor exclusivo fue detenido y eliminado por `--rm`; también se eliminó su volumen anónimo, que contenía solo datos sintéticos. Se conservaron bajo `work/comparison/` el checkout, el test propio, el toolchain portable y sus caches. No se modificaron servicios existentes ni instalaciones globales.

## Fuentes de semántica no ejecutada

- [Trust y promoción en el commit](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/docs/decisions/trust-rules.md): rechazar conserva visibilidad; aprobación no equivale a verdad.
- [Búsqueda SQL](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/internal/postgres/queries/search.sql): filtra scopes/status; no exige `approved` para recuperar.
- [Roles y tipos](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/internal/memory/types.go): reader/writer/maintainer y relaciones específicas de promoción/override. [CreateInput](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/internal/memory/service.go) no ofrece un campo genérico `derived_from`.
- [Mirror y recuperación](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/docs/operations/mirror.md): exportación unidireccional por operador; recuperación excepcional recrea contenido sin restaurar aprobación. **No ejecutado aquí**.
- [Implementación de recuperación](https://github.com/team-memory/team-memory/blob/6a537166b7cff7b5198d86f0c1167df0dc34b836/internal/mirror/rebuild.go): no es prueba de protección completa contra reimportar toda copia antigua.
