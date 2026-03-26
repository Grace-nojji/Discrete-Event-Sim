"""
A Critical care unit model

Main model class: CCU_model
Patient process class: CCU_Patient

Process overview:

"""

import numpy as np
import pandas as pd
import itertools
import simpy
from joblib import Parallel, delayed
from distribution.empirical import make_group_dist
from distribution.distributions import Exponential, Lognormal

# DEFAULT RESOURCES
N_BED = 24


# default parameters for arrival distributions (unplanned)
emerg_iat = 37.03
ward_iat = 25.97
other_iat = 47.1
AnE_iat = 22.72
xray_iat = 575.09
# arrival distribution for planned
group_dist = make_group_dist(random_seed=5)

# mean Length of stay (Lognormal)
emerg_mean_los = 140.15
ward_mean_los = 177.89
other_mean_los = 212.86
AnE_mean_los = 128.86
xray_mean_los = 87.53
elect_mean_los = 57.34

# Standard deviation of length of stay (Lognormal)
emerg_std_los = 218.02
ward_std_los = 276.54
other_std_los = 457.67
AnE_std_los = 267.51
xray_std_los = 108.15
elect_std_los = 99.78


TRACE = False

# default random number SET
DEFAULT_RNG_SET = None
N_STREAMS = 30


# default results collection period (8760 hours)
DEFAULT_RESULTS_COLLECTION_PERIOD = 365 * 24

# default number of replications
DEFAULT_N_REPS = 5

# warmup auditing
DEFAULT_WARMUP_AUDIT_INTERVAL = 12


def trace(msg):
    """
    Utility function for printing simulation
    set the TRACE constant to FALSE to
    turn tracing off.

    Params:
    -------
    msg: str
        string to print to screen.
    """
    if TRACE:
        print(msg)


class Scenario:
    """
    Parameter class for Critical Care Unit
    (CCU) simulation model
    """

    def __init__(self, random_number_set=DEFAULT_RNG_SET):
        """
        Initialises the Scenario class

        Parameters:
        -----------
        random_number_set: int, optional (default=DEFAULT_RNG_SET)
            Set to control the initial seeds of each stream of pseudo
            random numbers used in the model.

        """
        # resource counts
        self.CCU_beds = N_BED

        # warm-up
        self.warm_up = 0.0

        # sampling
        self.random_number_set = random_number_set
        self.init_sampling()

    def set_random_no_set(self, random_number_set):
        """
        Controls the random sampling

        Parameters:
        ----------
        random_number_set: int
            Used to control the set of psuedo random numbers
            used by the distributions in the simulation.
        """
        self.random_number_set = random_number_set
        self.init_sampling()

    def init_sampling(self):
        """
        Defines the distribution by the model and
        initialises
        the random seeds of each.
        """
        # create random number streams
        rng_streams = np.random.default_rng(self.random_number_set)
        self.seeds = rng_streams.integers(0, 999999999, size=N_STREAMS)

        # inter-arrival distribution for unplanned cases
        self.arrival_dist_emerg = Exponential(emerg_iat, random_seed=self.seeds[0])
        self.arrival_dist_ward = Exponential(ward_iat, random_seed=self.seeds[1])
        self.arrival_dist_other = Exponential(other_iat, random_seed=self.seeds[2])
        self.arrival_dist_AnE = Exponential(AnE_iat, random_seed=self.seeds[3])
        self.arrival_dist_xray = Exponential(xray_iat, random_seed=self.seeds[4])

        # inter-arrival distribution for planned cases
        self.arrival_dist_elective = make_group_dist(random_seed=self.seeds[5])

        # length of stay distribution for unplanned patients
        self.emerg_dist = Lognormal(
            emerg_mean_los, emerg_std_los, random_seed=self.seeds[6]
        )
        self.ward_dist = Lognormal(
            ward_mean_los, ward_std_los, random_seed=self.seeds[7]
        )
        self.other_dist = Lognormal(
            other_mean_los, other_std_los, random_seed=self.seeds[8]
        )
        self.AnE_dist = Lognormal(AnE_mean_los, AnE_std_los, random_seed=self.seeds[9])
        self.xray_dist = Lognormal(
            xray_mean_los, xray_std_los, random_seed=self.seeds[10]
        )
        self.elect_dist = Lognormal(
            elect_mean_los, elect_std_los, random_seed=self.seeds[11]
        )


class CCU_Patients:
    """
    A class for each CCU Patient.
    """

    def __init__(self, identifier, env, args, group):
        """
        Initialises each CCU class

        Params:
        -----
        identifier: int
            assigns an id to each patient

        env: simpy.Environment
            patient environment

        args: Scenario
            scenario
        group: Planned/Unplanned
        """
        self.identifier = identifier
        self.env = env
        self.args = args
        self.group = group

        self.beds = args.beds

        self.wait_time = 0
        self.planned_cancellations = 0
        self.total_bed_busy_time = 0
        self.total_patients_admitted = 0

    def assessment(self):
        """
        Patient Sequence of Event:
        UNPLANNED
        1. request bed
        2. wait if needed
        3. stay
        4. discharge
        5. bed cleaning for 5hrs

        PLANNED
        1. if no bed available at arrival, cancel;
        otherwise admit
        2. stay
        3. discharge
        4. bed cleaning

        """

        arrival_time = self.env.now

        if self.group["type"] == "planned":
            if self.beds.count >= self.beds.capacity:
                self.patient_gets_cancelled()
                trace(
                    f'{self.group["name"]}-patient {self.identifier} PLANNED CANCELLED at{self.env.now:.2f}'
                )
                return

            trace(
                f'{self.group["name"]}-patient {self.identifier} PLANNED ARRIVED at {self.env.now:.2f}'
            )

        elif self.group["type"] == "unplanned":
            trace(
                f'{self.group["name"]}-patient {self.identifier} ARRIVED at {self.env.now:.2f}'
            )

        with self.beds.request(priority=self.group["priority"]) as req:
            yield req

            # waiting time
            self.wait_time = self.env.now - arrival_time

            # notify observer when patient gets a bed
            self.patient_gets_admitted()

            trace(
                f'{self.group["name"]}-patient {self.identifier} ENTERED CCU after waiting {self.wait_time:.2f}'
            )

            los = self.group["los_dist"].sample()

            # occupancy tracking
            self.total_bed_busy_time += los
            self.total_patients_admitted += 1

            yield self.env.timeout(los)

            self.patient_gets_discharged()

            trace(
                f'{self.group["name"]}-patient {self.identifier} DISCHARGED AT {self.env.now:.2f}'
            )

            cleaning_time = 5
            self.total_bed_busy_time += cleaning_time
            yield self.env.timeout(cleaning_time)

            trace(f"bed ready after cleaning at {self.env.now:.2f}")

    def patient_gets_cancelled(self):
        trace(
            f'{self.group["name"]}-patient {self.identifier} cancelled {self.env.now:.3f}'
        )

    def patient_gets_admitted(self):
        trace(
            f'{self.group["name"]}-patient {self.identifier} admitted {self.env.now:.3f}; '
            + f"waiting time was {self.wait_time:.3f}"
        )

    def patient_gets_discharged(self):
        trace(
            f'{self.group["name"]}-patient {self.identifier} discharged {self.env.now:.3f}'
        )


class MonitoredPatient(CCU_Patients):
    """
    Monitors a Patient.  Inherits from CCU_Patients
    Implemented using the observer design pattern

    A MonitoredPatient notifies its observers that a patient
    process has reached an event
    1. Patient gets admitted in CCU
    2. Patient is discharged from CCU
    """

    def __init__(self, identifier, env, args, group, model):
        """
        Constructor

        Params:
        -------
        identifier : any
        Unique identifier for the patient.

        env : simpy.Environment
        The simulation environment in which the patient operates.

        args : dict or object
        Additional parameters required for patient setup.

        group : any
        Group or category the patient belongs to.

        model : object
        Initial observer to register. Must implement a method
        """
        super().__init__(identifier, env, args, group)
        self._observers = [model]

    def register_observer(self, observer):
        self._observers.append(observer)

    def notify_observers(self, *args, **kwargs):
        for observer in self._observers:
            observer.process_event(*args, **kwargs)

    def patient_gets_cancelled(self):
        super().patient_gets_cancelled()
        # call the patients operator_service_complete method to execute logic
        super().patient_gets_cancelled()

        # passes the patient (self) and a message
        self.notify_observers(self, "patient_gets_cancelled")

    def patient_gets_admitted(self):
        # call the patients operator_service_complete method to execute logic
        super().patient_gets_admitted()

        # passes the patient (self) and a message
        self.notify_observers(self, "patient_gets_admitted")

    def patient_gets_discharged(self):
        # call the patients nurse_service_complete method to execute logic
        super().patient_gets_discharged()

        # passes the patient (self) and a message
        self.notify_observers(self, "patient_gets_discharged")


class CCU_model:
    """
    Simulation model for managing admissions and bed usage in a CCU.

    This class sets up and runs a SimPy-based simulation environment for a
    Coronary Care Unit (CCU). It initialises the simulation resources,
    configures the arrival process, and tracks key operational performance
    metrics such as bed waiting time, bed utilisation, queue length,
    admissions, discharges, and cancellation.
    """

    def __init__(self, args):
        """
        Constructor:
        args : dict or object
            Additional parameters required for patient setup.
        """
        self.env = simpy.Environment()
        self.args = args
        self.init_resources()
        self.arrival_dist(args)
        self.patients = []

        # running performance metrics:
        self.wait_for_CCU_bed = 0.0
        self.bed_util = 0.0
        self.CCU_bed_queue = 0.0

        self.bed_time_used = 0.0
        self.no_cancellations = 0.0
        self.no_admissions = 0
        self.no_discharges = 0

    def init_resources(self):
        """
        Init the number of resources
        and store in the arguments container object
        """
        self.args.beds = simpy.PriorityResource(self.env, capacity=self.args.CCU_beds)

    def arrival_dist(self, args):

        self.group = [
            {
                "name": "emergency",
                "arrival_dist": args.arrival_dist_emerg,
                "los_dist": args.emerg_dist,
                "type": "unplanned",
                "priority": 0,
            },
            {
                "name": "ward",
                "arrival_dist": args.arrival_dist_ward,
                "los_dist": args.ward_dist,
                "type": "unplanned",
                "priority": 0,
            },
            {
                "name": "other",
                "arrival_dist": args.arrival_dist_other,
                "los_dist": args.other_dist,
                "type": "unplanned",
                "priority": 0,
            },
            {
                "name": "xray",
                "arrival_dist": args.arrival_dist_xray,
                "los_dist": args.xray_dist,
                "type": "unplanned",
                "priority": 0,
            },
            {
                "name": "AnE",
                "arrival_dist": args.arrival_dist_AnE,
                "los_dist": args.AnE_dist,
                "type": "unplanned",
                "priority": 0,
            },
            {
                "name": "elective",
                "arrival_dist": args.arrival_dist_elective,
                "los_dist": args.elect_dist,
                "type": "planned",
                "priority": 1,
            },
        ]

    def run(
        self, results_collection_period=DEFAULT_RESULTS_COLLECTION_PERIOD, warm_up=0
    ):
        """
        Conduct a single run of the model in its current
        configuration

        run length = results_collection_period + warm_up

        Parameters:
        ----------
        results_collection_period, float, optional
            default = DEFAULT_RESULTS_COLLECTION_PERIOD

        warm_up, float, optional (default=0)
            length of initial transient period to truncate
            from results.

        Returns:
        --------
            None

        """
        # setup the arrival process
        for group in self.group:
            self.env.process(self.arrivals_generator(group))

        # run
        self.env.run(until=results_collection_period + warm_up)

    def arrivals_generator(self, group):
        """
        IAT is the different distributions from different sources

        Parameters:
        ------
        group: planned/unplanned
        """

        for patient_count in itertools.count(start=1):
            inter_arrival_time = group["arrival_dist"].sample()
            yield self.env.timeout(inter_arrival_time)

            # create a new minor patient and pass in env and args
            new_patient = MonitoredPatient(
                patient_count, self.env, self.args, group, self
            )

            # keep a record of the patient for results calculation
            self.patients.append(new_patient)

            # init the CCU process for this patient
            self.env.process(new_patient.assessment())

    def process_event(self, *args, **kwargs):
        """
        Running calculates each time a Patient process ends
        (when a patient departs the simulation model)

        Params:
        --------
        *args: list
            variable number of arguments. This is useful in case you need to
            pass different information for different events

        *kwargs: dict
            keyword arguments.  Same as args, but you can is a dict so you can
            use keyword to identify arguments.

        """
        patient = args[0]
        msg = args[1]

        # only run if warm up complete
        if self.env.now < self.args.warm_up:
            return

        if msg == "patient_gets_cancelled":
            self.no_cancellations += 1

        if msg == "patient_gets_admitted":
            self.no_admissions += 1
            n = self.no_admissions

            # running calculation for mean waiting time for unpanned patient
            if patient.group["type"] == "unplanned":
                self.wait_for_CCU_bed += (patient.wait_time - self.wait_for_CCU_bed) / n

            # mean CCU bed queue length
            current_q = len(self.args.beds.queue)
            self.CCU_bed_queue += (current_q - self.CCU_bed_queue) / n

        elif msg == "patient_gets_discharged":
            self.no_discharges += 1
            n = self.no_discharges

            # running calc for mean bed utilisation
            self.bed_time_used += patient.total_bed_busy_time

    def run_summary_frame(self):
        # append to results df
        CCU_bed_wait_time = self.wait_for_CCU_bed

        # adjust util calculations for warmup period
        rc_period = self.env.now - self.args.warm_up
        bed_util = self.bed_time_used / (rc_period * self.args.CCU_beds)

        df = pd.DataFrame(
            {
                "1": {
                    "CCU_bed_wait_time": CCU_bed_wait_time,
                    "CCU_bed_queue": self.CCU_bed_queue,
                    "bed_util": bed_util,
                    "n_planned_cancellations": self.no_cancellations,
                    "n_admissions": self.no_admissions,
                    "n_discharges": self.no_discharges,
                }
            }
        )
        df = df.T
        df.index.name = "rep"
        return df


def single_run(
    scenario,
    rc_period=DEFAULT_RESULTS_COLLECTION_PERIOD,
    warm_up=0,
    random_no_set=DEFAULT_RNG_SET,
):
    """
    Perform a single run of the model and return the results

    Parameters:
    -----------

    scenario: Scenario object
        The scenario/paramaters to run

    rc_period: int
        The length of the simulation run that collects results

    warm_up: int, optional (default=0)
        warm-up period in the model.  The model will not collect any results
        before the warm-up period is reached.

    random_no_set: int or None, optional (default=1)
        Controls the set of random seeds used by the stochastic parts of the
        model.  Set to different ints to get different results.  Set to None
        for a random set of seeds.

    Returns:
    --------
        pandas.DataFrame:
        results from single run.
    """

    # set random number set - this controls sampling for the run.
    scenario.set_random_no_set(random_no_set)

    # create an instance of the model
    model = CCU_model(scenario)

    model.run(results_collection_period=rc_period, warm_up=warm_up)

    # run the model
    results_summary = model.run_summary_frame()

    return results_summary


def multiple_replications(
    scenario,
    rc_period=DEFAULT_RESULTS_COLLECTION_PERIOD,
    warm_up=0,
    n_reps=DEFAULT_N_REPS,
    n_jobs=-1,
):
    """
    Perform multiple replications of the model.

    Params:
    ------
    scenario: Scenario
        Parameters/arguments to configurethe model

    rc_period: float, optional (default=DEFAULT_RESULTS_COLLECTION_PERIOD)
        results collection period.
        the number of minutes to run the model beyond warm up
        to collect results

    warm_up: float, optional (default=0)
        initial transient period.  no results are collected in this period

    n_reps: int, optional (default=DEFAULT_N_REPS)
        Number of independent replications to run.

    n_jobs, int, optional (default=-1)
        No. replications to run in parallel.

    Returns:
    --------
    List
    """
    res = Parallel(n_jobs=n_jobs)(
        delayed(single_run)(scenario, rc_period, warm_up, random_no_set=rep)
        for rep in range(n_reps)
    )

    # format and return results in a dataframe
    df_results = pd.concat(res)
    df_results.index = np.arange(1, len(df_results) + 1)
    df_results.index.name = "rep"
    return df_results


class WarmupAuditor:
    """
    Auditor for analysing model behaviour during the warm-up period.

    This class collects time-series data for key performance metrics during
    the initial phase of a simulation run (the warm-up period). It is used
    to assess when the system reaches steady state by tracking cumulative
    trends in metrics such as waiting time and bed utilisation.

    Attributes
    ----------
    env : simpy.Environment
        The simulation environment.
    model : CCU_model
        The simulation model being audited.
    interval : float
        Time interval between successive audit observations.
    wait_for_CCU_bed : list of float
        Recorded values of cumulative waiting time for a CCU bed.
    bed_util : list of float
        Recorded values of bed utilisation over time.

    """

    def __init__(self, model, interval=DEFAULT_WARMUP_AUDIT_INTERVAL):
        """
        Initialise the auditor/monitor for tracking CCU performance metrics.

        Parameters:
        -----------
        model : object
            The simulation model containing the environment (`env`) and system state.

        interval : float, optional
            Time interval between audit checks. Defaults to
            DEFAULT_WARMUP_AUDIT_INTERVAL.

        Attributes:
        -----------
        env : simpy.Environment
            Reference to the simulation environment.

        model : object
            Reference to the simulation model.

        interval : float
            Time interval used for periodic auditing.

        wait_for_CCU_bed : list
            Records waiting times for patients requiring a CCU bed.

        bed_util : list
            Stores CCU bed utilisation data over time.

        CCU_bed_queue : list
            Tracks the queue length for CCU beds.

        Description:
        ------------
        - Stores references to the simulation model and environment.
        - Initialises data structures used to collect performance metrics
          during the simulation.
        """
        self.env = model.env
        self.model = model
        self.interval = interval
        self.wait_for_CCU_bed = []
        self.bed_util = []
        self.CCU_bed_queue = []

    def run(self, rc_period):
        """
        Run the audited model

        Parameters:
        ----------
        rc_period: float
            Results collection period.  Typically this should be many times
            longer than the expected results collection period.

        Returns:
        -------
        None.
        """
        # set up data collection for warmup variables.
        self.env.process(self.audit_model())
        self.model.run(rc_period, 0)

    def audit_model(self):
        """
        Audit the model at the specified intervals
        """
        for i in itertools.count():
            yield self.env.timeout(self.interval)

            # Performance metrics
            # calculate the utilisation metrics
            bed_util = self.model.bed_time_used / (
                self.env.now * self.model.args.CCU_beds
            )

            # store the metrics
            self.wait_for_CCU_bed.append(self.model.wait_for_CCU_bed)
            self.bed_util.append(bed_util)
            self.CCU_bed_queue.append(self.model.CCU_bed_queue)

    def summary_frame(self):
        """
        Return the audit observations in a summary dataframe

        Returns:
        -------
        pd.DataFrame
        """

        df = pd.DataFrame([self.wait_for_CCU_bed, self.bed_util, self.CCU_bed_queue]).T
        df.columns = ["CCU_bed_wait_time", "bed_util", "CCU_bed_queue"]

        return df


def warmup_single_run(
    scenario,
    rc_period,
    interval=DEFAULT_WARMUP_AUDIT_INTERVAL,
    random_no_set=DEFAULT_RNG_SET,
):
    """
    Perform a single simulation run for warm-up analysis.

    This function executes the CCU model over a specified run length
    and collects performance metrics at regular intervals to assess
    system stabilisation (warm-up period).

    Parameters:
    -----------
    scenario : object
        Simulation scenario containing configuration parameters and
        random number control methods.

    rc_period : float
        Total run length (simulation time) for the warm-up run.

    interval : float, optional
        Time interval between successive audit measurements.
        Defaults to DEFAULT_WARMUP_AUDIT_INTERVAL.

    random_no_set : int, optional
        Identifier for the random number stream to ensure reproducibility.
        Defaults to DEFAULT_RNG_SET.

    Returns:
    --------
    pandas.DataFrame
        A summary dataframe containing recorded performance metrics
        (e.g., waiting times, bed utilisation, queue lengths) over time.
    """

    # set random number set - this controls sampling for the run.
    scenario.set_random_no_set(random_no_set)

    # create an instance of the model
    model = CCU_model(scenario)

    # create warm-up model auditor and run
    audit_model = WarmupAuditor(model, interval)
    audit_model.run(rc_period)

    return audit_model.summary_frame()


# example solution
def warmup_analysis(
    scenario,
    rc_period,
    n_reps=DEFAULT_N_REPS,
    interval=DEFAULT_WARMUP_AUDIT_INTERVAL,
    n_jobs=-1,
):
    """
    Perform multiple simulation runs to analyse the warm-up period.

    This function executes several independent replications of the CCU model
    and aggregates key performance metrics over time to assess when the system
    reaches steady state.

    Parameters:
    -----------
    scenario : object
        Simulation scenario containing configuration parameters and random
        number control.

    rc_period : float
        Total run length (simulation time) for each replication.

    n_reps : int, optional
        Number of independent replications to perform.
        Defaults to DEFAULT_N_REPS.

    interval : float, optional
        Time interval between successive audit measurements.
        Defaults to DEFAULT_WARMUP_AUDIT_INTERVAL.

    n_jobs : int, optional
        Number of parallel jobs to run.
        -1 uses all available CPU cores.
        Defaults to -1.

    Returns:
    --------
    dict of pandas.DataFrame
        A dictionary containing time-indexed dataframes for each metric:

        - 'CCU_bed_wait_time': Waiting times for CCU beds
        - 'bed_util': CCU bed utilisation over time
        - 'CCU_bed_queue': Queue length for CCU beds

        Each dataframe:
        - Rows represent audit points (time steps)
        - Columns represent replications (rep_1, rep_2, ..., rep_n)
    """
    res = Parallel(n_jobs=n_jobs)(
        delayed(warmup_single_run)(
            scenario, rc_period, random_no_set=rep, interval=interval
        )
        for rep in range(n_reps)
    )

    # format and return results
    metrics = {"CCU_bed_wait_time": [], "bed_util": [], "CCU_bed_queue": []}

    # preprocess results of each replication
    for rep in res:
        metrics["CCU_bed_wait_time"].append(rep.CCU_bed_wait_time)
        metrics["bed_util"].append(rep.bed_util)
        metrics["CCU_bed_queue"].append(rep.CCU_bed_queue)

    # cast to dataframe
    metrics["CCU_bed_wait_time"] = pd.DataFrame(metrics["CCU_bed_wait_time"]).T
    metrics["bed_util"] = pd.DataFrame(metrics["bed_util"]).T
    metrics["CCU_bed_queue"] = pd.DataFrame(metrics["CCU_bed_queue"]).T

    # index as obs number
    metrics["CCU_bed_wait_time"].index = np.arange(
        1, len(metrics["CCU_bed_wait_time"]) + 1
    )
    metrics["bed_util"].index = np.arange(1, len(metrics["bed_util"]) + 1)
    metrics["CCU_bed_queue"].index = np.arange(1, len(metrics["CCU_bed_queue"]) + 1)

    # obs label
    metrics["CCU_bed_wait_time"].index.name = "audit"
    metrics["bed_util"].index.name = "audit"
    metrics["CCU_bed_queue"].index.name = "audit"

    # columns as rep number
    cols = [f"rep_{i}" for i in range(1, n_reps + 1)]
    metrics["CCU_bed_wait_time"].columns = cols
    metrics["bed_util"].columns = cols
    metrics["CCU_bed_queue"].columns = cols

    return metrics
