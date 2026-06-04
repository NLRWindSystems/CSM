"""Experimental generic new model generation and 2015 replication."""

from typing import Any

import attrs
from attrs import define, fields

from csm.base_model import CSMBase


base = fields(CSMBase)


@define
class Land2015NLR(CSMBase):
    """Replication of the original CSM model for land-based turbines in 2015. Replicates both the
    Excel and WISDEM CSM implementation. For complete details on all arguments, attributes, and
    methods. please see the :py:class:`csm.base_model.CSMBase` documentation. All listed attributes
    below describe the models defaults and any relevant contextual information.

    Attributes:
    ----------
        sample (float): description. Set to 1.0.
        pitch_system_mass_cost_coeff (float): Not updated in 2015, so is the original $22.1 USD/kg.
        gearbox_torque_density (float): In 2024, modern 5-7MW gearboxes are able to reach 200 Nm/kg.
        gearbox_torque_cost (float): In 2024, modern 5-7MW gearboxes cost approximately $50/kNm.
        pitch_bearing_mass_coeff (float): Not updated in 2015, so is the original 0.1295.
        pitch_bearing_mass_intercept (float): Not updated in 2015, so is the original 491.31 kg.
        bearing_housing_fraction (float): Not updated in 2015, so is the original 0.3280.
        mass_sys_offset (float): Not updated in 2015, so is the original 555.0 kg.
        brake_mass_cost_coeff (float): In 2020, updated to $3.6254 USD/kg. Regression based sizing
            derived by J.Keller under FOA 1981 support project.
    """

    efficiency_max: float = base.efficiency_max.evolve(default=1.0, init=False)
    blade_mass_coeff: float = base.blade_mass_coeff.evolve(default=0.5, init=False)
    blade_mass_cost_coeff: float = base.blade_mass_cost_coeff.evolve(default=14.6, init=False)
    hub_mass_coeff: float = base.hub_mass_coeff.evolve(default=2.3, init=False)
    hub_mass_intercept: float = base.hub_mass_intercept.evolve(default=1320.0, init=False)
    hub_mass_cost_coeff: float = base.hub_mass_cost_coeff.evolve(default=3.9, init=False)
    pitch_bearing_mass_coeff: float = base.pitch_bearing_mass_coeff.evolve(
        default=0.1295, init=False
    )
    pitch_bearing_mass_intercept: float = base.pitch_bearing_mass_intercept.evolve(
        default=491.31, init=False
    )
    bearing_housing_fraction: float = base.bearing_housing_fraction.evolve(
        default=0.3280, init=False
    )
    mass_sys_offset: float = base.mass_sys_offset.evolve(default=555.0, init=False)
    spinner_mass_coeff: float = base.spinner_mass_coeff.evolve(default=15.5, init=False)
    spinner_mass_intercept: float = base.spinner_mass_intercept.evolve(default=-980.0, init=False)
    spinner_mass_cost_coeff: float = base.spinner_mass_cost_coeff.evolve(default=11.1, init=False)
    lss_mass_coeff: float = base.lss_mass_coeff.evolve(default=13.0, init=False)
    lss_mass_exp: float = base.lss_mass_exp.evolve(default=0.65, init=False)
    lss_mass_intercept: float = base.lss_mass_intercept.evolve(default=775.0, init=False)
    lss_mass_cost_coeff: float = base.lss_mass_cost_coeff.evolve(default=11.9, init=False)
    bearing_mass_coeff: float = base.bearing_mass_coeff.evolve(default=0.0001, init=False)
    bearing_mass_exp: float = base.bearing_mass_exp.evolve(default=3.5, init=False)
    bearing_mass_cost_coeff: float = base.bearing_mass_cost_coeff.evolve(default=4.5, init=False)
    gearbox_torque_density: float = base.gearbox_torque_density.evolve(default=200, init=False)
    gearbox_torque_cost: float = base.gearbox_torque_cost.evolve(default=50, init=False)
    brake_mass_coeff: float = base.gearbox_torque_cost.evolve(default=0.00122, init=False)
    hss_mass_coeff: float = base.hss_mass_coeff.evolve(default=0.19894, init=False)
    hss_mass_cost_coeff: float = base.hss_mass_cost_coeff.evolve(default=6.8, init=False)


# TODO: Determine if there is a way to use evolve and make_class together with a workaround
# NOTE: The below does not function while evolve and make_class remain incompatible


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

    Raises:
    ------
        ValueError: Raised when incompatible model attributes are passed.

    Returns:
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


# TODO: check this workaround: https://github.com/python-attrs/attrs/issues/637#issuecomment-1019330330  # noqa: E501
# NOTE: Same issue with _CountingAttr _default vs default, so likely not worth continuing down this path  # noqa: E501
def generate_model(name: str, default_map: dict[str, Any]):  # noqa: D103
    def gen_fields(base_fields):
        for field in base_fields:
            name = field.name
            if (default := default_map.get(name)) is None:  # noqa: F841
                yield name, field
                continue
            yield name, field.evolve(default=default_map, init=False)

    def reset_defaults(base_fields: tuple[attrs.Attribute]):
        return dict(gen_fields(base_fields))

    return attrs.make_class(name, reset_defaults(base), bases=(CSMBase,))
