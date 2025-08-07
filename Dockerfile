# ---------- builder ----------
FROM python:3.13.5-slim-bookworm AS build

# metadata
ARG VCS_REF="unknown"
ARG BUILD_DATE
LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.source="https://github.com/your-org/arian-receipts"

# system deps
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install --no-install-recommends -y build-essential ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# project deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable  

# project code
COPY . .
RUN uv pip install --no-deps .           

# gRPC health-probe
ARG GRPC_HEALTH_PROBE_VERSION=v0.4.39
RUN curl -fsSL -o /usr/local/bin/grpc_health_probe \
      https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 \
    && chmod +x /usr/local/bin/grpc_health_probe

# ---------- runtime ----------
FROM python:3.13.5-slim-bookworm

RUN apt-get update && \
    apt-get install --no-install-recommends -y ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    addgroup --system --gid 1000 arian && \
    adduser  --system --uid 1000 --gid 1000 --disabled-password arian

WORKDIR /app
COPY --from=build /app/.venv /app/.venv                 
COPY --from=build /usr/local/bin/grpc_health_probe /usr/local/bin/

ENV PATH="/app/.venv/bin:${PATH}"
USER arian
EXPOSE 8080

ENTRYPOINT ["arian-receipts"]
