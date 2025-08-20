from src.rl.gridworld import GridWorld, GWCfg


def test_env_step_and_safety():
    cfg = GWCfg(w=6, h=5, start=(0, 0), goal=(5, 4), obstacles={(2, 2)}, hazards={(1, 0)})
    env = GridWorld(cfg, seed=1)
    s = env.reset(1)
    assert s == (0, 0)
    # step into hazard -> unsafe flag + penalty in reward already
    s2, r, done, info = env.step(0)  # move E
    assert s2 == (1, 0)
    assert info.get("unsafe", False)
    # hitting obstacle keeps position and yields obstacle penalty
    env.pos = (2, 1)
    s3, r2, done2, info2 = env.step(2)  # move S into obstacle at (2,2)
    assert s3 == (2, 1)
    assert r2 < -0.5 and not done2
