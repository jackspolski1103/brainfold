# 0018 A landing page and a public demo of the documentation

Date: 2026-11-19. Status: accepted by the author ("dejar alguna web en railway", "Solo docs y login", "puede ser otro repo").

- **Landing page:** one static page in its own repository, `jackspolski1103/brainfold-site`, served at <https://brainfold-site-production.up.railway.app>. A separate repository is what comparable projects do (Langfuse, basic-memory). It does not copy the documentation.
- **Documentation demo:** a second service, `brainfold-demo`, runs this repository's image at <https://brainfold-demo-production.up.railway.app>. It has no volume, no account and an empty brain: visitors read the documentation at `#/docs`; nobody can create the first account without the setup code in the service logs. A shared demo account was the alternative; the author chose not to publish one.
- **Hosting:** both are new services in the author's existing Railway project, apart from the service that holds the team's brain.
- **Still pending:** hosting for a real deployment by another team, and a domain of its own.
