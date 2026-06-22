FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && (apt-get install -y --no-install-recommends libaio1t64 \
        || apt-get install -y --no-install-recommends libaio1) \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --upgrade pip && pip install --prefix=/install .

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && (apt-get install -y --no-install-recommends libaio1t64 \
        || apt-get install -y --no-install-recommends libaio1) \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 supply_chain_dw \
    && useradd --uid 1000 --gid supply_chain_dw --shell /bin/bash --create-home supply_chain_dw
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=supply_chain_dw:supply_chain_dw src/ ./src/
COPY --chown=supply_chain_dw:supply_chain_dw data/sample/ ./data/sample/
COPY --chown=supply_chain_dw:supply_chain_dw config/ ./config/
USER supply_chain_dw
ENTRYPOINT ["python", "-m", "supply_chain_dw.main"]
CMD ["--help"]
