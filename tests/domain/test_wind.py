from src.domain.wind import OUParams, WindField


def test_wind_stats_and_repeatability():
    wf1 = WindField(OUParams(tau_s=2.0, sigma=1.5), OUParams(tau_s=3.0, sigma=0.8), seed=7)
    wf2 = WindField(OUParams(tau_s=2.0, sigma=1.5), OUParams(tau_s=3.0, sigma=0.8), seed=7)
    dt = 0.05
    N = 400
    s1 = []
    s2 = []
    for _ in range(N):
        s1.append(wf1.sample(dt))
        s2.append(wf2.sample(dt))
    # same seed => identical sequences
    assert s1 == s2
    # variance roughly near sigma^2 (loose check)
    xs = [v[0] for v in s1]
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / len(xs)
    assert 0.5 < var < 4.0
