# %%
from csm import CSM
from csm import run_parameter_config
import pandas as pd
import seaborn as sns
import itertools

# %%
params = {
    "rotor_efficiency_max": 1.0,
    "tip_speed_max": 90,
    "is_direct_drive": False,
    "offshore": {
        "model": ["Empirical2020", "Empirical2030", "Empirical2024Offshore"],
        "rotor_diameter": [[200, 300], 11],
        "turbine_rating_MW": [[12, 25], 13],
    },
    "onshore": {
        "model": ["Empirical2020", "Empirical2030", "Empirical2024Onshore"],
        "rotor_diameter": [[120, 180], 7],
        "turbine_rating_MW": [[3.0, 7.2], 21],
    },
}

result = run_parameter_config({"parameters": params})
models, result = zip(*result)
result, _ = zip(*result)
result = pd.concat(result, keys=models, names=["model"])
result = result.reset_index("model", drop=False)

param = "blade_mass"
dependent_vars = set(
    itertools.chain.from_iterable(
        CSM.from_name(n).required_inputs_to_calculate(param) for n in models
    )
)

# %%
sns.relplot(
    data=result.loc[
        (result["model"] != "Empirical2024Onshore") & (result["rotor_diameter"] == 280)
        | (result["model"] != "Empirical2024Offshore")
        & (result["rotor_diameter"] == 150)
    ],
    kind="line",
    x="turbine_rating_MW",
    y="gearbox_mass",
    hue="model",
    col="scenario",
    aspect=1,
    height=5,
    facet_kws=dict(
        sharex=False,
        sharey=False,
    ),
)

# %%

sns.relplot(
    data=result.loc[
        (result["model"] != "Empirical2024Onshore") & (result["rotor_diameter"] == 280)
        | (result["model"] != "Empirical2024Offshore")
        & (result["rotor_diameter"] == 150)
    ],
    kind="line",
    x="turbine_rating_MW",
    y="gearbox_cost",
    hue="model",
    col="scenario",
    aspect=1,
    height=5,
    facet_kws=dict(
        sharex=False,
        sharey=False,
    ),
)

# %%

sns.relplot(
    data=result,
    kind="line",
    x="rotor_diameter",
    y="blade_mass",
    col="scenario",
    hue="model",
    aspect=1,
    height=5,
    facet_kws=dict(
        sharex=False,
        sharey=False,
    ),
)

# %%
