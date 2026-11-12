FROM node:22-slim AS panel
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web ./
RUN npm run build

FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home brainfold \
 && mkdir /brain /data \
 && chown brainfold /brain /data

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY --from=panel /build/src/brainfold/panel ./src/brainfold/panel
RUN pip install --no-cache-dir .

USER brainfold
EXPOSE 8020
ENTRYPOINT ["brainfold"]
CMD ["serve", "--root", "/brain", "--db", "/data/brainfold.db", "--host", "0.0.0.0"]
