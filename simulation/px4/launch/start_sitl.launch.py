from __future__ import annotations

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("px4_firmware", default_value=os.getenv("PX4_FIRMWARE", "")),
            DeclareLaunchArgument(
                "world",
                default_value=os.getenv(
                    "GZ_WORLD",
                    os.path.join(
                        os.getcwd(), "simulation", "gazebo", "worlds", "airfield_day.world"
                    ),
                ),
            ),
            DeclareLaunchArgument("vehicle", default_value=os.getenv("PX4_SIM_MODEL", "x500")),
            SetEnvironmentVariable(
                name="GZ_SIM_RESOURCE_PATH", value=os.path.join(os.getcwd(), "simulation", "gazebo")
            ),
            SetEnvironmentVariable(name="PX4_SIM_MODEL", value=LaunchConfiguration("vehicle")),
            ExecuteProcess(
                cmd=["bash", "-lc", 'gz sim -r "${world}"'], shell=True, output="screen"
            ),
            ExecuteProcess(
                cmd=["bash", "-lc", 'cd "${px4_firmware}" && build/px4_sitl_default/bin/px4 -i 0'],
                shell=True,
                output="screen",
            ),
        ]
    )
