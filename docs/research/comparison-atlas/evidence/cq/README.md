# Evidencia cq — caso Atlas

Prueba local ejecutada el 11 de noviembre de 2026 sobre el servidor OSS de referencia, **no cq.exchange**. Pin: [`2e538ec61b3f136d8aca6dd95db522118dda64eb`](https://github.com/mozilla-ai/cq/tree/2e538ec61b3f136d8aca6dd95db522118dda64eb), commit del 5 de noviembre.

## Contenido

- `run_case.py`: caso común por API en FastAPI TestClient y SQLite efímero. Usa `../../case-atlas.json`; hace logins y emite claves **solo sintéticas**, en memoria, sin registrar sus valores. No inicia listener ni llama a modelos.
- `server-results.json`: resultados de la ejecución; `server-run.log`: stdout/stderr capturado.
- `run_local_case.py`: SDK del mismo checkout con almacenamiento en memoria, consulta y retiro local; `local-results.json`: resultados.
- `upstream-tests.log`: salida de tres módulos de pruebas upstream, no del caso propio.

La fuente privada no se sube al servidor: se usa el candidato ya saneado del fixture común. Esto **no valida** aislamiento de fuente, extracción LLM ni DLP. Los nombres de rol Atlas/Boreal/verificador representan requisitos externos; no pudieron configurarse como roles del servidor. `domains` no se interpreta como ACL. Enviar campos no soportados a approve no prueba bypass de revisiones.

La skill derivada se representa como otra KU y una extensión `case:derived_from` inventada para el experimento; no se presenta como lineage nativo. El export es un snapshot JSON manual, no una función de revocación remota.

## Reproducción

Desde la raíz del repo OIF, con Python 3.11+ y uv disponibles. Revisar primero las instrucciones y el código del checkout fijado. Los siguientes comandos descargan código público y dependencias, sin instalar globalmente. No ejecutar servicios Docker ni apuntar las pruebas a bases existentes.

```sh
CQ_CASE_REPO=work/cq-oss
git -c credential.helper= clone https://github.com/mozilla-ai/cq.git "$CQ_CASE_REPO"
git -C "$CQ_CASE_REPO" checkout --detach 2e538ec61b3f136d8aca6dd95db522118dda64eb
uv sync --frozen --project "$CQ_CASE_REPO/server/backend" --group tests
"$CQ_CASE_REPO/server/backend/.venv/bin/python" docs/research/comparison-atlas/evidence/cq/run_case.py
"$CQ_CASE_REPO/server/backend/.venv/bin/python" docs/research/comparison-atlas/evidence/cq/run_local_case.py "$CQ_CASE_REPO"
```

Tests upstream, desde la raíz del checkout cq:

```sh
env -u TOKEN_EMBEDDING_URL -u CQ_DATABASE_URL -u CQ_TEST_DATABASE_URL \
  server/backend/.venv/bin/python -m pytest \
  server/backend/tests/test_review.py \
  server/backend/tests/test_auth.py \
  server/backend/tests/test_api_keys.py -q
```

Entorno observado: Python 3.12.12, uv 0.10.2, cq-sdk 0.21.2, cq-server 0.0.0.dev0 del checkout, FastAPI 0.137.1, pytest 9.1.0. El script local usa deliberadamente el SDK fuente del pin; el servidor usa su dependencia cq-sdk bloqueada. No se probaron PostgreSQL, embeddings, CLI binaria, clientes de modelos, capa hospedada ni aislamiento OS entre personas. Las dependencias pueden requerir acceso al registro público para reproducir.

## Lectura breve

La revisión pending→approved sí condiciona búsqueda normal. En el servidor base, sin embargo, la revisión requiere solo usuario autenticado y la lectura de aprobados es pública incluso si la unidad dice `tier=private`. La revocación de API key impide escrituras posteriores; no cierra una ruta de lectura pública. Corregir con otra KU y flag no retira automáticamente la anterior ni la skill. El SDK local sí elimina una unidad al revocarla. Nada recupera el snapshot ya entregado en esta prueba.
