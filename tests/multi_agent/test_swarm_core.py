import numpy as np

from src.multi_agent.swarm import auction_assign, min_pairwise_distance, simulate_swarm


def test_formation_and_separation():
    offs = [(1.0, 0.0), (-1.0, 0.0), (0.0, 1.0)]
    wps = [(4.0, 0.0), (4.0, 4.0)]
    T = 320  # a few more steps to settle
    tr = simulate_swarm(
        4,
        offs,
        wps,
        dt=0.05,
        steps=T,
        vmax=2.0,
        kp_leader=1.0,
        kp_form=1.0,
        r_avoid=0.85,
        k_avoid=0.9,  # <-- stronger avoidance than before
    )
    # followers near desired offsets from leader
    leader = tr[-1, 0, :]
    errs = []
    for i, (ox, oy) in enumerate(offs, start=1):
        des = leader + np.array([ox, oy])
        errs.append(float(np.linalg.norm(tr[-1, i, :] - des)))
    assert np.median(errs) < 0.7
    # no close approaches
    assert min_pairwise_distance(tr) >= 0.30


def test_auction_unique_pairs():
    agents = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
    goals = [(0.5, 0.0), (5.2, 0.0), (9.6, 0.0)]
    pairs = auction_assign(agents, goals)
    assert len(pairs) == 3
    assert len({i for i, j in pairs}) == 3
    assert len({j for i, j in pairs}) == 3
