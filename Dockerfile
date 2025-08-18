# ----- build ------------------------------------------------------------------------------------- 
FROM --platform=$BUILDPLATFORM python:3.13-slim-bookworm AS builder

ARG TARGETARCH
ARG BUILD_TIME
ARG GIT_COMMIT
ARG GIT_BRANCH

# minimal build dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git

# install uv from official image
COPY --from=ghcr.io/astral-sh/uv:0.5.27 /uv /bin/uv

# optimize uv for docker
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system

WORKDIR /build

# dependency installation (cached layer)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# application installation
COPY app/ ./app/
COPY arian/ ./arian/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev && \
    uv pip install --no-deps -e . && \
    python -m compileall -q /build

# write version info
RUN echo "{\"build_time\": \"${BUILD_TIME:-$(date -u +%Y%m%d-%H%M%S)}\", \
          \"git_commit\": \"${GIT_COMMIT:-dev}\", \
          \"git_branch\": \"${GIT_BRANCH:-main}\"}" > /build/app/version.json

# download grpc_health_probe in parallel stage
FROM curlimages/curl:8.11.1 AS health-probe

ARG TARGETARCH

USER root
RUN GRPC_HEALTH_PROBE_VERSION=v0.4.39 && \
    ARCH=${TARGETARCH:-amd64} && \
    curl -fsSL "https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-${ARCH}" \
    -o /grpc_health_probe && \
    chmod +x /grpc_health_probe

# ----- runtime ----------------------------------------------------------------------------------- 

FROM python:3.13-slim-bookworm AS runtime

# metadata
LABEL org.opencontainers.image.title="arian-receipts" \
      org.opencontainers.image.description="Receipt Image Processing Service" \
      org.opencontainers.image.source="https://github.com/xhos/arian-receipts"

# install runtime deps and create user in single layer
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    libgomp1 \
    libglib2.0-0 \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    groupadd -g 1001 app && \
    useradd -u 1001 -g app -m -s /bin/false app && \
    mkdir -p /tmp/receipts && \
    chown app:app /tmp/receipts

# copy application and dependencies
COPY --from=builder --chown=app:app /build/.venv /app/.venv
COPY --from=builder --chown=app:app /build/app /app/app
COPY --from=builder --chown=app:app /build/arian /app/arian

# fix shebang in executable to point to correct python path
RUN sed -i '1s|#!/build/.venv/bin/python3|#!/app/.venv/bin/python3|' /app/.venv/bin/arian-receipts

# copy health probe
COPY --from=health-probe --chown=app:app /grpc_health_probe /usr/local/bin/grpc_health_probe

# set python path and environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PYTHONOPTIMIZE=2 \
    # LOG_LEVEL=INFO \
    # MAX_UPLOAD_MB=10 \
    # PROVIDER_TIMEOUT_SECS=20 \
    TMPDIR=/tmp/receipts

USER app
WORKDIR /app

EXPOSE 50051

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/usr/local/bin/grpc_health_probe", "-addr=:50051"]

# use exec form for proper signal handling
ENTRYPOINT ["arian-receipts"]