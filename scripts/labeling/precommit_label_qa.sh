#!/usr/bin/env bash
set -euo pipefail
IMG_ROOT="data/images"
LBL_ROOT="data/labels"
LMAP="configs/labeling/labelmap.yaml"

if [[ ! -d "$IMG_ROOT" || ! -d "$LBL_ROOT" ]]; then
  echo "[label-qa] dataset dirs not present; skipping."
  exit 0
fi

python scripts/labeling/qa_check.py \
  --images "$IMG_ROOT" \
  --labels "$LBL_ROOT" \
  --labelmap "$LMAP"
