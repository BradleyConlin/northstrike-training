#!/usr/bin/env bash
set -euo pipefail
DEST="$HOME/Downloads/QGroundControl.AppImage"
urls=(
  "https://github.com/mavlink/qgroundcontrol/releases/latest/download/QGroundControl-x86_64.AppImage"
  "https://github.com/mavlink/qgroundcontrol/releases/latest/download/QGroundControl.AppImage"
  "https://d176tv9ibo4jno.cloudfront.net/latest/QGroundControl.AppImage"
)
for u in "${urls[@]}"; do
  echo "Trying: $u"
  if curl -L --retry 3 -f "$u" -o "$DEST"; then break; fi
done
chmod +x "$DEST"
echo "✅ QGC ready at: $DEST"
