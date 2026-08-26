"""Plotting library for CSM results comparisons."""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

from csm import get_model


def plot_mass_cost_comparison(
    base_kwargs: dict[str, dict],
    parameterization: dict[str, list],
    component: str,
    parameter_label: str,
    reference_turbines: dict[str, dict] | None = None,
    background_data: pd.DataFrame | None = None,
    mass_units: str = "tonnes",
    cost_basis: str = "millions",
    save_name: str | Path | None = None,
    fig_kwargs: dict | None = None,
    legend_kwargs: dict | None = None,
    reference_scatter_kwargs: dict | None = None,
    background_scatter_kwargs: dict | None = None,
    plot_kwargs: dict | None = None,
    axis_label_kwargs: dict | None = None,
    model_plot_settings: dict[str, str] | None = None,
    turbine_scatter_settings: dict[str, str] | None = None,
    mass_xlim: tuple[float, float] | None = None,
    mass_ylim: tuple[float, float] | None = None,
    cost_xlim: tuple[float, float] | None = None,
    cost_ylim: tuple[float, float] | None = None,
    *,
    return_fig_ax: bool = False,
) -> None | tuple[plt.Figure, tuple[plt.Axes, plt.Axes]]:
    """Removes the missing docstring error."""
    # Handle None defaults for expected non-None types
    fig_settings = {"dpi": 200, "figsize": (9, 4)}
    if fig_kwargs is not None:
        fig_settings.update(fig_kwargs)

    legend_settings = {}
    if legend_kwargs is not None:
        legend_settings.update(legend_kwargs)

    reference_scatter_settings = {}
    if reference_scatter_kwargs is not None:
        reference_scatter_settings.update(reference_scatter_kwargs)

    background_scatter_settings = {}
    if background_scatter_kwargs is not None:
        background_scatter_settings.update(background_scatter_kwargs)

    plot_settings = {}
    if plot_kwargs is not None:
        plot_settings.update(plot_kwargs)

    axis_label_settings = {}
    if axis_label_kwargs is not None:
        axis_label_settings.update(axis_label_kwargs)

    if turbine_scatter_settings is None:
        turbine_scatter_settings = {}

    if model_plot_settings is None:
        model_plot_settings = {}

    # Create models and results
    metrics = [f"{component}_mass", f"{component}_cost"]
    models = {name: get_model(name) for name in base_kwargs}
    parameter = next(iter(parameterization))
    if len(parameterization) > 1:
        msg = f"'parameterization' has multiple entries, only '{parameter}' will be used."
        warnings.warn(msg, UserWarning, stacklevel=1)

    results = {
        name: model.parameterize_subset(base_kwargs[name], parameterization, metrics)
        for name, model in models.items()
    }

    # Handle mass and cost units
    match mass_units.lower():
        case "kg":
            label_units = "kg"
            mass_scale = 1
        case "tonnes":
            mass_scale = 1 / 1e3
            label_units = "Metric Tonnes"
        case _:
            raise ValueError("'mass_units' should be one of 'kg' or 'tonnes'.")

    match cost_basis.lower():
        case "dollars":
            label_cost = "USD"
            cost_scale = 1
        case "thousands":
            cost_scale = 1 / 1e3
            label_cost = "Thousands USD"
        case "millions":
            cost_scale = 1 / 1e6
            label_cost = "Millions USD"
        case _:
            raise ValueError("'cost_basis' should be one of 'dollars', 'thousands', 'millions'.")

    mass_label = f"{component.title()} Mass ({label_units})"
    cost_label = f"{component.title()} Cost ({label_cost})"

    # Plotting setup
    fig = plt.figure(**fig_settings)
    ax1, ax2 = fig.subplots(1, 2)

    ax1.set_xlabel(parameter_label, **axis_label_settings)
    ax1.set_ylabel(mass_label, **axis_label_settings)
    ax2.set_xlabel(mass_label, **axis_label_settings)
    ax2.set_ylabel(cost_label, **axis_label_settings)

    ax1.set_xlim(mass_xlim)
    ax1.set_ylim(mass_ylim)
    ax2.set_xlim(cost_xlim)
    ax2.set_ylim(cost_ylim)

    for ax in (ax1, ax2):
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        ax.grid()
        ax.set_axisbelow(True)

    # Model line plots
    for name, _results in results.items():
        parameter_values = _results.columns
        mass = _results.loc[f"{component}_mass"] * mass_scale
        cost = _results.loc[f"{component}_cost"] * cost_scale

        formatting = plot_settings | model_plot_settings.get(name, {})
        ax1.plot(parameter_values, mass, label=name, **formatting)
        ax2.plot(mass, cost, **plot_settings, **formatting)

    # Background scatter points
    if background_data is not None:
        scatter_data = background_data.loc[:, [parameter, *metrics]]
        parameter_values = scatter_data[parameter].to_numpy()
        mass = scatter_data[metrics[0]].to_numpy() * mass_scale
        cost = scatter_data[metrics[1]].to_numpy() * cost_scale
        ax1.scatter(
            parameter_values, mass, **({"label": "Empirical Data"} | background_scatter_settings)
        )
        ax2.scatter(mass, cost, **background_scatter_settings)

    # Reference turbine scatter plots
    # TODO: reference turbine scatter plots
    if reference_turbines is None:
        reference_turbines = {}
    for turbine, config in reference_turbines.items():
        if (parameter_value := config.get(parameter)) is None:
            continue
        turbine_models = {
            name: model.from_dict(config, partial=True) for name, model in models.items()
        }
        [model.calculate(*metrics) for model in turbine_models.values()]

        parameter_values = [parameter_value] * len(turbine_models)
        mass = [getattr(model, f"{component}_mass") for model in turbine_models.values()]
        cost = [getattr(model, f"{component}_cost") for model in turbine_models.values()]
        mass = np.array(mass) * mass_scale
        cost = np.array(cost) * cost_scale

        formatting = reference_scatter_settings | turbine_scatter_settings.get(turbine, {})
        ax1.scatter(parameter_values, mass, label=turbine, **formatting)
        ax2.scatter(mass, cost, **formatting)

    # TODO: background data scatter for industry data points

    # Post-plot figure handling
    fig.legend(**legend_settings)

    fig.tight_layout()
    if save_name is not None:
        fig.savefig(save_name, bbox_inches="tight")

    if return_fig_ax:
        return fig, (ax1, ax2)
