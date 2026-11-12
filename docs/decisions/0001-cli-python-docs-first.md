# 0001 — Harness CLI, Python y documentación primero

Fecha: 11 de noviembre de 2026.

Estado: aceptada por el autor.

## Contexto

La visión original define un framework de inteligencia colaborativa con modelos, canales, almacenamiento y harnesses intercambiables. Al iniciar el repositorio se propuso una web como primera experiencia. El autor aclaró que espera un harness de agente utilizable por terminal, con una experiencia comparable en forma de uso a la de los agentes de terminal que ya utiliza.

## Decisión

- Construir una experiencia CLI como entrada principal inicial.
- Usar Python para lo agéntico.
- Completar la documentación del producto y la arquitectura antes de implementar.
- Consultar decisiones de producto y arquitectura conforme aparezcan.
- Mantener el proyecto personal y separado del trabajo del autor.

## Consecuencias

El diseño incluye sesiones, ciclo de ejecución, herramientas locales, permisos de ejecución, cancelación y memoria. Las conexiones se administran desde comandos del CLI; el navegador puede utilizarse para completar autenticación con proveedores.

El harness de referencia debe consumir contratos del núcleo. Ofrecer uno propio es compatible con permitir que otros harnesses utilicen conocimiento, permisos y memoria mediante adapters.

Web, Slack, Teams y otros canales permanecen como posibilidades de integración. No son requisitos del primer punto de entrada.

## Todavía no decidido

Nombre definitivo, repositorio remoto, visibilidad, licencia, librerías concretas, alcance de herramientas locales, proveedor del modelo, autenticación y distribución local/remota.
