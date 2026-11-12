# 0007 — Cerebro compartido agnóstico al harness

Fecha: 12 de noviembre de 2026.

Estado: confirmado por el autor. Reemplaza la parte de [0001](0001-cli-python-docs-first.md)
que definía un harness propio como primer producto.

## Elección del autor

«Agnóstico al harness. Quiero hasta poder conectar cc».

El producto es el cerebro compartido: carpetas y archivos con permisos, expuestos por MCP
para que Claude Code, Codex o cualquier otro harness los use. El proyecto no compite con
esos harnesses. La colaboración sigue siendo el núcleo ([0004](0004-colaboracion-como-nucleo-del-producto.md))
y el modelo de memoria es el de [0006](0006-memoria-como-repositorio-con-permisos.md).

## Alternativa descartada

Mantener el harness propio como producto y sumarle el servidor: duplica la superficie a
mantener y no alcanza a los harnesses existentes.

## Implementado en este incremento

- `src/oif/brain.py`: carpetas y archivos reales en disco. Cada carpeta puede tener un
  `.oif.toml` con `description`, `start_here`, `read` y `write`; los grupos se definen en
  el `.oif.toml` de la raíz.
- Lectura: se deniega salvo concesión y se restringe por intersección hacia abajo.
  Escritura: decide la carpeta más cercana que la declare; denegada por defecto.
- Metadatos, `.git` y enlaces simbólicos nunca son visibles ni escribibles para el agente.
- Herramientas MCP: `listar_memoria`, `leer_memoria`, `escribir_memoria`, `buscar_memoria`.
- Si la raíz del cerebro es un repositorio git, cada escritura queda como commit con la
  identidad de quien escribió.
- Las skills son carpetas con un `SKILL.md` dentro del mismo árbol y los mismos permisos.

## Límites

La identidad sigue siendo por tokens de desarrollo. Los permisos se editan en disco; no
hay administración conversacional de ACL. Hay dos niveles (leer y escribir); «entrar»
equivale a leer. Escribir en una carpeta compartida exige permiso de escritura, que hoy
hace las veces de autoridad editorial de [0003](0003-consumo-de-conocimiento-compartido.md);
el flujo de borrador, revisión y promoción sigue pendiente. La última escritura gana.

## Resuelto después

El harness propio se eliminó; véase [0008](0008-alcance-acotado.md).
