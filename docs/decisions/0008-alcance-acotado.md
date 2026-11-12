# 0008 — Alcance acotado: cerebro por MCP y nada más

Fecha: 12 de noviembre de 2026.

Estado: confirmado por el autor. Reemplaza [0003](0003-consumo-de-conocimiento-compartido.md)
y [0005](0005-primer-corte-capacidad-compartida-mcp.md).

## Elección del autor

«Definamos bien el scope y hagamos algo armable y con criterio. No quiero algo que haga
todo». Ante la propuesta concreta respondió «sí a las tres, borrá el harness»:

1. Se acepta la lista de exclusiones de [scope.md](../scope.md). En particular no habrá
   motor de borradores, revisión y aprobación: el permiso de escritura es la autoridad
   para publicar en una carpeta, y el historial es git.
2. Se elimina el harness propio: runtime, adapter de OpenAI, CLI conversacional, servicio
   HTTP, registro de capacidades y sus pruebas. Quedan en el historial de git.
3. Despliegue: un servidor por equipo, levantado por el equipo. Se descartó el modo local
   por persona sincronizado con git porque anula los permisos de lectura.

Durante el mismo intercambio el autor pidió «un panel web o algo así para poder manejar
los accesos a la información». Entra al alcance como pieza prevista y acotada a accesos;
un editor web de contenido sigue fuera.

## Consecuencias

- `docs/vision.md` y la investigación quedan como antecedentes históricos, no como plan.
- Se eliminaron `docs/cli.md`, `docs/first-increment.md`, `docs/development.md` y
  `docs/credentials.md`, que describían el harness.
- El paquete depende solo de `mcp` y `uvicorn`.

## Pendiente

Login real, quién administra accesos y forma del panel, nombre, licencia y publicación.
