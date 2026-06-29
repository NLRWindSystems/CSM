"""Provides the ``CSMBase`` base model, which serves as the basis for all inputs and outputs
that subsequent subclasses will use.

Please see the :ref:`../../docs/user_guide/new_models` for creating new models to implement
model-specific defaults while maintaining all input validation, metadata, and functionality from
the base model.


"""

import math
from copy import deepcopy
from typing import Any
from functools import cached_property
from itertools import product, zip_longest
from collections.abc import Generator

import numpy as np
import pandas as pd
import networkx as nx
from attrs import Attribute, field, define, fields, validators

from csm.models.utils import create_field


parameter_map = {
    "blade_mass": ("rotor_diameter", "turbine_class", "blade_has_carbon", "blade_mass_coeff"),
    "blade_cost": ("blade_mass", "blade_mass_cost_coeff"),
    "hub_mass": ("blade_mass", "hub_mass_coeff", "hub_mass_intercept"),
    "hub_cost": ("hub_mass", "hub_mass_cost_coeff"),
    "pitch_system_mass": (
        "num_blades",
        "pitch_bearing_mass_coeff",
        "blade_mass",
        "pitch_bearing_mass_intercept",
        "bearing_housing_fraction",
        "mass_sys_offset",
    ),
    "pitch_system_cost": ("pitch_system_mass", "pitch_system_mass_cost_coeff"),
    "spinner_mass": ("spinner_mass_coeff", "rotor_diameter", "spinner_mass_intercept"),
    "spinner_cost": ("spinner_mass", "spinner_mass_cost_coeff"),
    "low_speed_shaft_mass": (
        "rated_power_kw",
        "blade_mass",
        "lss_mass_coeff",
        "lss_mass_exp",
        "lss_mass_intercept",
    ),
    "low_speed_shaft_cost": ("low_speed_shaft_mass", "lss_mass_cost_coeff"),
    "bearing_mass": ("bearing_mass_coeff", "rotor_diameter", "bearing_mass_exp"),
    "bearing_cost": ("bearing_mass", "bearing_mass_cost_coeff"),
    "rated_rpm": ("rotor_diameter", "rated_power_kw", "efficiency_max", "max_tip_speed"),
    "rotor_torque": ("rotor_diameter", "rated_power_kw", "efficiency_max", "max_tip_speed"),
    "gearbox_mass": ("rotor_torque", "gearbox_torque_density"),
    "gearbox_cost": ("gearbox_mass", "gearbox_torque_density", "gearbox_torque_cost"),
    "brake_mass": ("rotor_torque", "brake_mass_coeff"),
    "brake_cost": ("brake_mass", "brake_mass_cost_coeff"),
    "high_speed_shaft_mass": ("rated_power_kw", "hss_mass_coeff"),
    "high_speed_shaft_cost": ("high_speed_shaft_mass", "hss_mass_cost_coeff"),
    "generator_mass": ("rated_power_kw", "generator_mass_coeff", "generator_mass_intercept"),
    "generator_cost": ("generator_mass", "generator_mass_cost_coeff"),
    "bedplate_mass": ("rotor_diameter", "bedplate_mass_exp"),
    "bedplate_cost": ("bedplate_mass", "bedplate_mass_cost_coeff"),
    "yaw_system_mass": (
        "rotor_diameter",
        "yaw_system_non_bearing_mass_coeff",
        "yaw_system_mass_coeff",
        "yaw_system_mass_exp",
    ),
    "yaw_system_cost": ("yaw_system_mass", "yaw_system_mass_cost_coeff"),
    "hydraulic_cooling_mass": ("rated_power_kw", "hvac_mass_coeff"),
    "hydraulic_cooling_cost": ("hydraulic_cooling_mass", "hvac_mass_cost_coeff"),
    "nacelle_cover_mass": (
        "rated_power_kw",
        "nacelle_cover_mass_coeff",
        "nacelle_cover_mass_intercept",
    ),
    "nacelle_cover_cost": ("nacelle_cover_mass", "nacelle_cover_mass_cost_coeff"),
    "platform_mainframe_mass": (
        "bedplate_mass",
        "platform_mainframe_mass_coeff",
        "has_crane",
        "crane_mass",
    ),
    "platform_mainframe_cost": (
        "platform_mainframe_mass",
        "platform_mainframe_mass_cost_coeff",
        "has_crane",
        "crane_mass",
        "crane_cost",
    ),
    "transformer_mass": ("rated_power_kw", "transformer_mass_coeff", "transformer_mass_intercept"),
    "transformer_cost": ("transformer_mass", "transformer_mass_cost_coeff"),
    "converter_mass": (),
    "converter_cost": ("converter_mass", "converter_mass_cost_coeff"),
    "electrical_connection_mass": (),
    "electrical_connection_cost": (
        "rated_power_kw",
        "electrical_connection_rated_power_cost_coeff",
    ),
    "controls_mass": (),
    "controls_cost": ("rated_power_kw", "controls_rated_power_cost_coeff"),
    "tower_mass": ("tower_length", "tower_mass_coeff", "tower_mass_exp"),
    "tower_cost": ("tower_mass", "tower_mass_cost_coeff"),
    "nacelle_mass": (
        "low_speed_shaft_mass",
        "num_bearings",
        "bearing_mass",
        "gearbox_mass",
        "brake_mass",
        "high_speed_shaft_mass",
        "generator_mass",
        "bedplate_mass",
        "yaw_system_mass",
        "hydraulic_cooling_mass",
        "nacelle_cover_mass",
        "platform_mainframe_mass",
        "transformer_mass",
        "converter_mass",
        "controls_mass",
        "electrical_connection_mass",
    ),
    "nacelle_cost": (
        "low_speed_shaft_cost",
        "num_bearings",
        "bearing_cost",
        "gearbox_cost",
        "brake_cost",
        "high_speed_shaft_cost",
        "generator_cost",
        "bedplate_cost",
        "yaw_system_cost",
        "hydraulic_cooling_cost",
        "nacelle_cover_cost",
        "platform_mainframe_cost",
        "transformer_cost",
    ),
    "hub_system_mass": ("hub_mass", "pitch_system_mass", "spinner_mass"),
    "hub_system_cost": ("hub_cost", "pitch_system_cost", "spinner_cost"),
    "rotor_mass": ("num_blades", "blade_mass", "hub_system_mass"),
    "rotor_cost": ("num_blades", "blade_cost", "hub_system_cost"),
    "turbine_mass": ("nacelle_mass", "rotor_mass", "tower_mass"),
    "turbine_cost": ("nacelle_cost", "rotor_cost", "tower_cost"),
}


@define
class CSMBase:
    """Base cost and scaling model that defines universally required inputs and calculations.

    Args:
        num_blades (int, optional): Number of turbine blades. Defaults to 3.
        rated_power_kw (float): Turbine rated power (:math:`kW`).
        rotor_diameter (float): Diameter of the swept area of the turbine blades (:math:`m`).
        turbine_class (int): Turbine classification; use 1 for IEC Wind-Class I, 2 fo
            IEC Wind-Class II or III.
        blade_mass_coeff (float): :math:`k` in the blade mass equation from
            :py:meth:`calculate_blade_mass`.
        blade_has_carbon (bool): Use True if the blade has carbon, False if not.
        blade_mass_cost_coeff (float): Blade cost per kilogram (USD/kg).
        blade_mass (float): Blade mass (kg).
        hub_mass_coeff (float): :math:`k` in the hub mass equation from
            :py:meth:`calculate_hub_mass`.
        hub_mass_intercept (bool): :math:`b` in the hub mass equation from
            :py:meth:`calculate_hub_mass`.
        hub_mass_cost_coeff (float): Hub cost per kilogram (USD/kg) from
            :py:meth:`calculate_hub_cost`.
        pitch_bearing_mass_coeff (float): :math:`k` in the pitch bearing mass equation from
            :py:meth:`calculate_pitch_system_mass`.
        pitch_bearing_mass_intercept (float): :math:`b1` in the pitch bearing mass equation from
            :py:meth:`calculate_pitch_system_mass`.
        bearing_housing_fraction (float): Mass of the housing for the bearing as a fraction of
            the bearing mass. :math:`h` in the pitch system mass equation from
            :py:meth:`calculate_pitch_system_mass`.
        mass_sys_offset (float): :math:`b2` in the pitch system mass equation from
            :py:meth:`calculate_pitch_system_mass`.
        pitch_system_mass_cost_coeff (float): Pitch system cost per kilogram (USD/kg) from
            :py:meth:`calculate_pitch_system_cost`.
        spinner_mass_coeff (float): :math:`k` in the mass equation above from
            :py:meth:`calculate_spinner_mass`.
        spinner_mass_intercept (bool): :math:`b` in the mass equation above from
            :py:meth:`calculate_spinner_mass`.
        spinner_mass_cost_coeff (float): Spinner cost per kilogram (USD/kg) from
            :py:meth:`calculate_spinner_cost`.
        lss_mass_coeff (float): :math:`k` in the low speed shaft mass equation from
            :py:meth:`calculate_low_speed_shaft_mass`.
        lss_mass_exp (float): :math:`b1` in the low speed shaft mass equation from
            :py:meth:`calculate_low_speed_shaft_mass`.
        lss_mass_intercept (float): :math:`b2` in the low speed shaft mass equation from
            :py:meth:`calculate_low_speed_shaft_mass`.
        lss_mass_cost_coeff (float): Low speed shaft cost per kilogram (USD/kg).
        bearing_mass_coeff (float): :math:`k` in the bearing mass equation from
            :py:meth:`calculate_bearing_mass`.
        bearing_mass_exp (bool): :math:`b` in the bearing mass equation from
            :py:meth:`calculate_bearing_mass`.
        bearing_mass_cost_coeff (float): Main bearing cost per kilogram (USD/kg).
        efficiency_max (float): Maximum possible drivetrain efficiency.
        max_tip_speed (float): Maximum allowable blade tip speed (:math:`m/s`).
        gearbox_torque_density (float): Gearbox torque per kilogram of mass from
            :py:meth:`calculate_gearbox_mass` and :py:meth:`calculate_gearbox_cost`
            (:math:`N*m/kg`).
        gearbox_torque_cost (float): Gearbox cost per unit of torque (:math:`USD/kN/m`) from
            :py:meth:`calculate_gearbox_cost`.
        brake_mass_coeff (bool): :math:`k` in the brake mass equation from
            :py:meth:`calculate_brake_mass`.
        brake_mass_cost_coeff (float): Brake cost per kilogram (USD/kg).
        rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
        hss_mass_coeff (float): Mass scaling coefficient, :math:`k` in the mass equation.
        hss_mass_cost_coeff (float): High speed shaft cost, per kilogram of mass, :math:`k` in the
            equation above (:math:`USD/kg`).
        generator_mass_coeff (float): :math:`k` in the generator mass equation above (:math:`kg/kW`)
            from :py:meth:`calculate_generator_mass`.
        generator_mass_intercept (bool): :math:`b` in the generator mass equation above (:math:`kg`)
            from :py:meth:`calculate_generator_mass`.
        generator_mass_cost_coeff (float): generator cost per kilogram (USD/kg).
        bedplate_mass_exp (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_bedplate_mass`.
        bedplate_mass_cost_coeff (float): bedplate cost per kilogram (USD/kg).
        yaw_system_non_bearing_mass_coeff (float): :math:`k1` in the mass equation from
            :py:meth:`calculate_yaw_system_mass` to account for non-bearing mass.
        yaw_system_mass_coeff (float): :math:`k2` in the mass equation from
            :py:meth:`calculate_yaw_system_mass`.
        yaw_system_mass_exp (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_yaw_system_mass`..
        yaw_system_mass_cost_coeff (float): Yaw system cost per kilogram (USD/kg).
        hvac_mass_coeff (float): Mass scaling coefficient. See
            :py:meth:`calculate_hydraulic_cooling_mass` for more details.
        hvac_mass_cost_coeff (float): Hydraulic cooling cost, per kilogram of mass.
        nacelle_cover_mass_coeff (float): :math:`k` in the mass equation from
            :py:meth:`calculate_nacelle_cover_mass`.
        nacelle_cover_mass_intercept (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_nacelle_cover_mass`.
        nacelle_cover_mass_cost_coeff (float): Nacelle cover cost per kilogram (USD/kg).
        platform_mainframe_mass_coeff (float): :math:`k` from
            :py:meth:`calculate_platform_mainframe_mass`.
        has_crane (bool): If True, apply :py:attr:`crane_mass` to
            :py:meth:`calculate_platform_mainframe_mass` and :py:attr:`crane_cost` to
            :py:meth:`calculate_platform_mainframe_cost`, otherwise ignore.
        crane_mass (bool): Mass of onboard crane, if :py:attr:`has_crane`, :math:`m_{crane}` from
            :py:meth:`calculate_platform_mainframe_mass`.
        crane_cost (bool): Cost of onboard crane, if :py:attr:`has_crane`, :math:`b` in the
            mass equation above.
        platform_mainframe_mass_cost_coeff (float): Platform mainframe cost per kilogram
            (USD/kg).
        transformer_mass_coeff (float): :math:`k` in the mass equation from
            :py:meth:`calculate_transformer_mass`.
        transformer_mass_intercept (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_transformer_mass`.
        transformer_mass_cost_coeff (float): Transformer cost per kilogram (USD/kg).
        controls_rated_power_cost_coeff (float): Controls cost per kilowatt of capacity (USD/kW).
        electrical_connection_rated_power_cost_coeff (float): Electrical connection cost per
            kilowatt (USD/kW).
        tower_mass_coeff (float): :math:`k` in the mass from :py:meth:`calculate_tower_mass`
            (:math:`kg/m`).
        tower_length (float): For onshore turbines, this is the hub height (total length above
            ground). For offshore turbines, this is length from transition piece to hub height
            (:math:`m`).
        tower_mass_exp (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_tower_mass`.
        tower_mass_cost_coeff (float): Tower cover cost per kilogram (USD/kg).

    Attributes:
        blade_mass (float): Blade mass (:math:`kg`). See :py:meth:`calculate_blade_mass`
            for details.
        blade_cost (float): Blade cost (USD). See :py:meth:`calculate_blade_cost`
            for details.
        hub_mass (float): Hub mass (kg). See :py:meth:`calculate_hub_mass`
            for more details.
        hub_cost (float): Hub cost (USD). See :py:meth:`calculate_hub_cost`
            for more details.
        pitch_system_mass (float): Pitch system mass (kg). See
            :py:meth:`calculate_pitch_system_mass` for more details.
        pitch_system_cost (float): Pitch system cost (USD). See
            :py:meth:`calculate_pitch_system_cost for more details.
        spinner_mass (float): Spinner mass (kg). See :py:meth:`calculate_spinner_mass`
            for more details.
        spinner_cost (float): Spinner cost (USD). See :py:meth:`calculate_spinner_cost`
            for more details.
        low_speed_shaft_mass (float): Low speed shaft mass (kg). See
            :py:meth:`calculate_low_speed_shaft_mass` for more details.
        low_speed_shaft_cost (float): Low speed shaft cost (USD). See
            :py:meth:`calculate_low_speed_shaft_cost` for more details.
        bearing_mass (float): Main bearing mass (kg). See :py:meth:`calculate_bearing_mass`
            for more details.
        bearing_cost (float): Main bearing cost (USD). See :py:meth:`calculate_bearing_cost`
            for more details.
        gearbox_mass (float): Gearbox mass (kg). See :py:meth:`calculate_gearbox_mass`
            for more details.
        gearbox_cost (float): Gearbox cost (USD). See :py:meth:`calculate_gearbox_cost`
            for more details.
        brake_mass (float): Brake mass (kg). See :py:meth:`brake_mass` for more details.
        brake_cost (float): Brake cost (USD). See :py:meth:`brake_cost` for more details.
        high_speed_shaft_mass (float): High speed shaft mass (kg).
            See :py:meth:`high_speed_shaft_mass` for more details.
        high_speed_shaft_cost (float): High speed shaft cost (USD).
            See :py:meth:`high_speed_shaft_cost` for more details.
        generator_mass (float): Generator mass (kg). See :py:meth:`calculate_generator_mass`
            for more details.
        generator_cost (float): Generator cost (USD). See :py:meth:`calculate_generator_cost`
            for more details.
        bedplate_mass (float): Bedplate mass (kg). See :py:meth:`calculate_bedplate_mass`
            for more details.
        bedplate_cost (float): Bedplate cost (USD). See :py:meth:`calculate_bedplate_cost`
            for more details.
        yaw_system_mass (float): Yaw system mass (kg). See :py:meth:`calculate_yaw_system_mass`
            for more details.
        yaw_system_cost (float): Yaw system cost (USD). See :py:meth:`calculate_yaw_system_cost`
            for more details.
        hydraulic_cooling_mass (float): Hydraulic cooling mass (kg). See
            :py:meth:`calculate_hydraulic_cooling_mass` for more details.
        hydraulic_cooling_cost (float): Hydraulic cooling cost (USD). See
            :py:meth:`calculate_hydraulic_cooling_cost` for more details.
        nacelle_cover_mass (float): nacelle_cover mass (kg). See
            :py:meth:`calculate_nacelle_cover_mass` for more details.
        nacelle_cover_cost (float): nacelle_cover mass (USD). See
            :py:meth:`calculate_nacelle_cover_cost` for more details.
        platform_mainframe_mass (float): Platform mainframe mass (kg).
            See :py:meth:`calculate_platform_mainframe_mass` for more details.
        platform_mainframe_cost (float): Platform mainframe cost (USD).
            See :py:meth:`calculate_platform_mainframe_cost` for more details.
        transformer_mass (float): Transformer cover mass (kg). See
            :py:meth:`calculate_transformer_mass` for more details.
        transformer_cost (float): Transformer cover cost (USD). See
            :py:meth:`calculate_transformer_cost` for more details.
        controls_mass (float): Controls mass (:math:`kg`). See
            :py:meth:`calculate_controls_mass` for more details.
        controls_cost (float): Controls cost (USD). See
            :py:meth:`calculate_controls_cost` for more details.
        electrical_connection_mass (float): Electrical connection mass (:math:`kg`). See
            :py:meth:`calculate_electrical_connection_mass` for more details.
        electrical_connection_cost (float): Electrical connection cost (USD). See
            :py:meth:`calculate_electrical_connection_cost` for more details.
        converter_mass (float): Power converter mass (:math:`kg`). See
            :py:meth:`calculate_converter_mass` for more details.
        converter_mass_cost_coeff (float): Power converter cost per kilogram (USD/kg). See
            :py:meth:`calculate_converter_cost` for more details.
        converter_cost (float): Power converter cost (USD). See
            :py:meth:`calculate_converter_cost` for more details.
        tower_mass (float): Tower mass (kg). See
            :py:meth:`calculate_tower_mass` for more details.
        tower_cost (float): Tower cost (USD). See
            :py:meth:`calculate_tower_cost` for more details.
        nacelle_mass (float): Total nacelle mass (kg). See
            :py:meth:`calculate_nacelle_mass` for more details.
        nacelle_cost (float): Total nacelle cost (US). See
            :py:meth:`calculate_nacelle_cost` for more details.
        hub_system_mass (float): Total hub system mass (kg). See
            :py:meth:`calculate_hub_system_mass` for more details.
        hub_system_cost (float): Total hub system cost (USD). See
            :py:meth:`calculate_hub_system_cost` for more details.
        rotor_mass (float): Total rotor mass (kg). See
            :py:meth:`calculate_rotor_mass` for more details.
        rotor_cost (float): Total rotor cost (USD). See
            :py:meth:`calculate_rotor_cost` for more details.
        turbine_mass (float): Total turbine mass (kg). See
            :py:meth:`calculate_turbine_mass` for more details.
        turbine_cost (float): Total turbine cost (USD). See
            :py:meth:`calculate_turbine_cost` for more details.
        turbine_cost (float): Total turbine cost, normalized by
            :py:attr:`rated_power_kw` (USD/kW).
    """

    # turbine general
    turbine_class: int = create_field(
        int, "unitless", "input", additional_validators=[validators.gt(0)]
    )
    rated_power_kw: int = create_field(int, "kW", "input", additional_validators=[validators.gt(0)])
    rotor_diameter: float = create_field(
        float, "m", "input", additional_validators=[validators.gt(0)]
    )
    efficiency_max: float = create_field(
        float, "unitless", "input", additional_validators=[validators.gt(0), validators.le(1)]
    )
    num_bearings: int = create_field(
        int, "unitless", "input", additional_validators=[validators.gt(0)]
    )

    # blades
    num_blades: int = create_field(
        int, "unitless", "input", default=3, additional_validators=[validators.gt(0)]
    )
    blade_has_carbon: bool = create_field(bool, "unitless", "input")
    blade_mass_coeff: float = create_field(float, "unitless", "input")
    blade_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    blade_mass: float = create_field(float, "kg", "both", additional_validators=[validators.ge(0)])
    blade_cost: float = create_field(float, "USD", "both", additional_validators=[validators.ge(0)])

    # hub
    hub_mass_coeff: float = create_field(float, "unitless", "input")
    hub_mass_intercept: float = create_field(float, "unitless", "input")
    hub_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    hub_mass: float = create_field(float, "kg", "both", additional_validators=[validators.ge(0)])
    hub_cost: float = create_field(float, "USD", "both", additional_validators=[validators.ge(0)])

    # rotor
    max_tip_speed: float = create_field(float, "m/s", "input")
    rated_rpm: float = create_field(float, "rpm", "both", additional_validators=[validators.ge(0)])
    rotor_torque: float = create_field(
        float, "MN*m", "both", additional_validators=[validators.ge(0)]
    )

    # pitch system
    pitch_bearing_mass_coeff: float = create_field(float, "unitless", "input")
    pitch_bearing_mass_intercept: float = create_field(float, "kg", "input")
    bearing_housing_fraction: float = create_field(float, "unitless", "input")
    mass_sys_offset: float = create_field(float, "kg", "input")
    pitch_system_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    pitch_system_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    pitch_system_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # spinner (nose cone)
    spinner_mass_coeff: float = create_field(float, "unitless", "input")
    spinner_mass_intercept: float = create_field(float, "kg", "input")
    spinner_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    spinner_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    spinner_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # low speed shaft
    lss_mass_coeff: float = create_field(float, "unitless", "input")
    lss_mass_intercept: float = create_field(float, "kg", "input")
    lss_mass_exp: float = create_field(float, "unitless", "input")
    lss_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    low_speed_shaft_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    low_speed_shaft_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # main bearing
    bearing_mass_coeff: float = create_field(float, "unitless", "input")
    bearing_mass_exp: float = create_field(float, "units", "input")
    bearing_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    bearing_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    bearing_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # gearbox
    gearbox_torque_density: float = create_field(float, "N*m/kg", "input")
    gearbox_torque_cost: float = create_field(float, "USD/kN/m", "input")
    gearbox_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    gearbox_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # brakes
    brake_mass_coeff: float = create_field(float, "unitless", "input")
    brake_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    brake_mass: float = create_field(float, "kg", "both", additional_validators=[validators.ge(0)])
    brake_cost: float = create_field(float, "USD", "both", additional_validators=[validators.ge(0)])

    # high speed shaft
    hss_mass_coeff: float = create_field(float, "unitless", "input")
    hss_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    high_speed_shaft_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    high_speed_shaft_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # generator
    generator_mass_coeff: float = create_field(float, "kg/kW", "input")
    generator_mass_intercept: float = create_field(float, "kg", "input")
    generator_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    generator_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    generator_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # bedplate
    bedplate_mass_exp: float = create_field(float, "unitless", "input")
    bedplate_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    bedplate_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    bedplate_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # yaw system
    yaw_system_non_bearing_mass_coeff: float = create_field(float, "unitless", "input")
    yaw_system_mass_coeff: float = create_field(float, "unitless", "input")
    yaw_system_mass_exp: float = create_field(float, "unitless", "input")
    yaw_system_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    yaw_system_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    yaw_system_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # high speed shaft
    hvac_mass_coeff: float = create_field(float, "unitless", "input")
    hvac_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    hydraulic_cooling_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    hydraulic_cooling_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # nacelle cover
    nacelle_cover_mass_coeff: float = create_field(float, "kg/kW", "input")
    nacelle_cover_mass_intercept: float = create_field(float, "kg", "input")
    nacelle_cover_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    nacelle_cover_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    nacelle_cover_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # platform mainframe
    has_crane: bool = create_field(bool, "unitless", "input")
    crane_mass: float = create_field(float, "kg", "input", additional_validators=[validators.ge(0)])
    crane_cost: float = create_field(
        float, "USD", "input", additional_validators=[validators.ge(0)]
    )
    platform_mainframe_mass_coeff: float = create_field(float, "unitless", "input")
    platform_mainframe_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    platform_mainframe_mass: float = create_field(float, "kg", "both")
    platform_mainframe_cost: float = create_field(float, "USD", "both")

    # transformer
    transformer_mass_coeff: float = create_field(float, "kg/kW", "input")
    transformer_mass_intercept: float = create_field(float, "kg", "input")
    transformer_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    transformer_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    transformer_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # electronics
    controls_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    controls_rated_power_cost_coeff: float = create_field(
        float, "USD/kW", "input", additional_validators=[validators.ge(0)]
    )
    controls_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    electrical_connection_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    electrical_connection_rated_power_cost_coeff: float = create_field(
        float, "USD/kW", "input", additional_validators=[validators.ge(0)]
    )
    electrical_connection_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    converter_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    converter_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    converter_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    # tower
    tower_mass_coeff: float = create_field(float, "unitless", "input")
    tower_length: float = create_field(float, "m", "input")
    tower_mass_exp: float = create_field(float, "unitless", "input")
    tower_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    tower_mass: float = create_field(float, "kg", "both", additional_validators=[validators.ge(0)])
    tower_cost: float = create_field(float, "USD", "both", additional_validators=[validators.ge(0)])

    # totals
    nacelle_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    nacelle_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )
    hub_system_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    hub_system_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )
    rotor_mass: float = create_field(float, "kg", "both", additional_validators=[validators.ge(0)])
    rotor_cost: float = create_field(float, "USD", "both", additional_validators=[validators.ge(0)])
    turbine_mass: float = create_field(
        float, "kg", "output", additional_validators=[validators.ge(0)]
    )
    turbine_cost: float = create_field(
        float, "USD", "output", additional_validators=[validators.ge(0)]
    )
    turbine_cost_kw: float = create_field(
        float, "USD/kW", "output", additional_validators=[validators.ge(0)]
    )

    # all else
    parameter_map: dict[str, tuple[str]] = field(init=False)
    parameter_graph: nx.Digraph = field(init=False)

    # NOTE: temporary while prototyping
    turbine_production_cost: float = field(default=1000.0)
    tower_flange_material_cost: float = field(default=1000.0)
    tower_flange_production_cost: float = field(default=1000.0)

    def __attrs_pre_init__(self):
        """Pre-initialization hook to set any hard-coded, mutable values."""
        self.parameter_map = deepcopy(parameter_map)

    def __attrs_post_init__(self):
        """Post initialization setup."""
        self.parameter_graph = nx.DiGraph()
        for key, params in self.parameter_map.items():
            for dependent in params:
                self.parameter_graph.add_edge(key, dependent)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, partial: bool = False):
        """Creates a new instance from a dictionary with simplified and intuitive error messages
        for extraneous and missing attributes.

        Args:
            data (dict): The data dictionary to be mapped.
            partial (bool, optional): If True, don't raise errors for an incomplete definition of
                the model. Defaults to False.

        Returns:-
            cls: An instance of :py:class:`CSMBase` or one of its subclasses.
        """
        inputs = set(data)
        _attrs = cls.__attrs_attrs__
        _name = cls.__name__
        valid_inputs = {
            el.name for el in _attrs if el.init and el.metadata.get("io") in ("input", "both")
        }
        required = {
            el.name
            for el in _attrs
            if el.init and el.default is None and el.metadata["io"] == "input"
        }

        extra = inputs.difference(valid_inputs)
        if len(extra):
            msg = f"The initialization for {_name} was given extraneous inputs: {', '.join(extra)}"
            raise AttributeError(msg)

        missing = required.difference(inputs)
        if missing and not partial:
            msg = (
                f"The class definition for {_name} is missing the following"
                f" inputs: {', '.join(missing)}"
            )
            raise AttributeError(msg)
        return cls(**data)

    @cached_property
    def fields(self) -> tuple[Attribute]:
        """Returns a tuple of :py:attr:`attrs.Attribute` that is a convenient shortcut for
        ``attrs.fields(self)``.

        Returns:
            tuple[Attribute]: See documentation for `attrs.fields`_ for more

        .. _attrs.fields:
            https://www.attrs.org/en/stable/api.html#attrs.fields
        """
        return self.__attrs_attrs__

    @cached_property
    def fields_dict(self) -> dict[str, Attribute]:
        """Returns a tuple of :py:attr:`attrs.Attribute` that is a convenient shortcut for
        ``attrs.fields_dict(self)``.

        Returns:
            tuple[Attribute]: See documentation for `attrs.fields_dict`_ for more

        .. _attrs.fields_dict:
            https://www.attrs.org/en/stable/api.html#attrs.fields_dict
        """
        return {el.name: el for el in self.__attrs_attrs__}

    def _has_values(self, *args: str) -> Generator[bool]:
        """Checks if the user provided values for a given :py:attr:`arg` (True), or if they are
        model defaults (False).

        Yields:
            Generator[bool]: Booleans indicating valid values have been implemented or provided
                by the user (True) or if the base class defaults are present (False).
        """
        for arg in args:
            default = getattr(self.fields, arg).default
            value = getattr(self, arg)
            non_none_has_val = value is not None and default is not None
            none_has_value = value != default and default is None
            yield non_none_has_val or none_has_value

    def _validate_inputs(self, parameters: tuple[str, ...]) -> None:
        """Validates if the required parameters to calculate an attribute's value have been
        populated by a subclass or provided by the user.

        Args:
            parameters (list[str]): List of class attributes to check for valid inputs.

        Raises:
            ValueError: Raised if any of the required :py:attr:`parameters` have not been
            provided by the user or a subclass.
        """
        has_values = tuple(self._has_values(*parameters))
        if not all(has_values):
            missing = [
                name for exists, name in zip(has_values, parameters, strict=True) if not exists
            ]
            raise ValueError(f"Inputs for the following variables required: {', '.join(missing)}")

    def _prepare_calculation(self, method: str) -> bool:
        """Checks the existence of the attribute(s) a method will set, and returns True
        if it exists already, or False if it still needs to be calculated. When False,
        the dependent parameters from :py:attr:`parameter_map` have valid inputs.

        Args:
            method (str): Name of the attribute the method is setting.

        Returns:
            bool: True if the method can be returned early, or False if :py:attr:`method` still
                needs to be calculated.
        """
        if next(self._has_values(method)):
            return True

        parameters = self.parameter_map[method]
        self._validate_inputs(parameters=parameters)
        return False

    def reset_values(self, *args: str) -> None:
        """Resets the values for any provided :py:attr:`args` to the model default.

        Raises:
            KeyError: Raised if any of :py:attr:`args` are not a class attribute
        """
        for arg in args:
            if (attribute := self.fields_dict.get(arg)) is None:
                raise KeyError(f"'{arg}' is an invalid attribute, please check your spelling.")
            setattr(self, arg, attribute.default)

    def get_dependent_attributes(self, name: str) -> set[str]:
        """Returns a set of model attributes that depend on the value of :py:attr:`name`.

        Args:
            name (str): The name of a model attribute that a user inputs or can be
                calculated.

        Returns:
            set[str]: Set of model attribute names that rely on the value of :py:attr:`name`.
        """
        return nx.ancestors(self.parameter_graph, name)

    def update(self, data: dict[str, Any]):
        """Update the value of one or multiple model parameters.

        Args:
            data (dict[str, Any]): Dictionary of an attribute and its new value.

        Raises:
            Attribute: Raised if any of :py:attr:`args` are not a class attribute
        """
        if not isinstance(data, dict):
            raise ValueError("`data` must be a dictionary")
        to_reset = set()
        for name, value in data.items():
            setattr(self, name, value)
            to_reset.update(self.get_dependent_attributes(name))

        to_reset.difference(data)
        self.reset_values(*to_reset)

    @classmethod
    def parameterize(
        cls,
        base_kwargs: dict[str, int | float | bool],
        parameterized_kwargs: dict[str, int | float | bool],
        results: str | list[str] | None = None,
    ):
        """Run a design loop using a set of control and independent variables as a product of all
        possible parameterized values.

        Args:
            base_kwargs (dict[str, int  |  float  |  bool]): Dictionary of control variables.
            parameterized_kwargs (dict[str, int  |  float  |  bool]): Dictionary of independent
                variables with an iterable value consisting of an explicit set of values or range
                of values generated by ``np.linspace``. For both cases, the first value must be one
                of "inputs" or "range". Subsequent values should specified according to the case:

                - "inputs": all subsequent values will be used as inputs, e.g.,
                  {"tower_length": ("inputs", 90, 100)} will run 2 iterations, one with a 90m tower
                  length and one with a 100 meter tower length.
                - "range": subsequent values must be start, stop, num where stop is inclusive,
                   e.g., {"efficiency_max": ("range", 0.8, 1.0, 5)} will run 5 iterations of the
                   model varying ``efficiency_max`` with values 0.8, 0.85, 0.9, 0.95, and 1.0.

            results (str | list[str] | None, optional): A specific list of model results to capture.
                 If None, then :py:meth:`get_results` will be used. Defaults to None.

        Raises:
            ValueError: Raised if any of the keys of :py:attr:`parameterized_kwargs` are not defined
                as a "range" or "inputs" style variable.
            ValueError: Raised if fewer than 2 inputs are able to be generated by the
                parameterization type.

        Returns:
            pd.DataFrame: DataFrame with a ``pandas.MultiIndex`` column set of all parameterized
                values and with an index of the results names.
        """
        names = []
        expanded = {}
        for name, vals in parameterized_kwargs.items():
            match how := vals[0]:
                case "inputs":
                    _inputs = vals[1:]
                case "range":
                    if len(vals[1:]) != 3:
                        msg = (
                            f"'range' input for '{name}' must have 3 values: start, stop, and"
                            " number of total values."
                        )
                        raise ValueError(msg)
                    _min, _max, _num = vals[1:]
                    _inputs = list(np.linspace(_min, _max, _num))
                case _:
                    raise ValueError(
                        f"First value for '{name}' must be 'inputs' or 'range', not '{how}'."
                    )
            if len(_inputs) < 2:
                raise ValueError(f"Parameterized inputs for '{name}' must have at least 2 values.")
            names.append(name)
            expanded[name] = _inputs

        inputs = list(zip_longest([names], list(product(*expanded.values())), fillvalue=names))
        additional_kwargs = [dict(zip(*el, strict=True)) for el in inputs]

        all_results = []
        model = cls.from_dict(base_kwargs, partial=True)
        for kwargs in additional_kwargs:
            model.update(kwargs)
            model.run()

            if results is None:
                single_results = model.get_results()
            else:
                if isinstance(results, str):
                    results = [results]
                single_results = {el: getattr(model, el) for el in results}
            all_results.append(
                pd.DataFrame.from_dict(single_results, orient="index")
                .assign(**kwargs)
                .set_index(names, append=True)
                .rename(columns={0: "result"})
            )
        df = pd.concat(all_results).unstack(level=names)
        df.columns = df.columns.droplevel(0)  # remove the "result" name for aesthetics
        return df

    def calculate_blade_mass(self):
        """Calculates and sets :py:attr:`blade_mass` if it was not provided by the user.

        .. math:: k * diameter^b

        where:

        - :math:`k =` :py:attr:`blade_mass_coeff`
        - :math:`diameter =` :py:attr:`rotor_diameter` / 2
        - :math:`b =`
          - 2.47 if :py:attr:`turbine_class` is 1 and :py:attr:`blade_has_carbon` is True
          - 2.54 if :py:attr:`turbine_class` is 1 and :py:attr:`blade_has_carbon` is False
          - 2.44 if :py:attr:`turbine_class` > 1 and :py:attr:`blade_has_carbon` is True
          - 2.5 if :py:attr:`turbine_class` > 1 and :py:attr:`blade_has_carbon` is False
          - 2.5 if :py:attr:`turbine_class` < 1

        Args:
            blade_mass_coeff (float): :math:`k` in the mass equation above.
            rotor_diameter (float): Diameter of the swept area of the turbine blades.
            turbine_class (int): Turbine classification; use 1 for IEC Wind-Class I, 2 fo
                IEC Wind-Class II or III.
            blade_has_carbon (bool): Use True if the blade has carbon, False if not.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("blade_mass")
        if exists:
            return

        match self.turbine_class:
            case 1:
                _exp = {"carbon": 2.47, "no_carbon": 2.54}
            case _ if self.turbine_class > 1:
                _exp = {"carbon": 2.44, "no_carbon": 2.5}
            case _:
                _exp = {"carbon": 2.5, "no_carbon": 2.5}
        exp = _exp["carbon" if self.blade_has_carbon else "no_carbon"]
        self.blade_mass = self.blade_mass_coeff * (self.rotor_diameter / 2) ** exp

    def calculate_blade_cost(self):
        """Calculates and sets :py:attr:`blade_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`blade_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`blade_mass`

        Args:
            blade_mass_cost_coeff (float): Blade cost per kilogram (USD/kg).
            blade_mass (float): Blade mass (kg).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("blade_cost")
        if exists:
            return

        self.blade_cost = self.blade_mass_cost_coeff * self.blade_mass

    def calculate_hub_mass(self):
        """Calculates and sets :py:attr:`hub_mass` if it was not provided by the user.

        .. math:: k * m_{blade} + b

        where:

        - :math:`k =` :py:attr:`hub_mass_coeff`
        - :math:`m_{blade} =` :py:attr:`blade_mass`
        - :math:`b =` :py:attr:`hub_mass_intercept`

        Args:
            hub_mass_coeff (float): :math:`k` in the mass equation above.
            blade_mass (float): Blade mass (:math:`kg`). See :py:meth:`calculate_blade_mass`
                for details.
            hub_mass_intercept (bool): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("hub_mass")
        if exists:
            return

        self.hub_mass = self.hub_mass_coeff * self.blade_mass + self.hub_mass_intercept

    def calculate_hub_cost(self):
        """Calculates and sets :py:attr:`hub_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`hub_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`hub_mass` (:math:`kg`).

        Args:
            hub_mass_cost_coeff (float): Hub cost per kilogram (USD/kg).
            hub_mass (float): Hub mass (kg). See :py:meth:`calculate_hub_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("hub_cost")
        if exists:
            return

        self.hub_cost = self.hub_mass_cost_coeff * self.hub_mass

    def calculate_pitch_system_mass(self):
        """Calculates and sets :py:attr:`pitch_system_mass` if it was not provided by the user.

        First, the pitch bearing mass is calculated as
        :math:`m_{bearing} = k*m_{blade}*{num_blades} + b1`. Then the total pitch system mass,
        including with bearing housing is calculated as :math:`mass = (1+h)*m_{bearing} + b2`.
        The values of the constants were NOT updated in 2015 and are the same as the original CSM.

        where:

        - :math:`k =` :py:attr:`pitch_bearing_mass_coeff`
        - :math:`m_{blade} =` :py:attr:`blade_mass`
        - :math:`b1 =` :py:attr:`pitch_bearing_mass_intercept`
        - :math:`h =` :py:attr:`bearing_housing_fraction`
        - :math:`b2 =` :py:attr:`mass_sys_offset`

        Args:
            num_blades (int, optional): Number of turbine blades. Defaults to 3.
            pitch_bearing_mass_coeff (float): :math:`k` in the pitch bearing mass equation.
            blade_mass (float): Blade mass (:math:`kg`). See :py:meth:`calculate_blade_mass`
                for details.
            pitch_bearing_mass_intercept (float): :math:`b1` in the pitch bearing mass equation.
            bearing_housing_fraction (float): Mass of the housing for the bearing as a fraction of
                the bearing mass. :math:`h` in the pitch system mass equation.
            mass_sys_offset (float): :math:`b2` in the pitch system mass equation.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("pitch_system_mass")
        if exists:
            return

        bearing_mass = (
            self.pitch_bearing_mass_coeff * self.blade_mass * self.num_blades
            + self.pitch_bearing_mass_intercept
        )
        self.pitch_system_mass = (
            bearing_mass * (1 + self.bearing_housing_fraction) + self.mass_sys_offset
        )

    def calculate_pitch_system_cost(self):
        """Calculates and sets :py:attr:`pitch_system_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`pitch_system_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`pitch_system_mass` (:math:`kg`).

        Args:
            pitch_system_mass_cost_coeff (float): Pitch system cost per kilogram (USD/kg).
            pitch_system_mass (float): Pitch system mass (kg). See
                :py:meth:`calculate_pitch_system_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        method = "pitch_system_cost"
        if next(self._has_values(method)):
            return

        parameters = self.parameter_map[method]
        self._validate_inputs(parameters=parameters)

        self.pitch_system_cost = self.pitch_system_mass_cost_coeff * self.pitch_system_mass

    def calculate_spinner_mass(self):
        """Calculates and sets :py:attr:`spinner_mass` (nose cone mass) if it was not provided by
        the user.

        .. math:: k * rotor_diameter + b

        where:

        - :math:`k =` :py:attr:`spinner_mass_coeff`
        - :math:`rotor_diameter =` :py:attr:`rotor_diameter`
        - :math:`b =` :py:attr:`spinner_mass_intercept`

        Args:
            spinner_mass_coeff (float): :math:`k` in the mass equation above.
            rotor_diameter (float): Turbine rotor diameter (:math:`m`).
            spinner_mass_intercept (bool): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("spinner_mass")
        if exists:
            return

        self.spinner_mass = (
            self.spinner_mass_coeff * self.rotor_diameter + self.spinner_mass_intercept
        )

    def calculate_spinner_cost(self):
        """Calculates and sets :py:attr:`spinner_cost` (nose cone cost) if it was not provided by
        the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`spinner_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`spinner_mass` (:math:`kg`).

        Args:
            spinner_mass_cost_coeff (float): Spinner cost per kilogram (USD/kg).
            spinner_mass (float): Spinner mass (kg). See :py:meth:`calculate_spinner_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("spinner_cost")
        if exists:
            return

        self.spinner_cost = self.spinner_mass_cost_coeff * self.spinner_mass

    def calculate_low_speed_shaft_mass(self):
        """Calculates and sets :py:attr:`low_speed_shaft_mass` if it was not provided by the user.

        :math:`m_{lss} = k*(m_{blade}*power)^b1 + b2`.

        where:

        - :math:`k =` :py:attr:`lss_mass_coeff`
        - :math:`power =` :py:attr:`rated_power_kw` / 1000
        - :math:`m_{blade} =` :py:attr:`blade_mass`
        - :math:`b1 =` :py:attr:`lss_mass_exp`
        - :math:`b2 =` :py:attr:`lss_mass_intercept`

        Args:
            rated_power_kw (int, optional): Turbine nameplate capacity, (:math:`kW`).
            blade_mass (float): Blade mass (:math:`kg`). See :py:meth:`calculate_blade_mass`
                for details.
            lss_mass_coeff (float): :math:`k` in the low speed shaft mass equation.
            lss_mass_exp (float): :math:`b1` in the low speed shaft mass equation.
            lss_mass_intercept (float): :math:`b2` in the low speed shaft mass equation.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("low_speed_shaft_mass")
        if exists:
            return

        self.low_speed_shaft_mass = (
            self.lss_mass_coeff
            * (self.blade_mass * self.rated_power_kw * 1e-3) ** self.lss_mass_exp
            + self.lss_mass_intercept
        )

    def calculate_low_speed_shaft_cost(self):
        """Calculates and sets :py:attr:`low_speed_shaft_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`lss_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`low_speed_shaft_mass` (:math:`kg`).

        Args:
            lss_mass_cost_coeff (float): Low speed shaft cost per kilogram (USD/kg).
            low_speed_shaft_mass (float): Low speed shaft mass (kg). See
                :py:meth:`calculate_low_speed_shaft_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("low_speed_shaft_cost")
        if exists:
            return

        self.low_speed_shaft_cost = self.lss_mass_cost_coeff * self.low_speed_shaft_mass

    def calculate_bearing_mass(self):
        """Calculates and sets :py:attr:`bearing_mass` for the main bearing if it was not provided
        by the user.

        .. math:: k*rotor_diameter^b

        where:

        - :math:`k =` :py:attr:`bearing_mass_coeff`
        - :math:`rotor_diameter =` :py:attr:`rotor_diameter`
        - :math:`b =` :py:attr:`bearing_mass_exp`

        Args:
            rotor_diameter (float): Turbine rotor diameter (:math:`m`).
            bearing_mass_coeff (float): :math:`k` in the mass equation above.
            bearing_mass_exp (bool): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("bearing_mass")
        if exists:
            return

        self.bearing_mass = self.bearing_mass_coeff * self.rotor_diameter**self.bearing_mass_exp

    def calculate_bearing_cost(self):
        """Calculates and sets :py:attr:`bearing_cost` (nose cone cost) if it was not provided by
        the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`bearing_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`bearing_mass` (:math:`kg`).

        Args:
            bearing_mass_cost_coeff (float): Main bearing cost per kilogram (USD/kg).
            bearing_mass (float): Main bearing mass (kg). See :py:meth:`calculate_bearing_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("bearing_cost")
        if exists:
            return

        self.bearing_cost = self.bearing_mass_cost_coeff * self.bearing_mass

    def calculate_rotor_torque(self):
        """Calculates and sets :py:attr:`rated_rpm` and :py:attr:`rotor_torque` if they were not
        provided by the user.

        Args:
            rotor_diameter (float): Turbine rotor diameter (:math:`m`).
            rated_power_kw (float): Turbine rated power (:math:`kW`).
            efficiency_max (float): Maximum possible drivetrain efficiency.
            max_tip_speed (float): Maximum allowable blade tip speed (:math:`m/s`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        rpm_exists = self._prepare_calculation("rated_rpm")
        torque_exists = self._prepare_calculation("rotor_torque")
        if rpm_exists and torque_exists:
            return

        rated_hub_power = self.rated_power_kw / self.efficiency_max
        rotor_speed = self.max_tip_speed / (0.5 * self.rotor_diameter)
        if not rpm_exists:
            self.rated_rpm = rotor_speed / (2.0 * math.pi) * 60.0
        if not torque_exists:
            self.rotor_torque = rated_hub_power / rotor_speed

    def calculate_gearbox_mass(self):
        """Calculates and sets :py:attr:`gearbox_mass` for the gearbox if it was not provided
        by the user.

        .. math:: torque * 1000 / b

        where:

        - :math:`torque =` :py:attr:`rotor_torque`
        - :math:`b =` :py:attr:`gearbox_torque_density`

        Args:
            rotor_torque (float): Turbine rotor torque at rated power (:math:`kNm`).
            gearbox_torque_density (float): :math:`k` in the mass equation above (:math:`N*m/kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("gearbox_mass")
        if exists:
            return

        self.gearbox_mass = self.rotor_torque * 1e3 / self.gearbox_torque_density

    def calculate_gearbox_cost(self):
        """Calculates and sets :py:attr:`gearbox_cost` if it was not provided by the user.

        .. math:: k * m_{gearbox} * {gearbox_torque_cost} / 1000

        where:

        - :math:`k =` :py:attr:`gearbox_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`gearbox_mass` (:math:`kg`).

        Args:
            gearbox_mass (float): Main bearing mass (kg). See :py:meth:`calculate_gearbox_mass`
                for more details.
            gearbox_torque_density (float): :math:`k` in the mass equation above (:math:`N*m/kg`).
            gearbox_torque_cost (float): Gearbox cost per :math:`N*m` (:math:`USD/kN/m`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("gearbox_cost")
        if exists:
            return

        self.gearbox_cost = (
            self.gearbox_mass * self.gearbox_torque_density * self.gearbox_torque_cost * 1e-3
        )

    def calculate_brake_mass(self):
        """Calculates and sets :py:attr:`brake_mass` for if it was not provided by the user.

        .. math:: k * torque

        where:

        - :math:`torque =` :py:attr:`rotor_torque`
        - :math:`k =` :py:attr:`brake_mass_coeff`

        Args:
            rotor_torque (float): Turbine rotor torque at rated power (:math:`kNm`).
            brake_mass_coeff (float): Mass scaling coefficient, :math:`k` in the mass equation.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("brake_mass")
        if exists:
            return

        parameters = ("rotor_torque", "brake_mass_coeff")
        self._validate_inputs(parameters=parameters)

        self.brake_mass = self.rotor_torque * 1000.0 * self.brake_mass_coeff

    def calculate_brake_cost(self):
        """Calculates and sets :py:attr:`brake_cost` if it was not provided by the user.

        .. math:: k * m_{brake}

        where:

        - :math:`k =` :py:attr:`brake_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`brake_mass` (:math:`kg`).

        Args:
            brake_mass (float): Brake mass (kg). See :py:meth:`calculate_brake_mass`
                for more details.
            brake_mass_cost_coeff (float): Brake cost, per kilogram of mass, :math:`k` in the
                equation above (:math:`USD/kg`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("brake_cost")
        if exists:
            return

        self.brake_cost = self.brake_mass * self.brake_mass_cost_coeff

    def calculate_high_speed_shaft_mass(self):
        """Calculates and sets :py:attr:`high_speed_shaft_mass` for if it was not provided by the
        user.

        .. math:: k * power

        where:

        - :math:`power =` :py:attr:`rated_power_kw`
        - :math:`k =` :py:attr:`hss_mass_coeff`

        Args:
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
            hss_mass_coeff (float): Mass scaling coefficient, :math:`k` in the mass equation.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("high_speed_shaft_mass")
        if exists:
            return

        self.high_speed_shaft_mass = self.hss_mass_coeff * self.rated_power_kw

    def calculate_high_speed_shaft_cost(self):
        """Calculates and sets :py:attr:`high_speed_shaft_cost` if it was not provided by the user.

        .. math:: k * m_{high_speed_shaft}

        where:

        - :math:`k =` :py:attr:`hss_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`high_speed_shaft_mass` (:math:`kg`).

        Args:
            high_speed_shaft_mass (float): High speed shaft mass (kg). See
                :py:meth:`calculate_high_speed_shaft_mass` for more details.
            hss_mass_cost_coeff (float): High speed shaft cost, per kilogram of mass, :math:`k` in
                the equation above (:math:`USD/kg`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("high_speed_shaft_cost")
        if exists:
            return

        self.high_speed_shaft_cost = self.high_speed_shaft_mass * self.hss_mass_cost_coeff

    def calculate_generator_mass(self):
        """Calculates and sets :py:attr:`generator_mass` if it was not provided by the user.

        .. math:: k * power + b

        where:

        - :math:`k =` :py:attr:`generator_mass_coeff`
        - :math:`power =` :py:attr:`rated_power_kw`
        - :math:`b =` :py:attr:`generator_mass_intercept`

        Args:
            generator_mass_coeff (float): :math:`k` in the mass equation above (:math:`kg/kW`).
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
            generator_mass_intercept (bool): :math:`b` in the mass equation above (:math:`kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("generator_mass")
        if exists:
            return

        self.generator_mass = (
            self.generator_mass_coeff * self.rated_power_kw + self.generator_mass_intercept
        )

    def calculate_generator_cost(self):
        """Calculates and sets :py:attr:`generator_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`generator_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`generator_mass` (:math:`kg`).

        Args:
            generator_mass_cost_coeff (float): generator cost per kilogram (USD/kg).
            generator_mass (float): generator mass (kg). See :py:meth:`calculate_generator_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("generator_cost")
        if exists:
            return

        self.generator_cost = self.generator_mass_cost_coeff * self.generator_mass

    def calculate_bedplate_mass(self):
        """Calculates and sets :py:attr:`bedplate_mass` if it was not provided by the user.

        .. math:: rotor_diameter ^ b

        where:

        - :math:`rotor_diameter =` :py:attr:`rotor_diameter`
        - :math:`b =` :py:attr:`bedplate_mass_exp`

        Args:
            rotor_diameter (float): Turbine rotor diameter (:math:`m`).
            bedplate_mass_exp (bool): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("bedplate_mass")
        if exists:
            return

        self.bedplate_mass = self.rotor_diameter**self.bedplate_mass_exp

    def calculate_bedplate_cost(self):
        """Calculates and sets :py:attr:`bedplate_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`bedplate_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`bedplate_mass` (:math:`kg`).

        Args:
            bedplate_mass_cost_coeff (float): bedplate cost per kilogram (USD/kg).
            bedplate_mass (float): bedplate mass (kg). See :py:meth:`calculate_bedplate_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("bedplate_cost")
        if exists:
            return

        self.bedplate_cost = self.bedplate_mass_cost_coeff * self.bedplate_mass

    def calculate_yaw_system_mass(self):
        r"""Calculates and sets :py:attr:`yaw_system_mass` if it was not provided by the user.

        .. math:: k1 * (k2 * rotor\_diameter ^ b)

        where:

        - :math:`k1 =` :py:attr:`yaw_system_non_bearing_mass_coeff`
        - :math:`k2 =` :py:attr:`yaw_system_mass_coeff`
        - :math:`rotor\_diameter =` :py:attr:`rotor_diameter`
        - :math:`b =` :py:attr:`yaw_system_mass_exp`

        Args:
            yaw_system_non_bearing_mass_coeff (float): :math:`k1` in the mass equation above to
                account for non-bearing mass.
            yaw_system_mass_coeff (float): :math:`k2` in the mass equation above (:math:`kg/kW`).
            rotor_diameter (float): Turbine rotor diameter (:math:`m`).
            yaw_system_mass_exp (bool): :math:`b` in the mass equation above (:math:`kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("yaw_system_mass")
        if exists:
            return

        self.yaw_system_mass = self.yaw_system_non_bearing_mass_coeff * (
            self.yaw_system_mass_coeff * self.rotor_diameter**self.yaw_system_mass_exp
        )

    def calculate_yaw_system_cost(self):
        """Calculates and sets :py:attr:`yaw_system_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`yaw_system_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`yaw_system_mass` (:math:`kg`).

        Args:
            yaw_system_mass_cost_coeff (float): Yaw system cost per kilogram (USD/kg).
            yaw_system_mass (float): Yaw system mass (kg).
                See :py:meth:`calculate_yaw_system_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("yaw_system_cost")
        if exists:
            return

        self.yaw_system_cost = self.yaw_system_mass_cost_coeff * self.yaw_system_mass

    def calculate_hydraulic_cooling_mass(self):
        """Calculates and sets :py:attr:`hydraulic_cooling_mass` for if it was not provided by the
        user.

        .. math:: k * power

        where:

        - :math:`power =` :py:attr:`rated_power_kw`
        - :math:`k =` :py:attr:`hvac_mass_coeff`

        Args:
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
            hvac_mass_coeff (float): Mass scaling coefficient, :math:`k` in the mass equation.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("hydraulic_cooling_mass")
        if exists:
            return

        self.hydraulic_cooling_mass = self.hvac_mass_coeff * self.rated_power_kw

    def calculate_hydraulic_cooling_cost(self):
        """Calculates and sets :py:attr:`hydraulic_cooling_cost` if it was not provided by the user.

        .. math:: k * m_{hydraulic_cooling}

        where:

        - :math:`k =` :py:attr:`hvac_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`hydraulic_cooling_mass` (:math:`kg`).

        Args:
            hydraulic_cooling_mass (float): Hydraulic cooling mass (kg). See
                :py:meth:`calculate_hydraulic_cooling_mass` for more details.
            hvac_mass_cost_coeff (float): Hydraulic cooling cost, per kilogram of mass, :math:`k` in
                the equation above (:math:`USD/kg`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("hydraulic_cooling_cost")
        if exists:
            return

        self.hydraulic_cooling_cost = self.hydraulic_cooling_mass * self.hvac_mass_cost_coeff

    def calculate_nacelle_cover_mass(self):
        """Calculates and sets :py:attr:`nacelle_cover_mass` if it was not provided by the user.

        .. math:: k * power + b

        where:

        - :math:`k =` :py:attr:`nacelle_cover_mass_coeff`
        - :math:`power =` :py:attr:`rated_power_kw`
        - :math:`b =` :py:attr:`nacelle_cover_mass_intercept`

        Args:
            nacelle_cover_mass_coeff (float): :math:`k` in the mass equation above (:math:`kg/kW`).
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
            nacelle_cover_mass_intercept (bool): :math:`b` in the mass equation above (:math:`kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("nacelle_cover_mass")
        if exists:
            return

        self.nacelle_cover_mass = (
            self.nacelle_cover_mass_coeff * self.rated_power_kw + self.nacelle_cover_mass_intercept
        )

    def calculate_nacelle_cover_cost(self):
        """Calculates and sets :py:attr:`nacelle_cover_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`nacelle_cover_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`nacelle_cover_mass` (:math:`kg`).

        Args:
            nacelle_cover_mass_cost_coeff (float): Nacelle cover cost per kilogram (USD/kg).
            nacelle_cover_mass (float): Nacelle cover mass (kg). See
                :py:meth:`calculate_nacelle_cover_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("nacelle_cover_cost")
        if exists:
            return

        self.nacelle_cover_cost = self.nacelle_cover_mass_cost_coeff * self.nacelle_cover_mass

    def calculate_platform_mainframe_mass(self):
        r"""Calculates and sets :py:attr:`platform_mainframe_mass` if it was not provided by the
        user.

        .. math::
            k * m_{bedplate} + \\left\\{
                \begin{array}{ll}
                m_{crane} & has\\_crane \\
                0 & otherwise \\
            \\end{array}
            \right.

        where:

        - :math:`k =` :py:attr:`platform_mainframe_mass_coeff`
        - :math:`m_{bedplate} =` :py:attr:`bedplate_mass`
        - :math:`m_{crane} =` :py:attr:`crane_mass`
        - :math:`has\\_crane =` :py:attr:`has_crane`

        Args:
            has_crane (bool): If True, apply :py:attr:`crane_mass`, otherwise ignore.
            platform_mainframe_mass_coeff (float): :math:`k` in the mass equation above.
            bedplate_mass (float): Bedplate mass (:math:`kg`). See
                :py:meth:`calculate_bedplate_mass` for details.
            crane_mass (bool): Mass of onboard crane, if :py:attr:`has_crane`, :math:`b` in the
                mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("platform_mainframe_mass")
        if exists:
            return

        self.platform_mainframe_mass = (
            self.platform_mainframe_mass_coeff * self.bedplate_mass
            + int(self.has_crane) * self.crane_mass
        )

    def calculate_platform_mainframe_cost(self):
        r"""Calculates and sets :py:attr:`platform_mainframe_cost` if it was not provided by the
        user.

        .. math::
            k * (m_{platform\\_mainframe}
            - \\left\\{
                \begin{array}{ll}
                m_{crane} & has\\_crane \\
                0 & otherwise \\
            \\end{array}
            )
            + \\left\\{
                \begin{array}{ll}
                m_{crane} & has\\_crane \\
                0 & otherwise \\
            \\end{array}
            \right.

        where:

        - :math:`k =` :py:attr:`platform_mainframe_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`platform_mainframe_mass` (:math:`kg`).

        Args:
            has_crane (bool): If True, apply :py:attr:`crane_cost`, otherwise ignore.
            crane_cost (bool): Cost of onboard crane, if :py:attr:`has_crane`, :math:`b` in the
                mass equation above.
            platform_mainframe_mass_cost_coeff (float): Platform mainframe cost per kilogram
                (USD/kg).
            platform_mainframe_mass (float): Platform mainframe mass (kg).
                See :py:meth:`calculate_platform_mainframe_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("platform_mainframe_cost")
        if exists:
            return

        has_crane = int(self.has_crane)
        self.platform_mainframe_cost = (
            self.platform_mainframe_mass_cost_coeff
            * (self.platform_mainframe_mass - has_crane * self.crane_mass)
            + has_crane * self.crane_cost
        )

    def calculate_transformer_mass(self):
        """Calculates and sets :py:attr:`transformer_mass` if it was not provided by the user.

        .. math:: k * power + b

        where:

        - :math:`k =` :py:attr:`transformer_mass_coeff`
        - :math:`power =` :py:attr:`rated_power_kw`
        - :math:`b =` :py:attr:`transformer_mass_intercept`

        Args:
            transformer_mass_coeff (float): :math:`k` in the mass equation above (:math:`kg/kW`).
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
            transformer_mass_intercept (bool): :math:`b` in the mass equation above (:math:`kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("transformer_mass")
        if exists:
            return

        self.transformer_mass = (
            self.transformer_mass_coeff * self.rated_power_kw + self.transformer_mass_intercept
        )

    def calculate_transformer_cost(self):
        """Calculates and sets :py:attr:`transformer_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`transformer_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`transformer_mass` (:math:`kg`).

        Args:
            transformer_mass_cost_coeff (float): Transformer cost per kilogram (USD/kg).
            transformer_mass (float): Transformer mass (kg). See
                :py:meth:`calculate_transformer_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("transformer_cost")
        if exists:
            return

        self.transformer_cost = self.transformer_mass_cost_coeff * self.transformer_mass

    def calculate_controls_mass(self):
        """Calculates and sets the :py:attr:`controls_mass` if it was not provided by the user.

        Currently sets the value to 0 as there is no base relationship.
        """
        exists = self._prepare_calculation("controls_mass")
        if exists:
            return

        self.controls_mass = 0.0

    def calculate_controls_cost(self):
        r"""Calculates and sets :py:attr:`controls_cost` if it was not provided by the user.

        .. math:: k * rated\_power

        where:

        - :math:`k =` :py:attr:`controls_rated_power_cost_coeff` (:math:`USD/kW`)
        - :math:`m =` :py:attr:`rated_power` (:math:`kW`).

        Args:
            controls_rated_power_cost_coeff (float): Controls cost per kW of capacity (USD/kW).
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("controls_cost")
        if exists:
            return

        self.controls_cost = self.controls_rated_power_cost_coeff * self.rated_power_kw

    def calculate_converter_mass(self):
        """Calculates and sets the :py:attr:`converter_mass` if it was not provided by the user.

        Currently sets the value to 0 as there is no base relationship.
        """
        exists = self._prepare_calculation("converter_mass")
        if exists:
            return

        self.converter_mass = 0.0

    def calculate_converter_cost(self):
        """Calculates and sets :py:attr:`converter_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`converter_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`converter_mass` (:math:`kg`).

        Args:
            converter_mass_cost_coeff (float): Power converter cost per kilogram (USD/kg).
            converter_mass (float): Power converter mass (kg). See
                :py:meth:`calculate_converter_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("converter_cost")
        if exists:
            return

        self.converter_cost = self.converter_mass_cost_coeff * self.converter_mass

    def calculate_electrical_connection_mass(self):
        """Calculates and sets the :py:attr:`electrical_connection_mass` if it was not provided by
        the user.

        Currently sets the value to 0 as there is no base relationship.
        """
        exists = self._prepare_calculation("electrical_connection_mass")
        if exists:
            return

        self.electrical_connection_mass = 0.0

    def calculate_electrical_connection_cost(self):
        r"""Calculates and sets :py:attr:`electrical_connection_cost` if it was not provided by the
        user.

        .. math:: k * rated\_power

        where:

        - :math:`k =` :py:attr:`electrical_connection_rated_power_cost_coeff` (:math:`USD/kW`)
        - :math:`m =` :py:attr:`rated_power` (:math:`kW`).

        Args:
            electrical_connection_rated_power_cost_coeff (float): Electrical connection cost per
                kW of capacity (USD/kW).
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("electrical_connection_cost")
        if exists:
            return

        self.electrical_connection_cost = (
            self.electrical_connection_rated_power_cost_coeff * self.rated_power_kw
        )

    def calculate_tower_mass(self):
        """Calculates and sets :py:attr:`tower_mass` if it was not provided by the user.

        .. math:: k * H_{hub}^b

        where:

        - :math:`k =` :py:attr:`tower_mass_coeff`
        - :math:`H_{hub} =` :py:attr:`hub_height`
        - :math:`b =` :py:attr:`tower_mass_exp`

        Args:
            tower_mass_coeff (float): :math:`k` in the mass equation above (:math:`kg/m`).
            tower_length (float): For onshore turbines, this is the hub height (total length above
                ground). For offshore turbines, this is length from transition piece to hub height
                (:math:`m`).
            tower_mass_exp (bool): :math:`b` in the mass equation above (:math:`kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("tower_mass")
        if exists:
            return

        self.tower_mass = self.tower_mass_coeff * self.tower_length**self.tower_mass_exp

    def calculate_tower_cost(self):
        """Calculates and sets :py:attr:`tower_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`tower_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`tower_mass` (:math:`kg`).

        Args:
            tower_mass_cost_coeff (float): Tower cost per kilogram (USD/kg).
            tower_mass (float): Tower mass (kg). See
                :py:meth:`calculate_tower_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("tower_cost")
        if exists:
            return

        self.tower_cost = self.tower_mass_cost_coeff * self.tower_mass

    def calculate_nacelle_mass(self):
        """Calculates and sets :py:attr:`nacelle_mass` (:math:`kg`) if it was not provided by the
        user.

        Sum of all above-tower components, excluding the blades (:py:meth:`calculate_rotor_mass`)
        and hub (:py:meth:`calculate_hub_system_mass`):

        - :py:attr:`low_speed_shaft_mass`
        - :py:attr:`bearing_mass` * :py:attr:`num_bearings`
        - :py:attr:`gearbox_mass`
        - :py:attr:`brake_mass`
        - :py:attr:`high_speed_shaft_mass`
        - :py:attr:`generator_mass`
        - :py:attr:`bedplate_mass`
        - :py:attr:`yaw_system_mass`
        - :py:attr:`hydraulic_cooling_mass`
        - :py:attr:`nacelle_cover_mass`
        - :py:attr:`platform_mainframe_mass`
        - :py:attr:`transformer_mass`
        - :py:attr:`controls_mass`
        - :py:attr:`converter_mass`
        - :py:attr:`electrical_connection_mass`

        Args:
            low_speed_shaft_mass (float): See :py:meth:`calculate_low_speed_shaft_mass` for more
                details.
            num_bearings (float): Number of main bearings (:py:attr:`num_bearings`).
            bearing_mass (float): See :py:meth:`calculate_bearing_mass` for more details.
            gearbox_mass (float): See :py:meth:`calculate_gearbox_mass` for more details.
            brake_mass (float): See :py:meth:`calculate_brake_mass` for more details.
            high_speed_shaft_mass (float): See :py:meth:`calculate_high_speed_shaft_mass` for
                more details.
            generator_mass (float): See :py:meth:`calculate_generator_mass` for more details.
            bedplate_mass (float): See :py:meth:`calculate_bedplate_mass` for more details.
            yaw_system_mass (float): See :py:meth:`calculate_yaw_system_mass` for more details.
            hydraulic_cooling_mass (float): See :py:meth:`calculate_hydraulic_cooling_mass` for
                more details.
            nacelle_cover_mass (float): See :py:meth:`calculate_nacelle_cover_mass` for more
                details.
            platform_mainframe_mass (float): See :py:meth:`calculate_platform_mainframe_mass` for
                more details.
            transformer_mass (float): See :py:meth:`calculate_transformer_mass` for more details.
            controls_mass (float): See :py:meth:`calculate_controls_mass` for more details.
            converter_mass (float): See :py:meth:`calculate_converter_mass` for more details.
            electrical_connection_mass (float): See
                :py:meth:`calculate_electrical_connection_mass` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("nacelle_mass")
        if exists:
            return

        self.nacelle_mass = sum(
            (
                self.low_speed_shaft_mass,
                self.num_bearings * self.bearing_mass,
                self.gearbox_mass,
                self.brake_mass,
                self.high_speed_shaft_mass,
                self.generator_mass,
                self.bedplate_mass,
                self.yaw_system_mass,
                self.hydraulic_cooling_mass,
                self.nacelle_cover_mass,
                self.platform_mainframe_mass,
                self.transformer_mass,
                self.controls_mass,
                self.converter_mass,
                self.electrical_connection_mass,
            )
        )

    def calculate_nacelle_cost(self):
        """Calculates and sets :py:attr:`nacelle_cost`  (USD) if it was not provided by the user.

        Sum of all above-tower components, excluding the blades (:py:meth:`calculate_rotor_cost`)
        and hub (:py:meth:`calculate_hub_system_cost`):

        - :py:attr:`low_speed_shaft_cost`
        - :py:attr:`bearing_cost` * :py:attr:`num_bearings`
        - :py:attr:`gearbox_cost`
        - :py:attr:`brake_cost`
        - :py:attr:`high_speed_shaft_cost`
        - :py:attr:`generator_cost`
        - :py:attr:`bedplate_cost`
        - :py:attr:`yaw_system_cost`
        - :py:attr:`hydraulic_cooling_cost`
        - :py:attr:`nacelle_cover_cost`
        - :py:attr:`platform_mainframe_cost`
        - :py:attr:`transformer_cost`
        - :py:attr:`controls_cost`
        - :py:attr:`converter_cost`
        - :py:attr:`electrical_connection_cost`

        Args:
            low_speed_shaft_cost (float): See :py:meth:`calculate_low_speed_shaft_cost` for more
                details.
            num_bearings (float): Number of main bearings (:py:attr:`num_bearings`).
            bearing_cost (float): See :py:meth:`calculate_bearing_cost` for more details.
            gearbox_cost (float): See :py:meth:`calculate_gearbox_cost` for more details.
            brake_cost (float): See :py:meth:`calculate_brake_cost` for more details.
            high_speed_shaft_cost (float): See :py:meth:`calculate_high_speed_shaft_cost` for
                more details.
            generator_cost (float): See :py:meth:`calculate_generator_cost` for more details.
            bedplate_cost (float): See :py:meth:`calculate_bedplate_cost` for more details.
            yaw_system_cost (float): See :py:meth:`calculate_yaw_system_cost` for more details.
            hydraulic_cooling_cost (float): See :py:meth:`calculate_hydraulic_cooling_cost` for
                more details.
            nacelle_cover_cost (float): See :py:meth:`calculate_nacelle_cover_cost` for more
                details.
            platform_mainframe_cost (float): See :py:meth:`calculate_platform_mainframe_cost` for
                more details.
            transformer_cost (float): See :py:meth:`calculate_transformer_cost` for more details.
            controls_cost (float): See :py:meth:`calculate_controls_cost` for more details.
            converter_cost (float): See :py:meth:`calculate_converter_cost` for more details.
            electrical_connection_cost (float): See
                :py:meth:`calculate_electrical_connection_cost` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("nacelle_cost")
        if exists:
            return

        self.nacelle_cost = sum(
            (
                self.low_speed_shaft_cost,
                self.num_bearings * self.bearing_cost,
                self.gearbox_cost,
                self.brake_cost,
                self.high_speed_shaft_cost,
                self.generator_cost,
                self.bedplate_cost,
                self.yaw_system_cost,
                self.hydraulic_cooling_cost,
                self.nacelle_cover_cost,
                self.platform_mainframe_cost,
                self.transformer_cost,
                self.controls_cost,
                self.converter_cost,
                self.electrical_connection_cost,
            )
        )

    def calculate_hub_system_mass(self):
        """Calculates and sets :py:attr:`hub_system_mass` (:math:`kg`) if it was not provided by the
        user.

        Sum of the following components:

        - :py:attr:`hub_mass`
        - :py:attr:`pitch_system_mass`
        - :py:attr:`spinner_mass`

        Args:
            hub_mass (float): See :py:meth:`calculate_hub_mass` for more details.
            pitch_system_mass (float): See :py:meth:`calculate_pitch_system_mass` for more
                details.
            spinner_mass (float): See :py:meth:`calculate_spinner_mass` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("hub_system_mass")
        if exists:
            return

        self.hub_system_mass = sum((self.hub_mass, self.pitch_system_mass, self.spinner_mass))

    def calculate_hub_system_cost(self):
        """Calculates and sets :py:attr:`hub_system_cost`  (USD) if it was not provided by the user.

        Sum of the following components:

        - :py:attr:`hub_cost`
        - :py:attr:`pitch_system_cost`
        - :py:attr:`spinner_cost`

        Args:
            hub_cost (float): See :py:meth:`calculate_hub_cost` for more details.
            pitch_system_cost (float): See :py:meth:`calculate_pitch_system_cost` for more
                details.
            spinner_cost (float): See :py:meth:`calculate_spinner_cost` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("hub_system_cost")
        if exists:
            return

        self.hub_system_cost = sum(
            (
                self.hub_cost,
                self.pitch_system_cost,
                self.spinner_cost,
            )
        )

    def calculate_rotor_mass(self):
        """Calculates and sets :py:attr:`rotor_mass` (:math:`kg`) if it was not provided by the
        user.

        Sum of the blades and hub system (:py:meth:`calculate_hub_system_mass`):

        Args:
            num_blades (float): Number of turbine blades (:py:attr:`num_blades`).
            blade_mass (float): See :py:meth:`calculate_blade_mass` for more details.
            hub_system_mass (float): See :py:meth:`calculate_hub_system_mass` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("rotor_mass")
        if exists:
            return

        self.rotor_mass = self.num_blades * self.blade_mass + self.hub_system_mass

    def calculate_rotor_cost(self):
        """Calculates and sets :py:attr:`rotor_cost` (:math:`kg`) if it was not provided by the
        user.

        Sum of the blades and hub system (:py:meth:`calculate_hub_system_cost`):

        Args:
            num_blades (float): Number of turbine blades (:py:attr:`num_blades`).
            blade_cost (float): See :py:meth:`calculate_blade_cost` for more details.
            hub_system_cost (float): See :py:meth:`calculate_hub_system_cost` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("rotor_cost")
        if exists:
            return

        self.rotor_cost = self.num_blades * self.blade_cost + self.hub_system_cost

    def calculate_turbine_mass(self):
        """Calculates and sets :py:attr:`turbine_mass` (:math:`kg`) if it was not provided by the
        user.

        Sum of the :py:attr:`rotor_mass` (:py:attr:`calculate_rotor_mass`),
        :py:attr:`hub_system_mass` (:py:attr:`calculate_hub_system_mass`),
        :py:attr:`nacelle_mass` (:py:attr:`calculate_nacelle_mass`), and
        :py:attr:`tower_mass` (:py:attr:`calculate_tower_mass`)

        Args:
            nacelle_mass (float): See :py:meth:`calculate_nacelle_mass` for more details.
            hub_system_mass (float): See :py:meth:`calculate_hub_system_mass` for more details.
            rotor_mass (float): See :py:meth:`calculate_rotor_mass` for more details.
            tower_mass (float): See :py:meth:`calculate_tower_mass` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("turbine_mass")
        if exists:
            return

        self.turbine_mass = self.nacelle_mass + self.rotor_mass + self.tower_mass

    def calculate_turbine_cost(self):
        """Calculates and sets :py:attr:`turbine_cost` (:math:`kg`) if it was not provided by the
        user.

        Sum of the :py:attr:`rotor_cost` (:py:attr:`calculate_rotor_cost`),
        :py:attr:`hub_system_cost` (:py:attr:`calculate_hub_system_cost`),
        :py:attr:`nacelle_cost` (:py:attr:`calculate_nacelle_cost`), and
        :py:attr:`tower_cost` (:py:attr:`calculate_tower_cost`)

        Args:
            nacelle_cost (float): See :py:meth:`calculate_nacelle_cost` for more details.
            hub_system_cost (float): See :py:meth:`calculate_hub_system_cost` for more details.
            rotor_cost (float): See :py:meth:`calculate_rotor_cost` for more details.
            tower_cost (float): See :py:meth:`calculate_tower_cost` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("turbine_cost")
        if exists:
            return

        self.turbine_cost = self.nacelle_cost + self.rotor_cost + self.tower_cost
        self.turbine_cost_kw = self.turbine_cost / self.rated_power_kw

    def calculate_subsystem_mass(self):
        """Runs all the mass calculations for the non-aggregated turbine subsytems."""
        self.calculate_blade_mass()
        self.calculate_hub_mass()
        self.calculate_pitch_system_mass()
        self.calculate_spinner_mass()
        self.calculate_low_speed_shaft_mass()
        self.calculate_bearing_mass()
        self.calculate_rotor_torque()
        self.calculate_gearbox_mass()
        self.calculate_brake_mass()
        self.calculate_high_speed_shaft_mass()
        self.calculate_generator_mass()
        self.calculate_bedplate_mass()
        self.calculate_yaw_system_mass()
        self.calculate_hydraulic_cooling_mass()
        self.calculate_nacelle_cover_mass()
        self.calculate_platform_mainframe_mass()
        self.calculate_transformer_mass()
        self.calculate_converter_mass()
        self.calculate_controls_mass()
        self.calculate_electrical_connection_mass()
        self.calculate_tower_mass()

    def calculate_subsystem_cost(self):
        """Runs all the cost calculations for the non-aggregated turbine subsystems."""
        self.calculate_blade_cost()
        self.calculate_hub_cost()
        self.calculate_pitch_system_cost()
        self.calculate_spinner_cost()
        self.calculate_low_speed_shaft_cost()
        self.calculate_bearing_cost()
        self.calculate_gearbox_cost()
        self.calculate_brake_cost()
        self.calculate_high_speed_shaft_cost()
        self.calculate_generator_cost()
        self.calculate_bedplate_cost()
        self.calculate_yaw_system_cost()
        self.calculate_hydraulic_cooling_cost()
        self.calculate_nacelle_cover_cost()
        self.calculate_platform_mainframe_cost()
        self.calculate_transformer_cost()
        self.calculate_converter_cost()
        self.calculate_controls_cost()
        self.calculate_electrical_connection_cost()
        self.calculate_tower_cost()

    def calculate_system_mass(self):
        """Calculates the mass for all aggregate turbine systems."""
        self.calculate_nacelle_mass()
        self.calculate_hub_system_mass()
        self.calculate_rotor_mass()
        self.calculate_turbine_mass()

    def calculate_system_cost(self):
        """Calculates the cost for all aggregate turbine systems."""
        self.calculate_nacelle_cost()
        self.calculate_hub_system_cost()
        self.calculate_rotor_cost()
        self.calculate_turbine_cost()

    def run(self):
        """Run the mass and cost calculations."""
        self._calculate_subsystem_mass()
        self._calculate_system_mass()
        self._calculate_subsystem_cost()
        self._calculate_system_costs()

    @classmethod
    def _get_attr_map(
        cls, *, both_as_separate: bool = False, include_units: bool = False
    ) -> dict[str, Any]:
        """Creates an dictionary attribute mapping of model attribute name to either default value
        or a dictionary of default value and units (when :py:attr:`include_units` is True). Use of
        False for :py:attr:`both_as_separate` and True for :py:attr:`include_units` are geared
        towards WISDEM use cases.

        Args:
            both_as_separate (bool, optional): Model attributes marked as "both" in their attribute
                metadata `io` field will be included in the "both" key. If False, the attribute and
                its value(s) will be include in both the "inputs" and "outputs" values. Defaults to
                False.
            include_units (bool, optional): Include the attribute's units in the attribute's values
                or just the default value (False). Defaults to False.

        Returns:-
            dict[str, Any]: Dictionary of "inputs", "outputs", and optionally "both (when
                :py:attr:`both_as_separate` is True). Each of the corresponding dictionaries will
                have keys of model attribute name and values of either the default value or a
                dictionary of "default" and "units" with their respective values.
        """
        attr_map = {"inputs": {}, "outputs": {}}
        if both_as_separate:
            attr_map["both"] = {}
        for f in fields(cls):
            meta = f.metadata
            if (_io := meta.get("io")) is None:
                continue
            name = f.name
            default = f.default
            val = {"default": default, "units": meta["units"]} if include_units else default
            match _io:
                case "input":
                    attr_map["inputs"][name] = val
                case "output":
                    attr_map["outputs"][name] = val
                case "both":
                    if both_as_separate:
                        attr_map["both"][name] = val
                    else:
                        attr_map["inputs"][name] = val
                        attr_map["outputs"][name] = val
        return attr_map

    def get_results(self) -> dict[str, float]:
        """Gathers the core results."""
        results = {
            "blade_mass": self.blade_mass,
            "blade_cost": self.blade_cost,
            "hub_mass": self.hub_mass,
            "hub_cost": self.hub_cost,
            "pitch_system_mass": self.pitch_system_mass,
            "pitch_system_cost": self.pitch_system_cost,
            "spinner_mass": self.spinner_mass,
            "spinner_cost": self.spinner_cost,
            "low_speed_shaft_mass": self.low_speed_shaft_mass,
            "low_speed_shaft_cost": self.low_speed_shaft_cost,
            "bearing_mass": self.bearing_mass,
            "bearing_cost": self.bearing_cost,
            "rated_rpm": self.rated_rpm,
            "rotor_torque": self.rotor_torque,
            "gearbox_mass": self.gearbox_mass,
            "gearbox_cost": self.gearbox_cost,
            "brake_mass": self.brake_mass,
            "brake_cost": self.brake_cost,
            "high_speed_shaft_mass": self.high_speed_shaft_mass,
            "high_speed_shaft_cost": self.high_speed_shaft_cost,
            "generator_mass": self.generator_mass,
            "generator_cost": self.generator_cost,
            "bedplate_mass": self.bedplate_mass,
            "bedplate_cost": self.bedplate_cost,
            "yaw_system_mass": self.yaw_system_mass,
            "yaw_system_cost": self.yaw_system_cost,
            "hydraulic_cooling_mass": self.hydraulic_cooling_mass,
            "hydraulic_cooling_cost": self.hydraulic_cooling_cost,
            "nacelle_cover_mass": self.nacelle_cover_mass,
            "nacelle_cover_cost": self.nacelle_cover_cost,
            "platform_mainframe_mass": self.platform_mainframe_mass,
            "platform_mainframe_cost": self.platform_mainframe_cost,
            "transformer_mass": self.transformer_mass,
            "transformer_cost": self.transformer_cost,
            "converter_mass": self.converter_mass,
            "converter_cost": self.converter_cost,
            "controls_mass": self.controls_mass,
            "controls_cost": self.controls_cost,
            "electrical_connection_mass": self.electrical_connection_mass,
            "electrical_connection_cost": self.electrical_connection_cost,
            "tower_mass": self.tower_mass,
            "tower_cost": self.tower_cost,
            "nacelle_mass": self.nacelle_mass,
            "nacelle_cost": self.nacelle_cost,
            "hub_system_mass": self.hub_system_mass,
            "hub_system_cost": self.hub_system_cost,
            "rotor_mass": self.rotor_mass,
            "rotor_cost": self.rotor_cost,
            "turbine_mass": self.turbine_mass,
            "turbine_cost": self.turbine_cost,
            "turbine_cost_kw": self.turbine_cost_kw,
        }
        return results

    def get_mass_results(self) -> dict[str, float]:
        """Gathers all the mass-specific outputs into a dictionary of attribute: value."""
        results = {
            "blade_mass": self.blade_mass,
            "hub_mass": self.hub_mass,
            "pitch_system_mass": self.pitch_system_mass,
            "spinner_mass": self.spinner_mass,
            "low_speed_shaft_mass": self.low_speed_shaft_mass,
            "bearing_mass": self.bearing_mass,
            "gearbox_mass": self.gearbox_mass,
            "brake_mass": self.brake_mass,
            "high_speed_shaft_mass": self.high_speed_shaft_mass,
            "generator_mass": self.generator_mass,
            "bedplate_mass": self.bedplate_mass,
            "yaw_system_mass": self.yaw_system_mass,
            "hydraulic_cooling_mass": self.hydraulic_cooling_mass,
            "nacelle_cover_mass": self.nacelle_cover_mass,
            "platform_mainframe_mass": self.platform_mainframe_mass,
            "transformer_mass": self.transformer_mass,
            "converter_mass": self.converter_mass,
            "controls_mass": self.controls_mass,
            "electrical_connection_mass": self.electrical_connection_mass,
            "tower_mass": self.tower_mass,
            "nacelle_mass": self.nacelle_mass,
            "hub_system_mass": self.hub_system_mass,
            "rotor_mass": self.rotor_mass,
            "turbine_mass": self.turbine_mass,
        }
        return results

    def get_cost_results(self) -> dict[str, float]:
        """Gathers all the cost-specific outputs into a dictionary of attribute: value."""
        results = {
            "blade_cost": self.blade_cost,
            "hub_cost": self.hub_cost,
            "pitch_system_cost": self.pitch_system_cost,
            "spinner_cost": self.spinner_cost,
            "low_speed_shaft_cost": self.low_speed_shaft_cost,
            "bearing_cost": self.bearing_cost,
            "gearbox_cost": self.gearbox_cost,
            "brake_cost": self.brake_cost,
            "high_speed_shaft_cost": self.high_speed_shaft_cost,
            "generator_cost": self.generator_cost,
            "bedplate_cost": self.bedplate_cost,
            "yaw_system_cost": self.yaw_system_cost,
            "hydraulic_cooling_cost": self.hydraulic_cooling_cost,
            "nacelle_cover_cost": self.nacelle_cover_cost,
            "platform_mainframe_cost": self.platform_mainframe_cost,
            "transformer_cost": self.transformer_cost,
            "converter_cost": self.converter_cost,
            "controls_cost": self.controls_cost,
            "electrical_connection_cost": self.electrical_connection_cost,
            "tower_cost": self.tower_cost,
            "nacelle_cost": self.nacelle_cost,
            "hub_system_cost": self.hub_system_cost,
            "rotor_cost": self.rotor_cost,
            "turbine_cost": self.turbine_cost,
            "turbine_cost_kw": self.turbine_cost_kw,
        }
        return results

    def irs_mpc_breakdown(  # noqa: D417
        self,
        turbine_production_cost: float,
        tower_flange_material_cost: float,
        tower_flange_production_cost: float,
        *,
        with_category: bool = False,
    ) -> pd.DataFrame:
        """Calculates the base cost breakdown for the United States IRS manufactured product
        component tables.

        Component mapping is as follows:

        - Wind turbine
          - Blades: model-calculated :py:attr:`blade_cost`. See :py:meth:`calculate_blade_cost`
            for complete details.
          - Rotor Hub: model-calculated :py:attr:`hub_cost`. See :py:meth:`calculate_hub_cost`
            for complete details.
          - Nacelle: model-calculated :py:attr:`nacelle_cost`.
            See :py:meth:`calculate_nacelle_cost for complete details.
          - Power Converter: model-calculated :py:attr:`converter_cost`. See
            :py:meth:`calculate_converter_cost` for complete details.
          - Production: user-provided :py:attr:`turbine_production_cost`
        - Wind Tower Flanges
          - Material: user-provided :py:attr:`tower_flange_material_cost`
          - Production: user-provided :py:attr:`tower_flange_production_cost`
        - Tower: not counted steel or iron product
        - Steel or iron productions in foundation: not counted steel or iron product

        Args:
            turbine_production_cost (float): Costs associated with production (i.e., not materials)
                of the wind turbine.
            tower_flange_material_cost (float): The materials cost for the tower flange.
            tower_flange_production_cost (float): The production cost for the tower flange.
            with_category (bool, optional: If True, return the DataFrame with the ``category``
                column intact, otherwise drop the column to produce an IRS-ready output. Defaults
                to False.

        Returns:-
            pd.DataFrame: Data Frame with indices for the APCs and MPCs, and columns for the
                mapping category (if :py:attr:`with_category`), "cost" (total USD), and "Value"
                (component cost / total cost * 100).
        """
        costs = {
            "blade": self.blade_cost,
            "hub": self.hub_cost,
            "nacelle": self.nacelle_cost,
            "power_converter": self.converter_cost,
            "turbine_production": turbine_production_cost,
            "tower_flange_material": tower_flange_material_cost,
            "tower_flange_production": tower_flange_production_cost,
        }
        apc_map = {
            "blade": "Wind Turbine",
            "hub": "Wind Turbine",
            "nacelle": "Wind Turbine",
            "power_converter": "Wind Turbine",
            "turbine_production": "Wind Turbine",
            "tower_flange_material": "Wind Tower Flange",
            "tower_flange_production": "Wind Tower Flange",
        }
        mpc_map = {
            "blade": "Blade",
            "hub": "Hub",
            "nacelle": "Nacelle",
            "power_converter": "Power Converter",
            "turbine_production": "Production",
            "tower_flange_material": "Material",
            "tower_flange_production": "Production",
        }
        breakdown = pd.DataFrame.from_dict(costs, orient="index", columns=["cost"])
        breakdown.index.name = "category"
        breakdown = breakdown.assign(
            Value=breakdown.cost / breakdown.cost.sum() * 100,
            APC=breakdown.index.str.replace(apc_map),
            MPC=breakdown.index.str.replace(mpc_map),
        )
        breakdown = breakdown.reset_index(drop=False).set_index(["APC", "MPC"])

        total = breakdown.sum().to_frame(name="Total").T.set_index(pd.Index(["-"]), append=True)
        total.index.names = ["APC", "MPC"]
        total.loc[("Total", "-"), "category"] = "-"

        empty = ["-", 0.0, 0.0]
        steel_ix = pd.MultiIndex.from_arrays(
            [["Tower", "Steel or iron products in foundation"], ["-", "-"]], names=("APC", "MPC")
        )
        steel = pd.DataFrame([empty, empty], columns=breakdown.columns, index=steel_ix)

        breakdown = pd.concat((breakdown, steel, total))
        if with_category:
            return breakdown
        return breakdown.replace(0, "-").drop(columns=["category"])

    def total_domestic_content(
        self,
        turbine_production_cost: float,
        tower_flange_material_cost: float,
        tower_flange_production_cost: float,
        domestic: list[str],
        *,
        return_table: bool = False,
    ) -> float | pd.DataFrame:
        """Calculates the total, valid domestic content production percentage based on the domestic
        or allowed-foreign entity produced components provided in :py:attr:`domestic` that align
        with :py:meth:`irs_mpc_breakdown`.

        Note:
            MPC domestic content only counts towards the domestic content production percentage if
            all of the MPCs in an APC have been domestically produced. See IRS notices 2023-38 and
            2026-15 for complete details prior to calculation of the final proportion.

        Args:
            turbine_production_cost (float): Costs associated with production (i.e., not materials)
                of the wind turbine.
            tower_flange_material_cost (float): The materials cost for the tower flange.
            tower_flange_production_cost (float): The production cost for the tower flange.
            domestic (list[str]): List of the components aligning with the ``category`` column
                of :py:meth:`irs_mpc_breakdown`.
            return_table (bool, optional): If True, return the DataFrame from
                :py:meth:`irs_mpc_breakdown` with the additional column ``Domestic`` that shows
                the total domestic content percentage the counts for the IRS domestic content
                production calculation. Defaults to False.

        Returns:-
            float | pd.DataFrame: Returns the total valid domestic content as a percent, or the
                DataFrame breakdown by category.
        """
        breakdown = self.irs_mpc_breakdown(
            turbine_production_cost=turbine_production_cost,
            tower_flange_material_cost=tower_flange_material_cost,
            tower_flange_production_cost=tower_flange_production_cost,
            with_category=True,
        )
        domestic_map = dict.fromkeys(breakdown.category, 0)
        domestic_map |= dict.fromkeys(domestic, 1)
        breakdown = breakdown.assign(Domestic=breakdown.category.map(domestic_map))

        for apc in ("Wind Turbine", "Wind Tower Flange"):
            component = breakdown.loc[apc, "Domestic"]
            if component.size != component.sum():
                breakdown.loc[apc, "Domestic"] = 0.0

        breakdown.Domestic = breakdown.Domestic * (breakdown.Value / 100)
        breakdown.loc["Total", "Domestic"] = breakdown.Domestic.sum()
        breakdown.Domestic *= 100
        if return_table:
            return breakdown
        return breakdown.loc["Total", "Domestic"].squeeze()
