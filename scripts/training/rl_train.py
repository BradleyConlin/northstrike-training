import argparse
import os

import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

# Import registers the env id "Px4GzHoverEnv-v0"
import rl.envs  # noqa: F401


def make_env(env_id: str, **env_kwargs):
    def _thunk():
        return gym.make(env_id, **env_kwargs)

    return _thunk


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cfg", type=str, default="", help="(unused placeholder: keeping your CLI)"
    )
    parser.add_argument("--total-steps", type=int, default=10_000)
    parser.add_argument("--udp-url", type=str, default="udp://:14540")
    args = parser.parse_args()

    # Env kwargs (align with our env defaults)
    env_kwargs = dict(
        udp_url=args.udp_url,
        step_hz=10.0,
        nudge=0.3,
        episode_seconds=20,
        pos_err_done_m=8.0,
        connect_timeout_s=180.0,
        debug=True,
    )

    env_id = "Px4GzHoverEnv-v0"
    vec_env = DummyVecEnv([make_env(env_id, **env_kwargs)])

    model = PPO("MlpPolicy", vec_env, verbose=1)
    model.learn(total_timesteps=args.total_steps)

    os.makedirs("models/checkpoints", exist_ok=True)
    model.save("models/checkpoints/ppo_hover_latest.zip")
    print("Saved model to models/checkpoints/ppo_hover_latest.zip")


if __name__ == "__main__":
    main()
