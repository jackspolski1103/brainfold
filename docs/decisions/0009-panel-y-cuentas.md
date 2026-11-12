# 0009 — Panel web y cuentas propias

Fecha: 12 de noviembre de 2026.

Estado: confirmado por el autor.

## Elección del autor

«Quiero hacerlo muy bien y con el panel web también, al estilo Infisical o Langfuse».
Ante tres preguntas concretas eligió:

1. **Panel:** aplicación React (Vite, shadcn/ui) sobre una API del mismo servidor Python,
   en un solo contenedor. Alternativas descartadas: HTML generado en Python (HTMX) y
   reescribir todo en Next.js.
2. **Login:** email y contraseña propios. El primer usuario crea la organización, invita al
   resto y cada persona genera su token de harness. Alternativa descartada: solo
   Google/GitHub/OIDC, que obliga a registrar una aplicación antes de la primera prueba.
3. **Primera versión del panel:** accesos por carpeta, miembros y tokens, explorador de
   archivos de solo lectura y actividad.

También indicó que dentro de las carpetas habrá skills accesibles para el agente.

## Implementado en este incremento (sin interfaz)

- `src/oif/accounts.py`: cuentas, invitaciones, grupos, tokens y actividad en SQLite.
  Contraseñas con scrypt; tokens e invitaciones guardados solo como resumen; bloqueo tras
  cinco intentos fallidos.
- `src/oif/server.py`: una sola aplicación con el endpoint MCP y la API `/api` del panel.
  Los tokens de desarrollo por variable de entorno se eliminaron.
- Los grupos pasan del `.oif.toml` de la raíz a la base de cuentas; los permisos de cada
  carpeta siguen en su `.oif.toml` y el panel los edita ahí.
- Herramienta MCP `listar_skills`.

## Criterios adoptados

- Un administrador ve la estructura de carpetas y sus accesos, pero no lee contenido que no
  tenga concedido. Puede concederse acceso, y eso queda en la actividad y en git.
- El identificador de una persona en los permisos es su email.

## Pendiente

La interfaz React, el empaquetado en contenedor, exponer el servidor fuera de loopback
(requiere TLS), cambio de contraseña y recuperación de cuenta, y login con proveedores
externos.
