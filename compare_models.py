# %%
from csm import CSM
from csm import run_config
import pandas as pd
import seaborn as sns
import itertools


# %%
params = {
    "rotor_efficiency_max": 1.0,
    "tip_speed_max": 90,
    "num_bearings": 2,
    "water_depth": 30,
    "hub_height": 150,
    "offshore": {
        "rotor_diameter": [[200, 300], 11],
        "2020": {
            "model": ["Empirical2020", "Empirical2030"],
            "turbine_rating_MW": [[12, 25], 14],
        },
        "2024": {
            "model": "Empirical2024Offshore",
            "turbine_rating_MW": [[12, 25], 14],
        },
        # "2015": {
        #     "model": "Replicate2015",
        #     "turbine_class": 2,
        #     "turbine_rating_kW": [[12_000, 25_000], 13],
        #     "blade_has_carbon": [True, False],
        # },
    },
    "onshore": {
        "rotor_diameter": [[120, 180], 7],
        "2020": {
            "model": ["Empirical2020", "Empirical2030"],
            "turbine_rating_MW": [[3.0, 7.2], 21],
        },
        "2024": {
            "model": "Empirical2024Onshore",
            "turbine_rating_MW": [[3.0, 7.2], 21],
        },
        # "2015": {
        #     "model": "Replicate2015",
        #     "turbine_class": 2,
        #     "turbine_rating_kW": [[3_000, 7_200], 21],
        #     "blade_has_carbon": [True, False],
        # },
    },
}

result = run_config({"parameters": params})
models, result = zip(*result)
result, _ = zip(*result)
result = pd.concat(result, keys=models, names=["model"])
result = result.reset_index("model", drop=False)

if "turbine_rating_kW" in result.columns:
    result["turbine_rating_MW"] = result["turbine_rating_MW"].fillna(
        result.pop("turbine_rating_kW") / 1000.0
    )
result["offshore"] = result["scenario"].str.startswith("offshore")

param = "blade_mass"
dependent_vars = set(
    itertools.chain.from_iterable(
        CSM.from_name(n).required_inputs_to_calculate(param) for n in models
    )
)
# %%
df_plot = result.loc[
    ((result["offshore"]) & (result["rotor_diameter"] == 280))
    | ((~result["offshore"]) & (result["rotor_diameter"] == 150)),
]

plot_args = dict(
    aspect=1,
    height=5,
    facet_kws=dict(
        sharex=False,
        sharey=False,
    ),
)

# %%

gearbox_mass = sns.relplot(
    data=df_plot,
    kind="line",
    x="turbine_rating_MW",
    y="gearbox_mass",
    hue="model",
    col="offshore",
    **plot_args,
)
gearbox_mass.figure.suptitle("Gearbox Mass")

# %%

gearbox_cost = sns.relplot(
    data=df_plot,
    kind="line",
    x="turbine_rating_MW",
    y="gearbox_cost",
    hue="model",
    col="offshore",
    **plot_args,
)
gearbox_cost.figure.suptitle("Gearbox Cost")

# %%

blade_mass = sns.relplot(
    # data=result.fillna({"blade_has_carbon": "?"}),
    data=result,
    kind="line",
    x="rotor_diameter",
    y="blade_mass",
    col="offshore",
    hue="model",
    # style="blade_has_carbon",
    **plot_args,
)
blade_mass.figure.suptitle("Blade Mass")

# %%

blade_cost = sns.relplot(
    # data=result.fillna({"blade_has_carbon": "?"}),
    data=result,
    kind="line",
    x="rotor_diameter",
    y="blade_cost",
    col="offshore",
    hue="model",
    # style="blade_has_carbon",
    **plot_args,
)
blade_cost.figure.suptitle("Blade Cost")

# %%

nacelle_mass = sns.relplot(
    data=result.loc[
        (result["offshore"] & (result["turbine_rating_MW"] == 15))
        | (~result["offshore"] & (result["turbine_rating_MW"] == 3.0))
    ],
    kind="line",
    x="rotor_diameter",
    y="nacelle_mass",
    col="offshore",
    hue="model",
    **plot_args,
)
nacelle_mass.figure.suptitle("Nacelle Mass")

# %%

nacelle_cost = sns.relplot(
    data=result.loc[
        (result["offshore"] & (result["turbine_rating_MW"] == 15))
        | (~result["offshore"] & (result["turbine_rating_MW"] == 3.0))
    ],
    kind="line",
    x="rotor_diameter",
    y="nacelle_cost",
    col="offshore",
    hue="model",
    **plot_args,
)
nacelle_cost.figure.suptitle("Nacelle Cost")

# %%

tower_mass = sns.relplot(
    data=result,
    kind="line",
    x="rotor_diameter",
    y="tower_mass",
    col="offshore",
    hue="model",
    **plot_args,
)
tower_mass.figure.suptitle("Tower Mass")

# %%

tower_cost = sns.relplot(
    data=result,
    kind="line",
    x="rotor_diameter",
    y="tower_cost",
    col="offshore",
    hue="model",
    **plot_args,
)
tower_cost.figure.suptitle("Tower Cost")


# %%
