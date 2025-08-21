FROM python:3.10-slim AS base

# Fast, quiet, reproducible installs
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Minimal system deps only (no dev toolchains, no CUDA)
# libgl1: matplotlib runtime; tini: clean signal handling (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps with no cache. We rely on CPU wheels.
# (stable-baselines3 pulls torch CPU; no CUDA.)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what we need into the image (keeps layers small)
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY configs/ /app/configs/
COPY simulation/ /app/simulation/
COPY budgets.yaml /app/budgets.yaml

# Runtime env
ENV MAVSDK_URL="udpin://0.0.0.0:14540" \
    PYTHONPATH="/app/src:$PYTHONPATH"

# Quick healthcheck (imports are cheap and prove env is sane)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import numpy, torch" || exit 1

# Default: show container env (you can override with `docker run ... python ...`)
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-c", "import os; print('Container up. PYTHONPATH=', os.environ.get('PYTHONPATH','')); print('MAVSDK_URL=', os.environ.get('MAVSDK_URL',''))"]
