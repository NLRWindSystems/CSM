"""Experimental generic new model generation and 2015 replication."""

from typing import Any

import attrs
from attrs import define, fields

from csm.models.base_model import CSMBase


base = fields(CSMBase)


@define
class Land2015NLR(CSMBase):
    """Replication of the original CSM model for land-based turbines in 2015. Replicates both the
    Excel and WISDEM CSM implementation. For complete details on all arguments, attributes, and
    methods. please see the :py:class:`csm.models.base_model.CSMBase` documentation. All listed
    attributes below describe the models defaults and any relevant contextual information.

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
        hvac_mass_coeff (float): Not updated in 2015, so is the original 0.08.
        hvac_mass_cost_coeff (float): Not updated in 2015, so is the original 124 USD/kg.
        platforms_mass_coeff (float): Not updated in 2015, so the original 0.125.
        crane_mass (float): Not updated in 2015, so the original 3000.
        platforms_mass_cost_coeff (float): Not updated in 2015, so the original 17.1.
        crane_cost (float): Not updated in 2015, so the original 12000.
    """

    efficiency_max: float = base.efficiency_max.evolve(default=1.0)
    blade_mass_coeff: float = base.blade_mass_coeff.evolve(default=0.5)
    blade_mass_cost_coeff: float = base.blade_mass_cost_coeff.evolve(default=14.6)
    hub_mass_coeff: float = base.hub_mass_coeff.evolve(default=2.3)
    hub_mass_intercept: float = base.hub_mass_intercept.evolve(default=1320.0)
    hub_mass_cost_coeff: float = base.hub_mass_cost_coeff.evolve(default=3.9)
    pitch_bearing_mass_coeff: float = base.pitch_bearing_mass_coeff.evolve(default=0.1295)
    pitch_bearing_mass_intercept: float = base.pitch_bearing_mass_intercept.evolve(default=491.31)
    bearing_housing_fraction: float = base.bearing_housing_fraction.evolve(default=0.3280)
    mass_sys_offset: float = base.mass_sys_offset.evolve(default=555.0)
    pitch_system_mass_cost_coeff: float = base.pitch_system_mass_cost_coeff.evolve(default=22.1)
    spinner_mass_coeff: float = base.spinner_mass_coeff.evolve(default=15.5)
    spinner_mass_intercept: float = base.spinner_mass_intercept.evolve(default=-980.0)
    spinner_mass_cost_coeff: float = base.spinner_mass_cost_coeff.evolve(default=11.1)
    lss_mass_coeff: float = base.lss_mass_coeff.evolve(default=13.0)
    lss_mass_exp: float = base.lss_mass_exp.evolve(default=0.65)
    lss_mass_intercept: float = base.lss_mass_intercept.evolve(default=775.0)
    lss_mass_cost_coeff: float = base.lss_mass_cost_coeff.evolve(default=11.9)
    bearing_mass_coeff: float = base.bearing_mass_coeff.evolve(default=0.0001)
    bearing_mass_exp: float = base.bearing_mass_exp.evolve(default=3.5)
    bearing_mass_cost_coeff: float = base.bearing_mass_cost_coeff.evolve(default=4.5)
    gearbox_torque_density: float = base.gearbox_torque_density.evolve(default=200)
    gearbox_torque_cost: float = base.gearbox_torque_cost.evolve(default=50)
    brake_mass_coeff: float = base.gearbox_torque_cost.evolve(default=0.00122)
    hss_mass_coeff: float = base.hss_mass_coeff.evolve(default=0.19894)
    hss_mass_cost_coeff: float = base.hss_mass_cost_coeff.evolve(default=6.8)
    generator_mass_coeff: float = base.generator_mass_coeff.evolve(default=2.3)
    generator_mass_intercept: float = base.generator_mass_intercept.evolve(default=3400)
    generator_mass_cost_coeff: float = base.generator_mass_cost_coeff.evolve(default=12.4)
    bedplate_mass_exp: float = base.bedplate_mass_exp.evolve(default=2.2)
    bedplate_mass_cost_coeff: float = base.bedplate_mass_cost_coeff.evolve(default=2.9)
    yaw_system_mass_coeff: float = base.yaw_system_mass_coeff.evolve(default=0.0009)
    yaw_system_mass_exp: float = base.yaw_system_mass_exp.evolve(default=3.314)
    yaw_system_mass_cost_coeff: float = base.yaw_system_mass_cost_coeff.evolve(default=8.3)
    hvac_mass_coeff: float = base.hvac_mass_coeff.evolve(default=0.08)
    hvac_mass_cost_coeff: float = base.hvac_mass_cost_coeff.evolve(default=124)
    nacelle_cover_mass_coeff: float = base.nacelle_cover_mass_coeff.evolve(default=1.2817)
    nacelle_cover_mass_intercept: float = base.nacelle_cover_mass_intercept.evolve(default=428.19)
    nacelle_cover_mass_cost_coeff: float = base.nacelle_cover_mass_cost_coeff.evolve(default=5.7)
    platform_mainframe_mass_coeff: float = base.platform_mainframe_mass_coeff.evolve(default=0.125)
    has_crane: bool = base.has_crane.evolve(default=False)
    crane_mass: float = base.crane_mass.evolve(default=3000)
    platform_mainframe_mass_cost_coeff: float = base.platform_mainframe_mass_cost_coeff.evolve(
        default=17.1
    )
    crane_cost: float = base.crane_cost.evolve(default=12000.0)
    transformer_mass_coeff: float = base.transformer_mass_coeff.evolve(default=1.9150)
    transformer_mass_intercept: float = base.transformer_mass_intercept.evolve(default=1910.0)
    transformer_mass_cost_coeff: float = base.transformer_mass_cost_coeff.evolve(default=18.8)
    tower_mass_coeff: float = base.tower_mass_coeff.evolve(default=19.828)
    tower_mass_exp: float = base.tower_mass_exp.evolve(default=2.0282)
    tower_mass_cost_coeff: float = base.tower_mass_cost_coeff.evolve(default=2.9)


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
            yield name, field.evolve(default=default_map)

    def reset_defaults(base_fields: tuple[attrs.Attribute]):
        return dict(gen_fields(base_fields))

    return attrs.make_class(name, reset_defaults(base), bases=(CSMBase,))
