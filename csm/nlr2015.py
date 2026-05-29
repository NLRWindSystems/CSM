"""Experimental generic new model generation and 2015 replication."""

from typing import Any

import attrs
from attrs import define, fields

from csm.base_model import CSMBase


base = fields(CSMBase)


@define
class Land2015NLR(CSMBase):
    """Replication of the original CSM model for land-based turbines in 2015. Replicates both the
    Excel and WISDEM CSM implementation.
    """

    rotor_efficiency_max: float = base.rotor_efficiency_max.evolve(default=1.0)
    blade_mass_coeff: float = base.blade_mass_coeff.evolve(default=0.5)
    blade_mass_cost_coeff: float = base.blade_mass_cost_coeff.evolve(default=14.6)
    hub_mass_coeff: float = base.hub_mass_coeff.evolve(default=2.3)
    hub_mass_intercept: float = base.hub_mass_intercept.evolve(default=1320.0)
    hub_mass_cost_coeff: float = base.hub_mass_cost_coeff.evolve(default=3.9)


# TODO: Determine if there is a way to use evolve and make_class together with a workaround
# NOTE: The below does not function while evolve and make_class remain incompatible
# TODO: check this workaround: https://github.com/python-attrs/attrs/issues/637#issuecomment-1019330330


def generate_new_model(name: str, default_map: dict[str, Any]):
    """Creates a custom CSM class with implemented defaults for new cost and scaling relationships.

    Example:
        In the following example we provide the 2015 model's blade defaults to highlight
        a simple, though partial new model generation workflow.

        >>> defaults = {"blade_mass_coeff": 0.5, "blade_mass_cost_coeff": 14.6}
        >>> Partial2015Model = generate_new_model("Partial2015Model", defaults)
        >>> all(Partial2015Model._has_values([*defaults]))


    Args:
        name (str): Name to assign the new class.
        default_map (dict[str, Any]): Dictionary of model attributes and their new default values.

    Raises
    ------
        ValueError: Raised when incompatible model attributes are passed.

    Returns
    -------
        Subclass of ``CSMBase``.
    """
    field_map = {el: f for el in default_map if (f := getattr(base, el)) is not None}
    missing = set(default_map).difference(field_map)
    if missing:
        raise ValueError(f"Incompatible inputs provided: {', '.join(missing)}")
    cls = attrs.make_class(
        name, {k: field_map[k].evolve(default=val) for k, val in default_map.items()}
    )
    return cls
