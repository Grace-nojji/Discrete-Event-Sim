# Discrete-Event-Sim

A discrete-event simulation project for modelling patient flow and bed usage in a Critical Care Unit (CCU).

- **Output Analysis** in `analysis/`
- **Distributions for Modelling IAT and Stay Time** in `distribution/`
- **Critical Care Unit Model (basic and prepared for warm-up** in `model/`
- **Testing of the functionalities** in `test/`, 

## Repository structure

```text
Discrete-Event-Sim/
├── analysis/
├── binder/
├── distribution/
├── model/
├── test/
├── README.md
├── setup.py
└── test.pdf
```

## File-by-file guide

### Root

#### `README.md`
The current top-level README appears to be a short placeholder with the project title and a brief description only. It should ideally point readers to the CCU model, setup steps, and how to run tests and replications.

#### `setup.py`
Project packaging/config metadata. The file defines a setuptools build backend and identifies the package as `DES` version `0.1.0`.

#### `test.pdf`
A PDF artifact stored at the repository root. Its purpose is not clear from the repository tree alone, so it is likely a report, export, or supplementary document.

---

### `analysis/`
This folder contains outputs used to inspect model behaviour and present results.

#### `analysis/output_analysis.ipynb`
A Jupyter notebook for post-run analysis. Based on the surrounding output files, it likely loads replication results and produces plots for waiting times, queue lengths, utilisation, and warm-up diagnostics.

#### `analysis/ccu_boxplots.png`
Static figure showing boxplots for one or more CCU performance metrics.

#### `analysis/rep_CCU_bed_queue..png`
Plot of replicated CCU bed queue results.

#### `analysis/rep_CCU_util.png`
Plot of CCU bed utilisation across replications or scenarios.

#### `analysis/rep_CCU_wait.png`
Plot of CCU bed waiting time across replications or scenarios.

#### `analysis/warm_up.png`
Warm-up analysis figure, likely used to assess when the simulation reaches steady state.

#### `analysis/.ipynb_checkpoints/`
Automatically generated Jupyter checkpoint files. These are editor artifacts rather than source files.

---

### `binder/`
This folder supports reproducible execution in Binder/Jupyter environments.

#### `binder/environment.yml`
A Conda environment definition named `hds_stoch`. It pins Python `3.11.13` and includes the modelling and analysis stack needed for the project, including `simpy`, `sim-tools`, `scipy`, `scikit-learn`, `statsmodels`, `plotly`, and test dependencies such as `pytest`.

#### `binder/.ipynb_checkpoints/`
Auto-generated notebook checkpoints.

---

### `distribution/`
This folder contains reusable distribution code and empirical data used by the CCU model.

#### `distribution/__init__.py`
Empty package marker file so Python treats `distribution/` as an importable module.

#### `distribution/bin.csv`
Empirical input data used to build grouped continuous empirical distributions. The companion code indicates the file contains at least `lower_bound`, `upper_bound`, and `y` columns, where `y` supplies frequencies or weights for each bin.

#### `distribution/distributions.py`
Helper module defining custom distribution wrapper classes used by the simulation:

- `Exponential`: wraps NumPy exponential sampling and stores the mean and RNG seed.
- `Lognormal`: converts a requested lognormal mean and standard deviation into the underlying normal parameters (`mu`, `sigma`) before sampling.
- `Normal`: samples from a normal distribution and resamples until the value is non-negative.

These classes make the model configuration more readable and keep random-number control consistent.

#### `distribution/empirical.py`
Factory/helper for creating an empirical distribution from `bin.csv`. The module reads the CSV and exposes `make_group_dist(...)`, which returns a `GroupedContinuousEmpirical` distribution using the bin lower bounds, upper bounds, and frequencies.

#### `distribution/empirical_freq.ipynb`
Notebook used to derive, inspect, or validate the empirical frequency distribution stored in `bin.csv`.

#### `distribution/__pycache__/`
Compiled Python cache files generated during execution.

#### `distribution/.ipynb_checkpoints/`
Auto-generated notebook checkpoints.

---

### `model/`
This is the core of the repository and contains the full CCU simulation model.

#### `model/__init__.py`
Empty package marker file for the `model/` package.

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

This is the most important file in the repository and the place to start if you want to understand or modify the simulation logic.

#### `model/__pycache__/`
Compiled Python cache files.

#### `model/.ipynb_checkpoints/`
Notebook checkpoint artifacts.

---

### `test/`
This folder contains automated tests and test data for the CCU model.

#### `test/__init__.py`
Empty package marker file for the test package.

#### `test/bin.csv`
CSV test fixture, likely used as controlled input data for empirical-distribution-related testing.

#### `test/pytest_ccu.py`
Pytest-based regression and behaviour tests for the CCU simulation.

The file defines:

- `ConstantDist`, a deterministic distribution used to remove randomness during tests.
- `make_test_scenario(...)`, which builds stable scenarios with controlled arrivals and lengths of stay.
- `run_model(...)`, a helper that runs the model and returns the first summary row.

The tests check several important model behaviours, including:

- more beds reduce queue length,
- more beds reduce waiting time,
- more beds do not increase utilisation under the same demand,
- very large bed capacity leads to zero queue and zero wait,
- zero beds raises an error, and
- high unplanned demand increases planned-patient cancellations.

These tests are especially useful because they validate the model with deterministic inputs rather than relying on noisy stochastic outputs.

#### `test/__pycache__/`
Compiled Python cache files.

#### `test/.ipynb_checkpoints/`
Auto-generated notebook checkpoints.

---

### Autogenerated / non-source folders

#### `__pycache__/`
Python bytecode cache directories. Safe to ignore in most documentation.

#### `.ipynb_checkpoints/`
Jupyter autosave checkpoints. Also safe to ignore in most documentation.

## Suggested improvements

To make the repository easier to use, the main README could be expanded with:

1. a short project overview and modelling objective,
2. installation instructions using `binder/environment.yml`,
3. example code for running `single_run()` and `multiple_replications()`,
4. instructions for running `pytest`, and
5. links to the analysis notebook and generated plots.

## Notes

A few entries above, especially notebooks, plots, and `test.pdf`, were described from their filenames and surrounding repository context rather than full file contents. The Python modules and package metadata were summarised from the visible code in the repository.
