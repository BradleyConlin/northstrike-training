#!/usr/bin/env bash
set -euo pipefail
: "${PX4_FIRMWARE:?Set PX4_FIRMWARE (e.g., export PX4_FIRMWARE=~/src/PX4-Autopilot)}"
: "${PX4_SIM_MODEL:=x500}"   # or plane

# Launch PX4 SITL (spawns Gazebo + vehicle)
( cd "$PX4_FIRMWARE" && PX4_SIM_MODEL="$PX4_SIM_MODEL" make px4_sitl gz_"$PX4_SIM_MODEL" ) &

# Launch QGC (allow override via QGC_APPIMAGE)
QGC="${QGC_APPIMAGE:-$HOME/Downloads/QGroundControl.AppImage}"
if [[ -x "$QGC" ]]; then
  "$QGC" &
else
  echo "⚠️  QGC not found at: $QGC" >&2
  echo "   Run ./scripts/get_qgc_appimage.sh or set QGC_APPIMAGE=/path/to/QGroundControl.AppImage" >&2
fi

wait
