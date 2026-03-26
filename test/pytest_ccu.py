import pytest
from model.CriticalCareUnit import Scenario, CCU_model


class ConstantDist:
    """Simple deterministic distribution for testing."""
    def __init__(self, value):
        self.value = value

    def sample(self):
        return self.value

def make_test_scenario(
    beds,
    unplanned_iat=2.5,
    planned_iat=10_000,
    unplanned_los=10,
    planned_los=10,
):
    """
    Build a scenario with deterministic arrivals and 
    LOS values so tests are stable.
    """
    s = Scenario(random_number_set=123)
    s.CCU_beds = beds
    s.warm_up = 0

    # deterministic arrivals
    s.arrival_dist_emerg = ConstantDist(unplanned_iat)
    s.arrival_dist_ward = ConstantDist(unplanned_iat)
    s.arrival_dist_other = ConstantDist(unplanned_iat)
    s.arrival_dist_AnE = ConstantDist(unplanned_iat)
    s.arrival_dist_xray = ConstantDist(unplanned_iat)


    s.arrival_dist_elective = ConstantDist(planned_iat)

    # deterministic LOS
    s.emerg_dist = ConstantDist(unplanned_los)
    s.ward_dist = ConstantDist(unplanned_los)
    s.other_dist = ConstantDist(unplanned_los)
    s.AnE_dist = ConstantDist(unplanned_los)
    s.xray_dist = ConstantDist(unplanned_los)
    s.elect_dist = ConstantDist(planned_los)

    return s


def run_model(scenario, rc_period=100):
    model = CCU_model(scenario)
    model.run(results_collection_period=rc_period, warm_up=0)
    return model.run_summary_frame().iloc[0]


def test_more_beds_reduce_queue_for_unplanned_patients():
    """
    Same demand, more beds => queue should be lower.
    """
    few_beds = make_test_scenario(beds=2, unplanned_iat=2.5, unplanned_los=10)
    many_beds = make_test_scenario(beds=8, unplanned_iat=2.5, unplanned_los=10)

    few = run_model(few_beds, rc_period=100)
    many = run_model(many_beds, rc_period=100)

    assert many["CCU_bed_queue"] < few["CCU_bed_queue"]


def test_more_beds_reduce_wait_for_ccu_bed():
    """
    Same demand, more beds => mean waiting time should be lower.
    """
    few_beds = make_test_scenario(beds=2, unplanned_iat=2.5, unplanned_los=10)
    many_beds = make_test_scenario(beds=8, unplanned_iat=2.5, unplanned_los=10)

    few = run_model(few_beds, rc_period=100)
    many = run_model(many_beds, rc_period=100)

    assert many["CCU_bed_wait_time"] < few["CCU_bed_wait_time"]


def test_more_beds_do_not_increase_occupancy_percentage_under_same_demand():
    """
    With the same arrival stream, 
    adding beds should usually reduce utilisation %.
    """
    few_beds = make_test_scenario(beds=2, unplanned_iat=5, unplanned_los=10)
    many_beds = make_test_scenario(beds=10, unplanned_iat=5, unplanned_los=10)

    few = run_model(few_beds, rc_period=100)
    many = run_model(many_beds, rc_period=100)

    assert many["bed_util"] <= few["bed_util"]


def test_very_large_number_of_beds_gives_zero_queue_and_zero_wait():
    """
    Infinite beds cases
    """
    huge_capacity = make_test_scenario(beds=10_000, 
                                       unplanned_iat=1, 
                                       unplanned_los=10)
    result = run_model(huge_capacity, 
                       rc_period=100)

    assert result["CCU_bed_queue"] == pytest.approx(0.0)
    assert result["CCU_bed_wait_time"] == pytest.approx(0.0)


def test_zero_beds_raises_error():
    """
    SimPy resources require positive capacity.
    Zero beds should fail clearly at model construction time.
    """
    scenario = make_test_scenario(beds=0)

    with pytest.raises((ValueError, RuntimeError)):
        CCU_model(scenario)

def test_no_elective_patients_means_zero_cancellations():
    """
    If there are no planned (elective) arrivals,
    then cancellations must be zero.
    """
    # Set elective IAT extremely large so none arrive
    scenario = make_test_scenario(
        beds=5,
        unplanned_iat=2,
        planned_iat=1_000_000,  # effectively no elective arrivals
        unplanned_los=10
    )

    result = run_model(scenario, rc_period=100)

    assert result["n_planned_cancellations"] == 0

def test_high_unplanned_demand_causes_high_planned_cancellations():
    """
    When unplanned arrivals are very frequent (high pressure),
    beds should be occupied most of the time and planned
    patients should be cancelled frequently.
    """

    # Low pressure scenario (baseline)
    low_pressure = make_test_scenario(
        beds=5,
        unplanned_iat=10,   # slow arrivals
        planned_iat=5,      # some elective patients
        unplanned_los=10
    )

    # High pressure scenario
    high_pressure = make_test_scenario(
        beds=5,
        unplanned_iat=1,   
        planned_iat=5,
        unplanned_los=10
    )

    low = run_model(low_pressure, rc_period=200)
    high = run_model(high_pressure, rc_period=200)

    # cancellations should be much higher under pressure
    assert high["n_planned_cancellations"] > low["n_planned_cancellations"]