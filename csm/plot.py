"""Plotting library for CSM results comparisons."""

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

from csm import get_model


def plot_mass_cost_comparison(
    base_kwargs: dict[str, dict],
    parameterization: dict[str, list],
    component: str,
    parameter_label: str,
    reference_turbines: dict[str, dict] | None = None,
    mass_units: str = "tonnes",
    cost_basis: str = "millions",
    save_name: str | Path | None = None,
    fig_kwargs: dict | None = None,
    scatter_kwargs: dict | None = None,
    plot_kwargs: dict | None = None,
    axis_label_kwargs: dict | None = None,
    model_plot_settings: dict[str, str] | None = None,
    mass_xlim: tuple[float, float] | None = None,
    mass_ylim: tuple[float, float] | None = None,
    cost_xlim: tuple[float, float] | None = None,
    cost_ylim: tuple[float, float] | None = None,
    *,
    return_fig_ax: bool = False,
) -> None | tuple[plt.Figure, tuple[plt.Axes, plt.Axes]]:
    """Removes the missing docstring error."""
    # Plot settings handling
    fig_settings = {"dpi": 200, "figsize": (9, 4)}
    if fig_kwargs is not None:
        fig_settings.update(fig_kwargs)

    # scatter_settings = {} if scatter_kwargs is None else scatter_kwargs
    plot_settings = {} if plot_kwargs is None else plot_kwargs
    axis_label_settings = {} if axis_label_kwargs is None else axis_label_kwargs

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

        formatting = model_plot_settings.get(name, {})
        ax1.plot(parameter_values, mass, label=name, **formatting, **plot_settings)
        ax2.plot(mass, cost, **plot_settings, **formatting, **plot_settings)

    # Reference turbine scatter plots
    # TODO: reference turbine scatter plots

    # Post-plot figure handling
    ax1.legend()

    fig.tight_layout()
    if save_name is not None:
        fig.savefig(save_name, bbox_inches="tight")

    if return_fig_ax:
        return fig, (ax1, ax2)
