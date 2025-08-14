from __future__ import annotations

import os
import shutil
import subprocess


def main() -> None:
    px4_fw = os.environ.get("PX4_FIRMWARE")
    if not px4_fw:
        raise SystemExit(
            "Set PX4_FIRMWARE to your PX4-Autopilot path (export PX4_FIRMWARE=~/src/PX4-Autopilot)"
        )

    vehicle = os.environ.get("PX4_SIM_MODEL", "x500").lower()
    # Map friendly names to PX4 make targets for Gazebo (GZ)
    target_map = {
        "x500": "gz_x500",
        "plane": "gz_plane",
        "iris": "gz_iris",
    }
    target = target_map.get(vehicle, "gz_x500")

    if not shutil.which("make"):
        raise SystemExit("`make` not found. Install build-essential.")

    # Use PX4's make wrapper which sets rootfs, scripts, env, and spawns GZ properly.
    cmd = f'cd "{px4_fw}" && PX4_SIM_MODEL="{vehicle}" make px4_sitl {target}'
    print(f"Launching PX4 SITL via: {cmd}")
    # Note: this foreground process will print PX4 + Gazebo logs until you Ctrl+C.
    subprocess.run(cmd, shell=True, check=True)


if __name__ == "__main__":
    main()
