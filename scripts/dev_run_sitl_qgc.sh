#!/usr/bin/env bash
set -euo pipefail
: "${PX4_FIRMWARE:?Set PX4_FIRMWARE (e.g., export PX4_FIRMWARE=~/src/PX4-Autopilot)}"
: "${PX4_SIM_MODEL:=x500}"   # or plane
( cd "$PX4_FIRMWARE" && PX4_SIM_MODEL="$PX4_SIM_MODEL" make px4_sitl gz_"$PX4_SIM_MODEL" ) &
QGC="$HOME/Downloads/QGroundControl.AppImage"
[ -x "$QGC" ] && "$QGC" &
wait
