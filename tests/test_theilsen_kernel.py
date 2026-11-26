from jointfolio.joint_sen_fit.estimator import slope_by_pairs


def test_robust_slope_survives_bad_probe_and_equal_heat_signals():
    points = [(x, 3 * x + 2) for x in range(10)] + [(4, 2000)]
    assert slope_by_pairs(points) == 3
    assert slope_by_pairs([(1, 0), (1, 4)]) == 0
