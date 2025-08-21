FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# minimal tools; tini for proper signal handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install only the small runtime deps
COPY deployment/docker/requirements-inference.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# bring in just what eval needs
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY configs/ /app/configs/
COPY simulation/ /app/simulation/
COPY budgets.yaml /app/budgets.yaml

ENV PYTHONPATH="/app/src" \
    MAVSDK_URL="udpin://0.0.0.0:14540"

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import numpy,yaml" || exit 1

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python","scripts/evaluation/rl_eval.py"]
