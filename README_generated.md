# Critical Care Unit DES Simulation

A discrete-event simulation project for modelling patient flow and bed usage in a Critical Care Unit (CCU).

- **Output Analysis** in `analysis/`
- **Distributions for Modelling IAT and Stay Time** in `distribution/`
- **Critical Care Unit Model (basic) and (prepared for warm-up)** in `model/`
- **Testing of the functionalities** in `test/`, 

## Repository structure

```text
Discrete-Event-Sim/
├── analysis/
 ├── output_analysis.ipynb
├── binder/
 ├── environment.yml
├── distribution/
 ├── bin.csv
 ├── distributions.py
 ├── empirirical.py
 ├── empirical_freq.ipynb
├── model/
 ├── CriticalCareUnit.py
 ├── basic_model.ipynb
├── test/
 ├── pytest_ccu.py
├── README.md
├── setup.py
└── test.pdf
```
---

### `analysis/`
This folder contains outputs used to inspect model behaviour and present results.

#### `analysis/output_analysis.ipynb`
A Jupyter notebook for post-run analysis.

---

### `binder/`
This folder supports reproducible execution in Binder/Jupyter environments.

#### `binder/environment.yml`
A Conda environment definition named `hds_stoch`. It pins Python `3.11.13` and includes the modelling and analysis stack needed for the project, including `simpy`, `sim-tools`, `scipy`, `scikit-learn`, `statsmodels`, `plotly`, and test dependencies such as `pytest`.

---

### `distribution/`
This folder contains reusable distribution code and empirical data used by the CCU model.

#### `distribution/bin.csv`
Empirical input data used to build grouped continuous empirical distributions from the literature (Griffiths et al)

#### `distribution/distributions.py`
Helper module defining custom distribution wrapper classes used by the simulation:

- `Exponential`: wraps NumPy exponential sampling and stores the mean and RNG seed.
- `Lognormal`: converts a requested lognormal mean and standard deviation into the underlying normal parameters (`mu`, `sigma`) before sampling.
- `Normal`: samples from a normal distribution and resamples until the value is non-negative.

#### `distribution/empirical.py`
Factory/helper for creating an empirical distribution from `bin.csv`. The module reads the CSV and exposes `make_group_dist(...)`, which returns a `GroupedContinuousEmpirical` distribution using the bin lower bounds, upper bounds, and frequencies.

#### `distribution/empirical_freq.ipynb`
Notebook used to derive the empirical distribution stored in `bin.csv`.

 
---

### `model/`
This is the core of the repository and contains the full CCU simulation model

#### `model/CriticalCareUnit.py`
Main simulation module. This file implements the CCU model itself using **SimPy** and includes scenario setup, patient behaviour, replication helpers, and warm-up analysis tools.

Key components include:

- **`Scenario`**
  - Stores simulation parameters such as the number of CCU beds and warm-up length.
  - Initialises random-number streams for reproducibility.
  - Builds arrival and length-of-stay distributions for multiple patient sources.

- **Patient flow classes**
  - `CCU_Patients` models the lifecycle of an individual patient.
  - The `assessment()` process distinguishes between:
    - **unplanned patients**, who queue for a bed if necessary, and
    - **planned/elective patients**, who may be cancelled if no bed is available on arrival.
  - The patient process includes admission, stay, discharge, and bed cleaning logic.

- **`MonitoredPatient`**
  - Extends `CCU_Patients` using an observer-style design.
  - Notifies the model when key events occur, including admission, discharge, and cancellation.

- **`CCU_model`**
  - Creates the SimPy environment and a `PriorityResource` representing CCU beds.
  - Defines patient source groups including `emergency`, `ward`, `other`, `xray`, `AnE`, and `elective`.
  - Generates arrivals for each group.
  - Tracks operational metrics such as:
    - mean waiting time for a CCU bed,
    - CCU bed queue length,
    - bed utilisation,
    - planned cancellations,
    - admissions, and
    - discharges.
  - `run_summary_frame()` returns these outputs as a Pandas DataFrame.

- **Experiment helpers**
  - `single_run(...)` executes one simulation run.
  - `multiple_replications(...)` executes many independent runs in parallel and concatenates the results.

- **Warm-up analysis tools**
  - `WarmupAuditor` samples key metrics over time.
  - `warmup_single_run(...)` and `warmup_analysis(...)` support identifying an appropriate warm-up period before collecting steady-state results.

---

### `test/`
This folder contains automated tests and test data for the CCU model.

#### `test/__init__.py`
Empty package marker file for the test package.

#### `test/bin.csv`
CSV test fixture, likely used as controlled input data for empirical-distribution-related testing.

#### `test/pytest_ccu.py`
Testing file for CCU functionalities
- more beds reduce queue length,
- more beds reduce waiting time,
- more beds do not increase utilisation under the same demand,
- very large bed capacity leads to zero queue and zero wait,
- zero beds raises an error, and
- high unplanned demand increases planned-patient cancellations.

---
