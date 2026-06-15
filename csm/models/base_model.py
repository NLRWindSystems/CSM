"""Provides the ``CSMBase`` base model, which serves as the basis for all inputs and outputs
that subsequent subclasses will use.

New models should take the following form to implement
model-specific defaults while maintaining all input validation, metadata, and functionality from
the base model.

```python
from attrs import define, fields

from csm.models.base_model import CSMBase

base = fields(CSMBase)

@define
class CustomModel(CSMBase):
    rotor_efficiency_max: float = base.rotor_efficiency_max.evolve(default=1.0)
```
"""

import math
from typing import Any
from collections.abc import Generator

import pandas as pd
from attrs import field, define, fields

from csm.models.utils import create_field


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
            :py:method:`calculate_blade_mass`.
        blade_has_carbon (bool): Use True if the blade has carbon, False if not.
        blade_mass_cost_coeff (float): Blade cost per kilogram (USD/kg).
        blade_mass (float): Blade mass (kg).
        hub_mass_coeff (float): :math:`k` in the hub mass equation from
            :py:method:`calculate_hub_mass`.
        hub_mass_intercept (bool): :math:`b` in the hub mass equation from
            :py:method:`calculate_hub_mass`.
        hub_mass_cost_coeff (float): Hub cost per kilogram (USD/kg) from
            :py:method:`calculate_hub_cost`.
        pitch_bearing_mass_coeff (float): :math:`k` in the pitch bearing mass equation from
            :py:method:`calculate_pitch_system_mass`.
        pitch_bearing_mass_intercept (float): :math:`b1` in the pitch bearing mass equation from
            :py:method:`calculate_pitch_system_mass`.
        bearing_housing_fraction (float): Mass of the housing for the bearing as a fraction of
            the bearing mass. :math:`h` in the pitch system mass equation from
            :py:method:`calculate_pitch_system_mass`.
        mass_sys_offset (float): :math:`b2` in the pitch system mass equation from
            :py:method:`calculate_pitch_system_mass`.
        pitch_system_mass_cost_coeff (float): Pitch system cost per kilogram (USD/kg) from
            :py:method:`calculate_pitch_system_cost`.
        spinner_mass_coeff (float): :math:`k` in the mass equation above from
            :py:method:`calculate_spinner_mass`.
        spinner_mass_intercept (bool): :math:`b` in the mass equation above from
            :py:method:`calculate_spinner_mass`.
        spinner_mass_cost_coeff (float): Spinner cost per kilogram (USD/kg) from
            :py:method:`calculate_spinner_cost`.
        lss_mass_coeff (float): :math:`k` in the low speed shaft mass equation from
            :py:method:`calculate_low_speed_shaft_mass`.
        lss_mass_exp (float): :math:`b1` in the low speed shaft mass equation from
            :py:method:`calculate_low_speed_shaft_mass`.
        lss_mass_intercept (float): :math:`b2` in the low speed shaft mass equation from
            :py:method:`calculate_low_speed_shaft_mass`.
        lss_mass_cost_coeff (float): Low speed shaft cost per kilogram (USD/kg).
        bearing_mass_coeff (float): :math:`k` in the bearing mass equation from
            :py:method:`calculate_bearing_mass`.
        bearing_mass_exp (bool): :math:`b` in the bearing mass equation from
            :py:method:`calculate_bearing_mass`.
        bearing_mass_cost_coeff (float): Main bearing cost per kilogram (USD/kg).
        efficiency_max (float): Maximum possible drivetrain efficiency.
        max_tip_speed (float): Maximum allowable blade tip speed (:math:`m/s`).
        gearbox_torque_density (float): Gearbox torque per kilogram of mass from
            :py:method:`calculate_gearbox_mass` and :py:method:`calculate_gearbox_cost`
            (:math:`N*m/kg`).
        gearbox_torque_cost (float): Gearbox cost per unit of torque (:math:`USD/kN/m`) from
            :py:method:`calculate_gearbox_cost`.
        brake_mass_coeff (bool): :math:`k` in the brake mass equation from
            :py:method:`calculate_brake_mass`.
        brake_mass_cost_coeff (float): Brake cost per kilogram (USD/kg).
        rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
        hss_mass_coeff (float): Mass scaling coefficient, :math:`k` in the mass equation.
        hss_mass_cost_coeff (float): High speed shaft cost, per kilogram of mass, :math:`k` in the
            equation above (:math:`USD/kg`).
        generator_mass_coeff (float): :math:`k` in the generator mass equation above (:math:`kg/kW`)
            from :py:method:`calculate_generator_mass`.
        generator_mass_intercept (bool): :math:`b` in the generator mass equation above (:math:`kg`)
            from :py:method:`calculate_generator_mass`.
        generator_mass_cost_coeff (float): generator cost per kilogram (USD/kg).
        bedplate_mass_exp (bool): :math:`b` in the mass equation from
            :py:method:`calculate_bedplate_mass`.
        bedplate_mass_cost_coeff (float): bedplate cost per kilogram (USD/kg).
        yaw_system_non_bearing_mass_coeff (float): :math:`k1` in the mass equation from
            :py:method:`calculate_yaw_system_mass` to account for non-bearing mass.
        yaw_system_mass_coeff (float): :math:`k2` in the mass equation from
            :py:method:`calculate_yaw_system_mass`.
        yaw_system_mass_exp (bool): :math:`b` in the mass equation from
            :py:method:`calculate_yaw_system_mass`..
        yaw_system_mass_cost_coeff (float): Yaw system cost per kilogram (USD/kg).
        hvac_mass_coeff (float): Mass scaling coefficient. See
            :py:method:`calculate_hydraulic_cooling_mass` for more details.
        hvac_mass_cost_coeff (float): Hydraulic cooling cost, per kilogram of mass.
        nacelle_cover_mass_coeff (float): :math:`k` in the mass equation from
            :py:method:`calculate_nacelle_cover_mass`.
        nacelle_cover_mass_intercept (bool): :math:`b` in the mass equation from
            :py:method:`calculate_nacelle_cover_mass`.
        nacelle_cover_mass_cost_coeff (float): Nacelle cover cost per kilogram (USD/kg).
        platform_mainframe_mass_coeff (float): :math:`k` from
            :py:method:`calculate_platform_mainframe_mass`.
        has_crane (bool): If True, apply :py:attr:`crane_mass` to
            :py:method:`calculate_platform_mainframe_mass` and :py:attr:`crane_cost` to
            :py:method:`calculate_platform_mainframe_cost`, otherwise ignore.
        crane_mass (bool): Mass of onboard crane, if :py:attr:`has_crane`, :math:`m_{crane}` from
            :py:method:`calculate_platform_mainframe_mass`.
        crane_cost (bool): Cost of onboard crane, if :py:attr:`has_crane`, :math:`b` in the
            mass equation above.
        platform_mainframe_mass_cost_coeff (float): Platform mainframe cost per kilogram
            (USD/kg).
        transformer_mass_coeff (float): :math:`k` in the mass equation from
            :py:method:`calculate_transformer_mass`.
        transformer_mass_intercept (bool): :math:`b` in the mass equation from
            :py:method:`calculate_transformer_mass`.
        transformer_mass_cost_coeff (float): Nacelle cover cost per kilogram (USD/kg).
        tower_mass_coeff (float): :math:`k` in the mass from :py:method:`calculate_tower_mass`
            (:math:`kg/m`).
        tower_length (float): For onshore turbines, this is the hub height (total length above
            ground). For offshore turbines, this is length from transition piece to hub height
            (:math:`m`).
        tower_mass_exp (bool): :math:`b` in the mass equation from
            :py:method:`calculate_tower_mass`.
        tower_mass_cost_coeff (float): Tower cover cost per kilogram (USD/kg).

    Attributes:
        blade_mass (float): Blade mass (:math:`kg`). See :py:method:`calculate_blade_mass`
            for details.
        blade_cost (float): Blade cost (USD). See :py:method:`calculate_blade_cost`
            for details.
        hub_mass (float): Hub mass (kg). See :py:method:`calculate_hub_mass`
            for more details.
        hub_cost (float): Hub cost (USD). See :py:method:`calculate_hub_cost`
            for more details.
        pitch_system_mass (float): Pitch system mass (kg). See
            :py:method:`calculate_pitch_system_mass` for more details.
        pitch_system_cost (float): Pitch system cost (USD). See
            :py:method:`calculate_pitch_system_cost for more details.
        spinner_mass (float): Spinner mass (kg). See :py:method:`calculate_spinner_mass`
            for more details.
        spinner_cost (float): Spinner cost (USD). See :py:method:`calculate_spinner_cost`
            for more details.
        low_speed_shaft_mass (float): Low speed shaft mass (kg). See
            :py:method:`calculate_low_speed_shaft_mass` for more details.
        low_speed_shaft_cost (float): Low speed shaft cost (USD). See
            :py:method:`calculate_low_speed_shaft_cost` for more details.
        bearing_mass (float): Main bearing mass (kg). See :py:method:`calculate_bearing_mass`
            for more details.
        bearing_cost (float): Main bearing cost (USD). See :py:method:`calculate_bearing_cost`
            for more details.
        gearbox_mass (float): Gearbox mass (kg). See :py:method:`calculate_gearbox_mass`
            for more details.
        gearbox_cost (float): Gearbox cost (USD). See :py:method:`calculate_gearbox_cost`
            for more details.
        brake_mass (float): Brake mass (kg). See :py:method:`brake_mass` for more details.
        brake_cost (float): Brake cost (USD). See :py:method:`brake_cost` for more details.
        high_speed_shaft_mass (float): High speed shaft mass (kg).
            See :py:method:`high_speed_shaft_mass` for more details.
        high_speed_shaft_cost (float): High speed shaft cost (USD).
            See :py:method:`high_speed_shaft_cost` for more details.
        generator_mass (float): Generator mass (kg). See :py:method:`calculate_generator_mass`
            for more details.
        generator_cost (float): Generator cost (USD). See :py:method:`calculate_generator_cost`
            for more details.
        bedplate_mass (float): Bedplate mass (kg). See :py:method:`calculate_bedplate_mass`
            for more details.
        bedplate_cost (float): Bedplate cost (USD). See :py:method:`calculate_bedplate_cost`
            for more details.
        yaw_system_mass (float): Yaw system mass (kg). See :py:method:`calculate_yaw_system_mass`
            for more details.
        yaw_system_cost (float): Yaw system cost (USD). See :py:method:`calculate_yaw_system_cost`
            for more details.
        hydraulic_cooling_mass (float): Hydraulic cooling mass (kg). See
            :py:method:`calculate_hydraulic_cooling_mass` for more details.
        hydraulic_cooling_cost (float): Hydraulic cooling cost (USD). See
            :py:method:`calculate_hydraulic_cooling_cost` for more details.
        nacelle_cover_mass (float): nacelle_cover mass (kg). See
            :py:method:`calculate_nacelle_cover_mass` for more details.
        nacelle_cover_cost (float): nacelle_cover mass (USD). See
            :py:method:`calculate_nacelle_cover_cost` for more details.
        platform_mainframe_mass (float): Platform mainframe mass (kg).
            See :py:method:`calculate_platform_mainframe_mass` for more details.
        platform_mainframe_cost (float): Platform mainframe cost (USD).
            See :py:method:`calculate_platform_mainframe_cost` for more details.
        transformer_mass (float): Transformer cover mass (kg). See
            :py:method:`calculate_transformer_mass` for more details.
        transformer_cost (float): Transformer cover cost (USD). See
            :py:method:`calculate_transformer_cost` for more details.
        tower_mass (float): Tower mass (kg). See
            :py:method:`calculate_tower_mass` for more details.
        tower_cost (float): Tower cost (USD). See
            :py:method:`calculate_tower_cost` for more details.
        nacelle_mass (float): Total nacelle mass (kg). See
            :py:method:`calculate_nacelle_mass` for more details.
        nacelle_cost (float): Total nacelle cost (US). See
            :py:method:`calculate_nacelle_cost` for more details.
        hub_system_mass (float): Total hub system mass (kg). See
            :py:method:`calculate_hub_system_mass` for more details.
        hub_system_cost (float): Total hub system cost (USD). See
            :py:method:`calculate_hub_system_cost` for more details.
        rotor_mass (float): Total rotor mass (kg). See
            :py:method:`calculate_rotor_mass` for more details.
        rotor_cost (float): Total rotor cost (USD). See
            :py:method:`calculate_rotor_cost` for more details.
        turbine_mass (float): Total turbine mass (kg). See
            :py:method:`calculate_turbine_mass` for more details.
        turbine_cost (float): Total turbine cost (USD). See
            :py:method:`calculate_turbine_cost` for more details.
        turbine_cost (float): Total turbine cost, normalized by
            :py:attr:`rated_power_kw` (USD/kW).
    """

    # turbine general
    turbine_class: int = create_field(int, "unitless", "input")
    rated_power_kw: int = create_field(int, "kW", "input")

    # blades
    num_blades: int = create_field(int, "unitless", "input", default=3)
    blade_has_carbon: bool = create_field(bool, "unitless", "input")
    blade_mass_coeff: float = create_field(float, "unitless", "input")
    blade_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    blade_mass: float = create_field(float, "kg", "both")
    blade_cost: float = create_field(float, "USD", "both")

    # hub
    hub_mass_coeff: float = create_field(float, "unitless", "input")
    hub_mass_intercept: float = create_field(float, "unitless", "input")
    hub_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    hub_mass: float = create_field(float, "kg", "both")
    hub_cost: float = create_field(float, "USD", "both")

    # rotor
    rotor_diameter: float = create_field(float, "m", "input")
    efficiency_max: float = create_field(float, "unitless", "input")
    max_tip_speed: float = create_field(float, "m/s", "input")
    rated_rpm: float = create_field(float, "rpm", "both")
    rotor_torque: float = create_field(float, "MN*m", "both")

    # pitch system
    pitch_bearing_mass_coeff: float = create_field(float, "unitless", "input")
    pitch_bearing_mass_intercept: float = create_field(float, "kg", "input")
    bearing_housing_fraction: float = create_field(float, "unitless", "input")
    mass_sys_offset: float = create_field(float, "kg", "input")
    pitch_system_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    pitch_system_mass: float = create_field(float, "kg", "both")
    pitch_system_cost: float = create_field(float, "USD", "both")

    # spinner (nose cone)
    spinner_mass_coeff: float = create_field(float, "unitless", "input")
    spinner_mass_intercept: float = create_field(float, "kg", "input")
    spinner_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    spinner_mass: float = create_field(float, "kg", "both")
    spinner_cost: float = create_field(float, "USD", "both")

    # low speed shaft
    lss_mass_coeff: float = create_field(float, "unitless", "input")
    lss_mass_intercept: float = create_field(float, "kg", "input")
    lss_mass_exp: float = create_field(float, "unitless", "input")
    lss_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    low_speed_shaft_mass: float = create_field(float, "kg", "both")
    low_speed_shaft_cost: float = create_field(float, "USD", "both")

    # main bearing
    num_bearings: int = create_field(int, "unitless", "input")
    bearing_mass_coeff: float = create_field(float, "unitless", "input")
    bearing_mass_exp: float = create_field(float, "units", "input")
    bearing_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    bearing_mass: float = create_field(float, "kg", "both")
    bearing_cost: float = create_field(float, "USD", "both")

    # gearbox
    gearbox_torque_density: float = create_field(float, "N*m/kg", "input")
    gearbox_torque_cost: float = create_field(float, "USD/kN/m", "input")
    gearbox_mass: float = create_field(float, "kg", "both")
    gearbox_cost: float = create_field(float, "USD", "both")

    # brakes
    brake_mass_coeff: float = create_field(float, "unitless", "input")
    brake_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    brake_mass: float = create_field(float, "kg", "both")
    brake_cost: float = create_field(float, "USD", "both")

    # high speed shaft
    hss_mass_coeff: float = create_field(float, "unitless", "input")
    hss_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    high_speed_shaft_mass: float = create_field(float, "kg", "both")
    high_speed_shaft_cost: float = create_field(float, "USD", "both")

    # generator
    generator_mass_coeff: float = create_field(float, "kg/kW", "input")
    generator_mass_intercept: float = create_field(float, "kg", "input")
    generator_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    generator_mass: float = create_field(float, "kg", "both")
    generator_cost: float = create_field(float, "USD", "both")

    # bedplate
    bedplate_mass_exp: float = create_field(float, "unitless", "input")
    bedplate_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    bedplate_mass: float = create_field(float, "kg", "both")
    bedplate_cost: float = create_field(float, "USD", "both")

    # yaw system
    yaw_system_non_bearing_mass_coeff: float = create_field(float, "unitless", "input")
    yaw_system_mass_coeff: float = create_field(float, "unitless", "input")
    yaw_system_mass_exp: float = create_field(float, "unitless", "input")
    yaw_system_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    yaw_system_mass: float = create_field(float, "kg", "both")
    yaw_system_cost: float = create_field(float, "USD", "both")

    # high speed shaft
    hvac_mass_coeff: float = create_field(float, "unitless", "input")
    hvac_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    hydraulic_cooling_mass: float = create_field(float, "kg", "both")
    hydraulic_cooling_cost: float = create_field(float, "USD", "both")

    # nacelle cover
    nacelle_cover_mass_coeff: float = create_field(float, "kg/kW", "input")
    nacelle_cover_mass_intercept: float = create_field(float, "kg", "input")
    nacelle_cover_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    nacelle_cover_mass: float = create_field(float, "kg", "both")
    nacelle_cover_cost: float = create_field(float, "USD", "both")

    # platform mainframe
    has_crane: bool = create_field(bool, "unitless", "input")
    crane_mass: float = create_field(float, "kg", "both")
    crane_cost: float = create_field(float, "USD", "both")
    platform_mainframe_mass_coeff: float = create_field(float, "unitless", "input")
    platform_mainframe_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    platform_mainframe_mass: float = create_field(float, "kg", "both")
    platform_mainframe_cost: float = create_field(float, "USD", "both")

    # transformer
    transformer_mass_coeff: float = create_field(float, "kg/kW", "input")
    transformer_mass_intercept: float = create_field(float, "kg", "input")
    transformer_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    transformer_mass: float = create_field(float, "kg", "both")
    transformer_cost: float = create_field(float, "USD", "both")

    # tower
    tower_mass_coeff: float = create_field(float, "unitless", "input")
    tower_length: float = create_field(float, "m", "input")
    tower_mass_exp: float = create_field(float, "unitless", "input")
    tower_mass_cost_coeff: float = create_field(float, "USD/kg", "input")
    tower_mass: float = create_field(float, "kg", "both")
    tower_cost: float = create_field(float, "USD", "both")

    # totals
    nacelle_mass: float = create_field(float, "kg", "both")
    nacelle_cost: float = create_field(float, "USD", "both")
    hub_system_mass: float = create_field(float, "kg", "both")
    hub_system_cost: float = create_field(float, "USD", "both")
    rotor_mass: float = create_field(float, "kg", "both")
    rotor_cost: float = create_field(float, "USD", "both")
    turbine_mass: float = create_field(float, "kg", "both")
    turbine_cost: float = create_field(float, "USD", "output")
    turbine_cost_kw: float = create_field(float, "USD/kW", "output")

    # NOTE: temporary while prototyping
    power_converter_cost: float = field(default=1000.0)
    turbine_production_cost: float = field(default=1000.0)
    tower_flange_material_cost: float = field(default=1000.0)
    tower_flange_production_cost: float = field(default=1000.0)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Creates a new instance from a dictionary with simplified and intuitive error messages
        for extraneous and missing attributes.

        Args:
            data (dict): The data dictionary to be mapped.

        Returns:-
            cls: An instance of :py:class:`CSMBase` or one of its subclasses.
        """
        inputs = set(data)
        attributes = {el.name for el in cls.__attrs_attrs__ if el.init}
        required = {
            el.name
            for el in cls.__attrs_attrs__
            if el.init and el.default is None and el.metadata["io"] == "input"
        }

        extra = inputs.difference(attributes)
        if len(extra):
            msg = (
                f"The initialization for {cls.__name__} was given extraneous "
                f"inputs: {', '.join(extra)}"
            )
            raise AttributeError(msg)

        missing = required.difference(inputs)
        if missing:
            msg = (
                f"The class definition for {cls.__name__} is missing the following inputs: "
                f"{missing}"
            )
            raise AttributeError(msg)
        return cls(**data)

    def _has_values(self, *args) -> Generator[bool]:
        """Checks if the user provided values for a given :py:attr:`arg` (True), or if they are
        model defaults (False).

        Yields:
            Generator[bool]: Booleans indicating valid values have been implemented or provided
                by the user (True) or if the base class defaults are present (False).
        """
        for arg in args:
            default = getattr(fields(CSMBase), arg).default
            value = getattr(self, arg)
            yield value != default or default is not None

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
        if next(self._has_values("blade_mass")):
            return

        parameters = ("rotor_diameter", "turbine_class", "blade_has_carbon", "blade_mass_coeff")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("blade_cost")):
            return

        parameters = ("blade_mass", "blade_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
            blade_mass (float): Blade mass (:math:`kg`). See :py:method:`calculate_blade_mass`
                for details.
            hub_mass_intercept (bool): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("hub_mass")):
            return

        parameters = ("blade_mass", "hub_mass_coeff", "hub_mass_intercept")
        self._validate_inputs(parameters=parameters)

        self.hub_mass = self.hub_mass_coeff * self.blade_mass + self.hub_mass_intercept

    def calculate_hub_cost(self):
        """Calculates and sets :py:attr:`hub_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`hub_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`hub_mass` (:math:`kg`).

        Args:
            hub_mass_cost_coeff (float): Hub cost per kilogram (USD/kg).
            hub_mass (float): Hub mass (kg). See :py:method:`calculate_hub_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("hub_cost")):
            return

        parameters = ("hub_mass", "hub_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
            blade_mass (float): Blade mass (:math:`kg`). See :py:method:`calculate_blade_mass`
                for details.
            pitch_bearing_mass_intercept (float): :math:`b1` in the pitch bearing mass equation.
            bearing_housing_fraction (float): Mass of the housing for the bearing as a fraction of
                the bearing mass. :math:`h` in the pitch system mass equation.
            mass_sys_offset (float): :math:`b2` in the pitch system mass equation.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("pitch_system_mass")):
            return

        parameters = (
            "num_blades",
            "pitch_bearing_mass_coeff",
            "blade_mass",
            "pitch_bearing_mass_intercept",
            "bearing_housing_fraction",
            "mass_sys_offset",
        )
        self._validate_inputs(parameters=parameters)

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
                :py:method:`calculate_pitch_system_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("pitch_system_cost")):
            return

        parameters = ("pitch_system_mass", "pitch_system_mass_cost_coeff")
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
        if next(self._has_values("spinner_mass")):
            return

        parameters = ("spinner_mass_coeff", "rotor_diameter", "spinner_mass_intercept")
        self._validate_inputs(parameters=parameters)

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
            spinner_mass (float): Spinner mass (kg). See :py:method:`calculate_spinner_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("spinner_cost")):
            return

        parameters = ("spinner_mass", "spinner_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
            blade_mass (float): Blade mass (:math:`kg`). See :py:method:`calculate_blade_mass`
                for details.
            lss_mass_coeff (float): :math:`k` in the low speed shaft mass equation.
            lss_mass_exp (float): :math:`b1` in the low speed shaft mass equation.
            lss_mass_intercept (float): :math:`b2` in the low speed shaft mass equation.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("low_speed_shaft_mass")):
            return

        parameters = (
            "rated_power_kw",
            "blade_mass",
            "lss_mass_coeff",
            "lss_mass_exp",
            "lss_mass_intercept",
        )
        self._validate_inputs(parameters=parameters)

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
                :py:method:`calculate_low_speed_shaft_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("low_speed_shaft_cost")):
            return

        parameters = ("low_speed_shaft_mass", "lss_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("bearing_mass")):
            return

        parameters = ("bearing_mass_coeff", "rotor_diameter", "bearing_mass_exp")
        self._validate_inputs(parameters=parameters)

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
            bearing_mass (float): Main bearing mass (kg). See :py:method:`calculate_bearing_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("bearing_cost")):
            return

        parameters = ("bearing_mass", "bearing_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
        if all(self._has_values("rated_rpm", "rotor_torque")):
            return

        parameters = ("rotor_diameter", "rated_power_kw", "efficiency_max", "max_tip_speed")
        self._validate_inputs(parameters=parameters)

        rated_hub_power = self.rated_power_kw / self.efficiency_max
        rotor_speed = self.max_tip_speed / (0.5 * self.rotor_diameter)
        self.rated_rpm = rotor_speed / (2.0 * math.pi) * 60.0
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
        if next(self._has_values("gearbox_mass")):
            return

        parameters = ("rotor_torque", "gearbox_torque_density")
        self._validate_inputs(parameters=parameters)

        self.gearbox_mass = self.rotor_torque * 1e3 / self.gearbox_torque_density

    def calculate_gearbox_cost(self):
        """Calculates and sets :py:attr:`gearbox_cost` if it was not provided by the user.

        .. math:: k * m_{gearbox} * {gearbox_torque_cost} / 1000

        where:

        - :math:`k =` :py:attr:`gearbox_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`gearbox_mass` (:math:`kg`).

        Args:
            gearbox_mass (float): Main bearing mass (kg). See :py:method:`calculate_gearbox_mass`
                for more details.
            gearbox_torque_density (float): :math:`k` in the mass equation above (:math:`N*m/kg`).
            gearbox_torque_cost (float): Gearbox cost per :math:`N*m` (:math:`USD/kN/m`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("gearbox_cost")):
            return

        parameters = ("gearbox_mass", "gearbox_torque_density", "gearbox_torque_cost")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("brake_mass")):
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
            brake_mass (float): Brake mass (kg). See :py:method:`calculate_brake_mass`
                for more details.
            brake_mass_cost_coeff (float): Brake cost, per kilogram of mass, :math:`k` in the
                equation above (:math:`USD/kg`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("brake_cost")):
            return

        parameters = ("brake_mass", "brake_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("high_speed_shaft_mass")):
            return

        parameters = ("rated_power_kw", "hss_mass_coeff")
        self._validate_inputs(parameters=parameters)

        self.high_speed_shaft_mass = self.hss_mass_coeff * self.rated_power_kw

    def calculate_high_speed_shaft_cost(self):
        """Calculates and sets :py:attr:`high_speed_shaft_cost` if it was not provided by the user.

        .. math:: k * m_{high_speed_shaft}

        where:

        - :math:`k =` :py:attr:`hss_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`high_speed_shaft_mass` (:math:`kg`).

        Args:
            high_speed_shaft_mass (float): High speed shaft mass (kg). See
                :py:method:`calculate_high_speed_shaft_mass` for more details.
            hss_mass_cost_coeff (float): High speed shaft cost, per kilogram of mass, :math:`k` in
                the equation above (:math:`USD/kg`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("high_speed_shaft_cost")):
            return

        parameters = ("high_speed_shaft_mass", "hss_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("generator_mass")):
            return

        parameters = ("rated_power_kw", "generator_mass_coeff", "generator_mass_intercept")
        self._validate_inputs(parameters=parameters)

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
            generator_mass (float): generator mass (kg). See :py:method:`calculate_generator_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("generator_cost")):
            return

        parameters = ("generator_mass", "generator_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("bedplate_mass")):
            return

        parameters = ("rotor_diameter", "bedplate_mass_exp")
        self._validate_inputs(parameters=parameters)

        self.bedplate_mass = self.rotor_diameter**self.bedplate_mass_exp

    def calculate_bedplate_cost(self):
        """Calculates and sets :py:attr:`bedplate_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`bedplate_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`bedplate_mass` (:math:`kg`).

        Args:
            bedplate_mass_cost_coeff (float): bedplate cost per kilogram (USD/kg).
            bedplate_mass (float): bedplate mass (kg). See :py:method:`calculate_bedplate_mass`
                for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("bedplate_cost")):
            return

        parameters = ("bedplate_mass", "bedplate_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("yaw_system_mass")):
            return

        parameters = (
            "rotor_diameter",
            "yaw_system_non_bearing_mass_coeff",
            "yaw_system_mass_coeff",
            "yaw_system_mass_exp",
        )
        self._validate_inputs(parameters=parameters)

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
                See :py:method:`calculate_yaw_system_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("yaw_system_cost")):
            return

        parameters = ("yaw_system_mass", "yaw_system_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("hydraulic_cooling_mass")):
            return

        parameters = ("rated_power_kw", "hvac_mass_coeff")
        self._validate_inputs(parameters=parameters)

        self.hydraulic_cooling_mass = self.hvac_mass_coeff * self.rated_power_kw

    def calculate_hydraulic_cooling_cost(self):
        """Calculates and sets :py:attr:`hydraulic_cooling_cost` if it was not provided by the user.

        .. math:: k * m_{hydraulic_cooling}

        where:

        - :math:`k =` :py:attr:`hvac_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`hydraulic_cooling_mass` (:math:`kg`).

        Args:
            hydraulic_cooling_mass (float): Hydraulic cooling mass (kg). See
                :py:method:`calculate_hydraulic_cooling_mass` for more details.
            hvac_mass_cost_coeff (float): Hydraulic cooling cost, per kilogram of mass, :math:`k` in
                the equation above (:math:`USD/kg`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("hydraulic_cooling_cost")):
            return

        parameters = ("hydraulic_cooling_mass", "hvac_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("nacelle_cover_mass")):
            return

        parameters = ("rated_power_kw", "nacelle_cover_mass_coeff", "nacelle_cover_mass_intercept")
        self._validate_inputs(parameters=parameters)

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
                :py:method:`calculate_nacelle_cover_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("nacelle_cover_cost")):
            return

        parameters = ("nacelle_cover_mass", "nacelle_cover_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

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
                :py:method:`calculate_bedplate_mass` for details.
            crane_mass (bool): Mass of onboard crane, if :py:attr:`has_crane`, :math:`b` in the
                mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("platform_mainframe_mass")):
            return

        parameters = ("bedplate_mass", "platform_mainframe_mass_coeff", "has_crane", "crane_mass")
        self._validate_inputs(parameters=parameters)

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
                See :py:method:`calculate_platform_mainframe_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("platform_mainframe_cost")):
            return

        parameters = (
            "platform_mainframe_mass",
            "platform_mainframe_mass_cost_coeff",
            "has_crane",
            "crane_mass",
            "crane_cost",
        )
        self._validate_inputs(parameters=parameters)

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
        if next(self._has_values("transformer_mass")):
            return

        parameters = ("rated_power_kw", "transformer_mass_coeff", "transformer_mass_intercept")
        self._validate_inputs(parameters=parameters)

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
            transformer_mass_cost_coeff (float): Transformer cover cost per kilogram (USD/kg).
            transformer_mass (float): Transformer cover mass (kg). See
                :py:method:`calculate_transformer_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("transformer_cost")):
            return

        parameters = ("transformer_mass", "transformer_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

        self.transformer_cost = self.transformer_mass_cost_coeff * self.transformer_mass

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
        if next(self._has_values("tower_mass")):
            return

        parameters = ("tower_length", "tower_mass_coeff", "tower_mass_exp")
        self._validate_inputs(parameters=parameters)

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
                :py:method:`calculate_tower_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("tower_cost")):
            return

        parameters = ("tower_mass", "tower_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

        self.tower_cost = self.tower_mass_cost_coeff * self.tower_mass

    def calculate_nacelle_mass(self):
        """Calculates and sets :py:attr:`nacelle_mass` (:math:`kg`) if it was not provided by the
        user.

        Sum of all above-tower components, excluding the blades (:py:method:`calculate_rotor_mass`)
        and hub (:py:method:`calculate_hub_system_mass`):

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

        Args:
            low_speed_shaft_mass (float): See :py:method:`calculate_low_speed_shaft_mass` for more
                details.
            num_bearings (float): Number of main bearings (:py:attr:`num_bearings`).
            bearing_mass (float): See :py:method:`calculate_bearing_mass` for more details.
            gearbox_mass (float): See :py:method:`calculate_gearbox_mass` for more details.
            brake_mass (float): See :py:method:`calculate_brake_mass` for more details.
            high_speed_shaft_mass (float): See :py:method:`calculate_high_speed_shaft_mass` for
                more details.
            generator_mass (float): See :py:method:`calculate_generator_mass` for more details.
            bedplate_mass (float): See :py:method:`calculate_bedplate_mass` for more details.
            yaw_system_mass (float): See :py:method:`calculate_yaw_system_mass` for more details.
            hydraulic_cooling_mass (float): See :py:method:`calculate_hydraulic_cooling_mass` for
                more details.
            nacelle_cover_mass (float): See :py:method:`calculate_nacelle_cover_mass` for more
                details.
            platform_mainframe_mass (float): See :py:method:`calculate_platform_mainframe_mass` for
                more details.
            transformer_mass (float): See :py:method:`calculate_transformer_mass` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("nacelle_mass")):
            return

        parameters = (
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
        )
        self._validate_inputs(parameters=parameters)

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
            )
        )

    def calculate_nacelle_cost(self):
        """Calculates and sets :py:attr:`nacelle_cost`  (USD) if it was not provided by the user.

        Sum of all above-tower components, excluding the blades (:py:method:`calculate_rotor_cost`)
        and hub (:py:method:`calculate_hub_system_cost`):

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

        Args:
            low_speed_shaft_cost (float): See :py:method:`calculate_low_speed_shaft_cost` for more
                details.
            num_bearings (float): Number of main bearings (:py:attr:`num_bearings`).
            bearing_cost (float): See :py:method:`calculate_bearing_cost` for more details.
            gearbox_cost (float): See :py:method:`calculate_gearbox_cost` for more details.
            brake_cost (float): See :py:method:`calculate_brake_cost` for more details.
            high_speed_shaft_cost (float): See :py:method:`calculate_high_speed_shaft_cost` for
                more details.
            generator_cost (float): See :py:method:`calculate_generator_cost` for more details.
            bedplate_cost (float): See :py:method:`calculate_bedplate_cost` for more details.
            yaw_system_cost (float): See :py:method:`calculate_yaw_system_cost` for more details.
            hydraulic_cooling_cost (float): See :py:method:`calculate_hydraulic_cooling_cost` for
                more details.
            nacelle_cover_cost (float): See :py:method:`calculate_nacelle_cover_cost` for more
                details.
            platform_mainframe_cost (float): See :py:method:`calculate_platform_mainframe_cost` for
                more details.
            transformer_cost (float): See :py:method:`calculate_transformer_cost` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("nacelle_cost")):
            return

        parameters = (
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
        )
        self._validate_inputs(parameters=parameters)

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
            hub_mass (float): See :py:method:`calculate_hub_mass` for more details.
            pitch_system_mass (float): See :py:method:`calculate_pitch_system_mass` for more
                details.
            spinner_mass (float): See :py:method:`calculate_spinner_mass` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("hub_system_mass")):
            return

        parameters = (
            "hub_mass",
            "pitch_system_mass",
            "spinner_mass",
        )
        self._validate_inputs(parameters=parameters)

        self.hub_system_mass = sum((self.hub_mass, self.pitch_system_mass, self.spinner_mass))

    def calculate_hub_system_cost(self):
        """Calculates and sets :py:attr:`hub_system_cost`  (USD) if it was not provided by the user.

        Sum of the following components:

        - :py:attr:`hub_cost`
        - :py:attr:`pitch_system_cost`
        - :py:attr:`spinner_cost`

        Args:
            hub_cost (float): See :py:method:`calculate_hub_cost` for more details.
            pitch_system_cost (float): See :py:method:`calculate_pitch_system_cost` for more
                details.
            spinner_cost (float): See :py:method:`calculate_spinner_cost` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("hub_system_cost")):
            return

        parameters = (
            "hub_cost",
            "pitch_system_cost",
            "spinner_cost",
        )
        self._validate_inputs(parameters=parameters)

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

        Sum of the blades and hub system (:py:method:`calculate_hub_system_mass`):

        Args:
            num_blades (float): Number of turbine blades (:py:attr:`num_blades`).
            blade_mass (float): See :py:method:`calculate_blade_mass` for more details.
            hub_system_mass (float): See :py:method:`calculate_hub_system_mass` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("rotor_mass")):
            return

        parameters = ("num_blades", "blade_mass", "hub_system_mass")
        self._validate_inputs(parameters=parameters)

        self.rotor_mass = self.num_blades * self.blade_mass + self.hub_system_mass

    def calculate_rotor_cost(self):
        """Calculates and sets :py:attr:`rotor_cost` (:math:`kg`) if it was not provided by the
        user.

        Sum of the blades and hub system (:py:method:`calculate_hub_system_cost`):

        Args:
            num_blades (float): Number of turbine blades (:py:attr:`num_blades`).
            blade_cost (float): See :py:method:`calculate_blade_cost` for more details.
            hub_system_cost (float): See :py:method:`calculate_hub_system_cost` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("rotor_cost")):
            return

        parameters = ("num_blades", "blade_cost", "hub_system_cost")
        self._validate_inputs(parameters=parameters)

        self.rotor_cost = self.num_blades * self.blade_cost + self.hub_system_cost

    def calculate_turbine_mass(self):
        """Calculates and sets :py:attr:`turbine_mass` (:math:`kg`) if it was not provided by the
        user.

        Sum of the :py:attr:`rotor_mass` (:py:attr:`calculate_rotor_mass`),
        :py:attr:`hub_system_mass` (:py:attr:`calculate_hub_system_mass`),
        :py:attr:`nacelle_mass` (:py:attr:`calculate_nacelle_mass`), and
        :py:attr:`tower_mass` (:py:attr:`calculate_tower_mass`)

        Args:
            nacelle_mass (float): See :py:method:`calculate_nacelle_mass` for more details.
            hub_system_mass (float): See :py:method:`calculate_hub_system_mass` for more details.
            rotor_mass (float): See :py:method:`calculate_rotor_mass` for more details.
            tower_mass (float): See :py:method:`calculate_tower_mass` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("turbine_mass")):
            return

        parameters = (
            "nacelle_mass",
            "rotor_mass",
            "tower_mass",
        )
        self._validate_inputs(parameters=parameters)

        self.turbine_mass = self.nacelle_mass + self.rotor_mass + self.tower_mass

    def calculate_turbine_cost(self):
        """Calculates and sets :py:attr:`turbine_cost` (:math:`kg`) if it was not provided by the
        user.

        Sum of the :py:attr:`rotor_cost` (:py:attr:`calculate_rotor_cost`),
        :py:attr:`hub_system_cost` (:py:attr:`calculate_hub_system_cost`),
        :py:attr:`nacelle_cost` (:py:attr:`calculate_nacelle_cost`), and
        :py:attr:`tower_cost` (:py:attr:`calculate_tower_cost`)

        Args:
            nacelle_cost (float): See :py:method:`calculate_nacelle_cost` for more details.
            hub_system_cost (float): See :py:method:`calculate_hub_system_cost` for more details.
            rotor_cost (float): See :py:method:`calculate_rotor_cost` for more details.
            tower_cost (float): See :py:method:`calculate_tower_cost` for more details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("turbine_cost")):
            return

        parameters = (
            "nacelle_cost",
            "rotor_cost",
            "tower_cost",
        )
        self._validate_inputs(parameters=parameters)

        self.turbine_cost = self.nacelle_cost + self.rotor_cost + self.tower_cost
        self.turbine_cost_kw = self.turbine_cost / self.rated_power_kw

    def run(self):
        """Run the mass and cost calculations."""
        # self.calculate_rotor_torque()
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
        self.calculate_tower_mass()
        self.calculate_nacelle_mass()
        self.calculate_hub_system_mass()
        self.calculate_rotor_mass()
        self.calculate_turbine_mass()

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
        self.calculate_tower_cost()
        self.calculate_nacelle_cost()
        self.calculate_hub_system_cost()
        self.calculate_rotor_cost()
        self.calculate_turbine_cost()

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
            # "rotor_torque": self.rotor_torque,
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
            "tower_cost": self.tower_cost,
            "nacelle_cost": self.nacelle_cost,
            "hub_system_cost": self.hub_system_cost,
            "rotor_cost": self.rotor_cost,
            "turbine_cost": self.turbine_cost,
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
          - Blades: model-calculated :py:attr:`blade_cost`. See :py:method:`calculate_blade_cost`
            for complete details.
          - Rotor Hub: model-calculated :py:attr:`hub_cost`. See :py:method:`calculate_hub_cost`
            for complete details.
          - Nacelle: model-calculated :py:attr:`nacelle_cost`.
            See :py:method:`calculate_nacelle_cost for complete details.
          - Power Converter: model-calculated :py:attr:`power_converter_cost`. See
            :py:method:`calculate_power_converter_cost` for complete details.
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
            "power_converter": self.power_converter_cost,
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
        with :py:method:`irs_mpc_breakdown`.

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
                of :py:method:`irs_mpc_breakdown`.
            return_table (bool, optional): If True, return the DataFrame from
                :py:method:`irs_mpc_breakdown` with the additional column ``Domestic`` that shows
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
