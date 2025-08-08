# ----- build ----------

FROM python:3.15-slim-bookworm AS builder

ARG BUILD_TIME
ARG GIT_COMMIT
ARG GIT_BRANCH

# install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential ca-certificates curl git && \
    rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# add uv to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /build

# copy dependencies
COPY pyproject.toml uv.lock ./

# install dependencies and pre-compile
RUN uv sync --frozen --no-dev --no-editable && \
    python -m compileall /build/.venv

# copy source
COPY arian_receipts/ ./arian_receipts/

# install and compile
RUN uv pip install --no-deps . && python -m compileall /build/.venv/lib/python*/site-packages/arian_receipts

# download grpc_health_probe
RUN GRPC_HEALTH_PROBE_VERSION=v0.4.39 && \
    curl -sL "https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64" \
    -o /build/grpc_health_probe && \
    chmod +x /build/grpc_health_probe

# ----- runtime ----------
FROM python:3.15-slim-bookworm

# metadata labels
LABEL org.opencontainers.image.title="arian-receipts" \
      org.opencontainers.image.description="Receipt Image Processing Service" \
      org.opencontainers.image.vendor="Arian" \
      org.opencontainers.image.source="https://github.com/xhos/arian-receipts" \
      org.opencontainers.image.created="${BUILD_TIME}" \
      org.opencontainers.image.revision="${GIT_COMMIT}"

# install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates libgomp1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/* && \
    # create non-root user
    groupadd -g 1001 arian && \
    useradd -u 1001 -g arian -m -d /app -s /bin/false arian && \
    # create necessary directories
    mkdir -p /app /tmp/receipts && \
    chown -R arian:arian /app /tmp/receipts

# copy python environment from builder
COPY --from=builder --chown=arian:arian /build/.venv /app/.venv

# copy health check tool
COPY --from=builder --chown=arian:arian /build/grpc_health_probe /usr/local/bin/grpc_health_probe

# set python environment
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    # python optimizations
    PYTHONOPTIMIZE=1 \
    # service configuration defaults
    GRPC_PORT=50052 \
    LOG_LEVEL=INFO \
    MAX_UPLOAD_MB=10 \
    PROVIDER_TIMEOUT_SECS=20 \
    # temp directory for processing
    TMPDIR=/tmp/receipts

# switch to non-root user
USER arian
WORKDIR /app

# expose gRPC port
EXPOSE 50052

# health check with proper timing
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/usr/local/bin/grpc_health_probe", "-addr=:50052"]

# run the service
ENTRYPOINT ["python", "-m", "arian_receipts"]
CMD ["--host", "0.0.0.0", "--port", "50052"]