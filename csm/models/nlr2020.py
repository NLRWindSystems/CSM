"""Experimental generic new model generation and 2015 replication."""

import numpy as np
from attrs import define, fields

from csm.models.utils import create_field
from csm.models.base_model import CSMBase


base = fields(CSMBase)


ALL_RESULT_NAMES = (
    "blade_mass",
    "blade_cost",
    "hub_mass",
    "hub_cost",
    "pitch_system_mass",
    "pitch_system_cost",
    "spinner_mass",
    "spinner_cost",
    "low_speed_shaft_mass",
    "low_speed_shaft_cost",
    "bearing_mass",
    "bearing_cost",
    "rated_rpm",
    "rotor_torque",
    "gearbox_mass",
    "gearbox_cost",
    "brake_mass",
    "brake_cost",
    "generator_mass",
    "generator_cost",
    "bedplate_mass",
    "bedplate_cost",
    "yaw_system_mass",
    "yaw_system_cost",
    "hydraulic_cooling_mass",
    "hydraulic_cooling_cost",
    "nacelle_cover_mass",
    "nacelle_cover_cost",
    "platform_mainframe_mass",
    "platform_mainframe_cost",
    "crane_mass",
    "crane_cost",
    "transformer_mass",
    "transformer_cost",
    "converter_mass",
    "converter_cost",
    "controls_mass",
    "controls_cost",
    "electrical_connection_mass",
    "electrical_connection_cost",
    "tower_mass",
    "tower_cost",
    "nacelle_mass",
    "nacelle_cost",
    "hub_system_mass",
    "hub_system_cost",
    "rotor_mass",
    "rotor_cost",
    "turbine_mass",
    "turbine_cost",
    "turbine_cost_kw",
    "transport_cost",
)

MASS_RESULT_NAMES = (
    "blade_mass",
    "hub_mass",
    "pitch_system_mass",
    "spinner_mass",
    "low_speed_shaft_mass",
    "bearing_mass",
    "gearbox_mass",
    "brake_mass",
    "generator_mass",
    "bedplate_mass",
    "yaw_system_mass",
    "hydraulic_cooling_mass",
    "nacelle_cover_mass",
    "platform_mainframe_mass",
    "crane_mass",
    "transformer_mass",
    "converter_mass",
    "controls_mass",
    "electrical_connection_mass",
    "tower_mass",
    "nacelle_mass",
    "hub_system_mass",
    "rotor_mass",
    "turbine_mass",
)

COST_RESULT_NAMES = (
    "blade_cost",
    "hub_cost",
    "pitch_system_cost",
    "spinner_cost",
    "low_speed_shaft_cost",
    "bearing_cost",
    "gearbox_cost",
    "brake_cost",
    "generator_cost",
    "bedplate_cost",
    "yaw_system_cost",
    "hydraulic_cooling_cost",
    "nacelle_cover_cost",
    "platform_mainframe_cost",
    "crane_cost",
    "transformer_cost",
    "converter_cost",
    "controls_cost",
    "electrical_connection_cost",
    "tower_cost",
    "nacelle_cost",
    "hub_system_cost",
    "rotor_cost",
    "turbine_cost",
    "turbine_cost_kw",
    "transport_cost",
)


@define
class Land2020NLR(CSMBase):
    r"""NLR 2020 empirically-based model based on updated data and feedback since the
    original and 2015 models.

    Unused parameters from the base model:

    - :py:attr:`turbine_class`
    - :py:attr:`blade_has_carbon`
    - :py:attr:`bearing_housing_fraction`
    - :py:attr:`pitch_bearing_mass_coeff`
    - :py:attr:`pitch_bearing_mass_intercept`
    - :py:attr:`lss_mass_exp`
    - :py:attr:`lss_mass_coeff`
    - :py:attr:`gearbox_torque_cost`
    - :py:attr:`hss_mass_coeff`
    - :py:attr:`hss_mass_cost_coeff`
    - :py:attr:`high_speed_shaft_mass`
    - :py:attr:`high_speed_shaft_cost`
    - :py:attr:`bedplate_mass_exp`
    - :py:attr:`hvac_mass_coeff`
    - :py:attr:`tower_mass_exp`

    Not updated from the 2015 model:

    - :py:attr:`pitch_system_mass_cost_coeff`

    Updated scaling relationships:

    - :py:attr:`blade_mass`
    - :py:attr:`pitch_system_mass`
    - :py:attr:`low_speed_shaft_mass`
    - :py:attr:`gearbox_mass`
    - :py:attr:`gearbox_cost`
    - :py:attr:`bedplate_mass`
    - :py:attr:`hydraulic_cooling_mass`
    - :py:attr:`platform_mainframe_mass`
    - :py:attr:`platform_mainframe_cost`
    - :py:attr:`crane_mass`
    - :py:attr:`crane_cost`
    - :py:attr:`tower_mass`
    - :py:attr:`transport_cost`
    - :py:attr:`nacelle_mass`
    - :py:attr:`nacelle_cost`


    Args:
        num_blades (int): Number of turbine blades
        num_bearings (int): Number of main bearings.
        rated_power_kw (float): Turbine rated power (:math:`kW`).
        rotor_diameter (float): Diameter of the swept area of the turbine blades (:math:`m`).
        efficiency_max (float): Maximum possible drivetrain efficiency.
        has_crane (bool): In the 2020 model, a crane is assumed to exist. Defaults to True.
        max_tip_speed (float): Maximum allowable blade tip speed (:math:`m/s`).
        tower_length (float): For onshore turbines, this is the hub height (total length above
            ground). For offshore turbines, this is length from transition piece to hub height
            (:math:`m`).

    Parameters:
        blade_mass_coeff (float): :math:`k` in the blade mass equation from
            :py:meth:`calculate_blade_mass`. Defaults to 9.2157.
        blade_mass_exp (float):  :math:`b` in the blade mass equation from
            :py:meth:`calculate_blade_mass`. Defaults to 1.7679.
        blade_mass_cost_coeff (float): Defaults to 15.9432.
        blade_mass (float): Single lade mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_blade_mass`.
        blade_cost (float): Single blade cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_blade_cost`.
        hub_mass_coeff (float): Defaults to 3.5793.
        hub_mass_intercept (float): Defaults to -25451.58.
        hub_mass_cost_coeff (float): Defaults to 4.2588.
        hub_mass (float): Hub mass (:math:`kg`). See :py:meth:`calculate_hub_mass`
            for more details.
        pitch_system_mass (float): Pitch system mass (:math:`kg`). See
            :py:meth:`calculate_pitch_system_mass` for more details.
        pitch_system_cost (float): Pitch system cost (:math:`USD`). See
            :py:meth:`calculate_pitch_system_cost` for more details.
        spinner_mass_coeff (float): Defaults to 2.3255 :math:`kg/m`.
        spinner_mass_intercept (float): Defaults to 204.65 :math:`kg`.
        spinner_mass_cost_coeff (float): Defaults to 12.1212 :math:`USD/kg`.
        spinner_mass (float): Spinner mass (:math:`kg`). See :py:meth:`calculate_spinner_mass`
            for more details.
        spinner_cost (float): Spinner cost (:math:`USD`). See :py:meth:`calculate_spinner_cost`
            for more details.
        lss_mass_coeff1 (float): Defaults to 2.1906 :math:`kg/m^2`.
        lss_mass_coeff2 (float): Defaults to -311.15 :math:`kg/m`.
        lss_mass_intercept (float): Defaults to 13108.0 :math:`kg`.
        lss_mass_cost_coeff (float): Defaults to 12.9948 :math:`USD/kg`.
        low_speed_shaft_mass (float): Low speed shaft mass (:math:`kg`). See
            :py:meth:`calculate_low_speed_shaft_mass` for more details.
        low_speed_shaft_cost (float): Low speed shaft cost (:math:`USD`). See
            :py:meth:`calculate_low_speed_shaft_cost` for more details.
        bearing_mass_coeff (float): Defaults to 0.0001.
        bearing_mass_exp (float): Defaults to 3.5.
        bearing_mass_cost_coeff (float): Defaults to 4.914 :math:`USD/kg`.
        bearing_mass (float): Main bearing mass (:math:`kg`). See :py:meth:`calculate_bearing_mass`
            for more details.
        bearing_cost (float): Main bearing cost (:math:`USD`). See :py:meth:`calculate_bearing_cost`
            for more details.
        rated_rpm (float): Rated RPM of the turbine based on the :py:attr:`max_tip_speed`
            and :py:attr:`rotor_diameter`. See :py:meth:`calculate_rotor_torque` for more details.
        rotor_torque (float): Maximum torque produced under normal operations of the turbine
            (kNm). See :py:meth:`calculate_rotor_torque` for more details.
        gearbox_torque_density (float): In 2024, modern 5-7MW gearboxes are able to reach 200 Nm/kg.
        gearbox_torque_exp (float): Defaults to 0.6566.
        gearbox_torque_cost (float): Unused in 2020. Defaults to 0.
        gearbox_mass_cost_coeff (float): Defaults to 14.0868.
        gearbox_mass (float): Gearbox mass (:math:`kg`). See :py:meth:`calculate_gearbox_mass`
            for more details.
        gearbox_cost (float): Gearbox cost (:math:`USD`). See :py:meth:`calculate_gearbox_cost`
            for more details.
        brake_mass_cost_coeff (float): In 2020, updated to $3.6254 USD/kg. Regression based sizing
            derived by J.Keller under FOA 1981 support project.
        brake_mass (float): Brake mass (:math:`kg`). See :py:meth:`calculate_brake_mass` for more
            details.
        brake_cost (float): Brake cost (:math:`USD`). See :py:meth:`calculate_brake_cost` for more
            details.
        generator_mass_coeff (float): Defaults to 1754.
        generator_mass_intercept (float): Defaults to 3503.6.
        generator_mass_cost_coeff (float): Defaults to 13.5408 :math:`USD/kg`.
        generator_mass (float): Generator mass (:math:`kg`). See :py:meth:`calculate_generator_mass`
            for more details.
        generator_cost (float): Generator cost (:math:`USD`). See
            :py:meth:`calculate_generator_cost` for more details.
        bedplate_mass_exp (float): Unused in the 2020 model. Defaults to 0.
        bedplate_mass_coeff (float): Defaults to 737.88.
        bedplate_mass_intercept (float): Defaults to -68066.
        bedplate_mass_cost_coeff (float): Defaults to 3.1668 :math:`USD/kg`.
        bedplate_mass (float): Bedplate mass (:math:`kg`). See :py:meth:`calculate_bedplate_mass`
            for more details.
        bedplate_cost (float): Bedplate cost (:math:`USD`). See :py:meth:`calculate_bedplate_cost`
            for more details.
        yaw_system_non_bearing_mass_coeff (float): Defaults to 1.6.
        yaw_system_mass_coeff (float): Defaults to 0.0007.
        yaw_system_mass_exp (float): Defaults to 3.1571.
        yaw_system_mass_cost_coeff (float): Defaults to 9.0636 :math:`USD/kg`.
        yaw_system_mass (float): Yaw system mass (:math:`kg`). See
            :py:meth:`calculate_yaw_system_mass` for more details.
        yaw_system_cost (float): Yaw system cost (:math:`USD`). See
            :py:meth:`calculate_yaw_system_cost` for more details.
        hvac_mass_cost_coeff (float): Defaults to 135.408 :math:`USD/kg`.
        hydraulic_cooling_mass (float): Defaults to 221 :math:`kg`.
        hydraulic_cooling_cost (float): Hydraulic cooling cost (:math:`USD`). See
            :py:meth:`calculate_hydraulic_cooling_cost` for more details.
        nacelle_cover_mass_coeff (float): Defaults to 1281.7 :math:`kg/kW`.
        nacelle_cover_mass_intercept (float): Defaults to 428.19.
        nacelle_cover_mass_cost_coeff (float): Defaults to 6.2244 :math:`USD/kg`.
        nacelle_cover_mass (float): nacelle_cover mass (:math:`kg`). See
            :py:meth:`calculate_nacelle_cover_mass` for more details.
        nacelle_cover_cost (float): nacelle_cover mass (:math:`USD`). See
            :py:meth:`calculate_nacelle_cover_cost` for more details.
        platform_mainframe_mass_coeff (float): Defaults to 0.005.
        platform_mainframe_mass_cost_coeff (float): Defaults to 18.6732 :math:`USD/kg`.
        platform_mainframe_mass (float): Platform mainframe mass (:math:`kg`).
            See :py:meth:`calculate_platform_mainframe_mass` for more details.
        platform_mainframe_cost (float): Platform mainframe cost (:math:`USD`).
            See :py:meth:`calculate_platform_mainframe_cost` for more details.
        crane_mass_cost_coeff (float): Defaults to 4.368 :math:`USD/kg`.
        crane_mass (float): If not provided, defaults to :py:attr:`platform_mainframe_mass`.
        transformer_mass_coeff (float): Defaults to 1915 :math:`kg/kW`.
        transformer_mass_intercept (bool): Defaults to 1910.
        transformer_mass_cost_coeff (float): Defaults to 20.5296 :math:`USD/kg`.
        transformer_mass (float): Transformer cover mass (:math:`kg`). See
            :py:meth:`calculate_transformer_mass` for more details.
        transformer_cost (float): Transformer cover cost (:math:`USD`). See
            :py:meth:`calculate_transformer_cost` for more details.
        controls_cost_coeff (float): 23.0958 :math:`USD/kW`.
        controls_mass (float): Controls mass (:math:`kg`). Defaults to 0 :math:`kg`.
        controls_cost (float): Controls cost (:math:`USD`). See
            :py:meth:`calculate_controls_cost` for more details.
        electrical_connection_mass (float): Electrical connection mass (:math:`kg`). See
            :py:meth:`calculate_electrical_connection_mass` for more details.
        electrical_connection_cost (float): Electrical connection cost (:math:`USD`). See
            :py:meth:`calculate_electrical_connection_cost` for more details.
        converter_mass_cost_coeff (float): Power converter cost per kilogram (:math:`USD/kg`).
            Defaults to 18.8 :math:`USD/kg`.
        converter_mass (float): Power converter mass (:math:`kg`). See
            :py:meth:`calculate_converter_mass` for more details.
        converter_cost (float): Power converter cost (:math:`USD`). See
            :py:meth:`calculate_converter_cost` for more details.
        electrical_connection_cost_coeff (float): Defaults to 45.7002 :math:`USD/kW`.
        tower_mass_coeff (float): Defaults to 0.152 :math:`kg/m`.
        tower_mass_intercept (bool): Defaults to -14281.
        tower_mass_cost_coeff (float): Defaults to 3.1668 :math:`USD/kg`.
        tower_mass (float): Tower mass (:math:`kg`). See
            :py:meth:`calculate_tower_mass` for more details.
        tower_cost (float): Tower cost (:math:`USD`). See
            :py:meth:`calculate_tower_cost` for more details.
        tower_cost (float): Tower cost (:math:`USD`). See
            :py:meth:`calculate_tower_cost` for more details.
        transport_drivetrain_cost_coeff1
        transport_power_electronics_cost_coeff
        transport_drivetrain_cost_coeff2
        transport_blade_cost_coeff1
        transport_blade_cost_coeff2
        transport_blade_cost_coeff3
        transport_blade_cost_intercept
        transport_hub_cost_intercept
        transport_tower_cost_coeff
        tower_section_mass_max
        transport_misc_parts_cost_coeff
        blade_transport_cost (float): Total blade transportation cost (:math:`USD`). See
            :py:meth:`calculate_blade_transport_cost` for more details.
        hub_transport_cost (float): Total hub transportation cost (:math:`USD`). See
            :py:meth:`calculate_hub_transport_cost` for more details.
        power_electronics_transport_cost (float): Total power_electronics transportation cost
            (:math:`USD`). See :py:meth:`calculate_power_electronics_transport_cost` for more
            details.
        drivetrain_transport_cost (float): Total drivetrain transportation cost (:math:`USD`). See
            :py:meth:`calculate_drivetrain_transport_cost` for more details.
        tower_transport_cost (float): Total tower transportation cost (:math:`USD`). See
            :py:meth:`calculate_tower_transport_cost` for more details.
        parts_transport_cost (float): Total transportation cost of miscellaneous parts
            (:math:`USD`). See :py:meth:`calculate_parts_transport_cost` for more details.
        transport_cost (float): Total transportation cost (:math:`USD`). See
            :py:meth:`calculate_transport_cost` for more details.
    """

    turbine_class = base.turbine_class.reuse(default=1)
    blade_mass_coeff = base.blade_mass_coeff.reuse(default=9.2157)
    blade_mass_exp = create_field(float, "unitless", "input", default=1.7679)
    blade_mass_cost_coeff = base.blade_mass_cost_coeff.reuse(default=15.9432)
    hub_mass_coeff = base.hub_mass_coeff.reuse(default=3.5793)
    hub_mass_intercept = base.hub_mass_intercept.reuse(default=-25451.58)
    hub_mass_cost_coeff = base.hub_mass_cost_coeff.reuse(default=4.2588)
    pitch_blade_mass_coeff = create_field(float, "unitless", "input", default=0.1295)
    pitch_system_mass_coeff = create_field(float, "unitless", "input", default=1.328)
    pitch_blade_mass_intercept = create_field(float, "unitless", "input", default=491.31)
    mass_sys_offset = base.mass_sys_offset.reuse(default=555.0)
    pitch_system_mass_cost_coeff = base.pitch_system_mass_cost_coeff.reuse(default=24.1332)
    spinner_mass_coeff = base.spinner_mass_coeff.reuse(default=2.3255)
    spinner_mass_intercept = base.spinner_mass_intercept.reuse(default=204.65)
    spinner_mass_cost_coeff = base.spinner_mass_cost_coeff.reuse(default=12.1212)
    lss_mass_coeff1 = create_field(float, units="unitless", io_type="input", default=2.1906)
    lss_mass_coeff2 = create_field(float, units="unitless", io_type="input", default=-311.15)
    lss_mass_intercept = base.lss_mass_intercept.reuse(default=13108.0)
    lss_mass_cost_coeff = base.lss_mass_cost_coeff.reuse(default=12.9948)
    bearing_mass_coeff = base.bearing_mass_coeff.reuse(default=0.0001)
    bearing_mass_exp = base.bearing_mass_exp.reuse(default=3.5)
    bearing_mass_cost_coeff = base.bearing_mass_cost_coeff.reuse(default=4.914)
    gearbox_torque_density = base.gearbox_torque_density.reuse(default=156.46)
    gearbox_torque_exp = create_field(float, "unitless", "input", default=0.6566)
    gearbox_mass_cost_coeff = create_field(float, "USD/kg", "input", default=14.0868)
    brake_mass_coeff = base.brake_mass_coeff.reuse(default=0.19851)
    brake_mass_intercept = create_field(float, units="unitless", io_type="input", default=1.893)
    brake_mass_cost_coeff = base.brake_mass_cost_coeff.reuse(default=7.4256)
    generator_mass_coeff = base.generator_mass_coeff.reuse(default=1.754)
    generator_mass_intercept = base.generator_mass_intercept.reuse(default=3503.6)
    generator_mass_cost_coeff = base.generator_mass_cost_coeff.reuse(default=13.5408)
    bedplate_mass_coeff = create_field(float, "unitless", "input", default=737.88)
    bedplate_mass_intercept = create_field(float, "unitless", "input", default=-68066)
    bedplate_mass_cost_coeff = base.bedplate_mass_cost_coeff.reuse(default=3.1668)
    yaw_system_non_bearing_mass_coeff = base.yaw_system_non_bearing_mass_coeff.reuse(default=1.6)
    yaw_system_mass_coeff = base.yaw_system_mass_coeff.reuse(default=0.0007)
    yaw_system_mass_exp = base.yaw_system_mass_exp.reuse(default=3.1571)
    yaw_system_mass_cost_coeff = base.yaw_system_mass_cost_coeff.reuse(default=9.0636)
    hvac_mass_cost_coeff = base.hvac_mass_cost_coeff.reuse(default=135.408)
    hydraulic_cooling_mass = base.hydraulic_cooling_mass.reuse(default=221)
    nacelle_cover_mass_coeff = base.nacelle_cover_mass_coeff.reuse(default=1.2817)
    nacelle_cover_mass_intercept = base.nacelle_cover_mass_intercept.reuse(default=428.19)
    nacelle_cover_mass_cost_coeff = base.nacelle_cover_mass_cost_coeff.reuse(default=6.2244)
    has_crane = base.has_crane.reuse(default=True)
    platform_mainframe_mass_coeff = base.platform_mainframe_mass_coeff.reuse(default=0.005)
    platform_mainframe_mass_cost_coeff = base.platform_mainframe_mass_cost_coeff.reuse(
        default=18.6732
    )
    crane_mass_cost_coeff = create_field(float, "USD/kg", "input", default=4.368)
    crane_mass = base.crane_mass.reuse(metadata={"io": "both"})
    transformer_mass_coeff = base.transformer_mass_coeff.reuse(default=1.915)
    transformer_mass_intercept = base.transformer_mass_intercept.reuse(default=1910.0)
    transformer_mass_cost_coeff = base.transformer_mass_cost_coeff.reuse(default=20.5296)
    converter_mass_cost_coeff = base.converter_mass_cost_coeff.reuse(default=18.8)
    controls_cost_coeff = base.controls_cost_coeff.reuse(default=23.0958)
    electrical_connection_cost_coeff = base.electrical_connection_cost_coeff.reuse(default=45.7002)
    tower_mass_coeff = base.tower_mass_coeff.reuse(default=0.152)
    tower_mass_intercept = create_field(float, "unitless", "input", default=-14281.0)
    tower_mass_cost_coeff = base.tower_mass_cost_coeff.reuse(default=3.1668)
    transport_drivetrain_cost_coeff1 = create_field(float, "USD", "input", default=9000)
    transport_power_electronics_cost_coeff = create_field(float, "USD", "input", default=9)
    transport_drivetrain_cost_coeff2 = create_field(float, "USD", "input", default=45000)
    transport_blade_cost_coeff1 = create_field(float, "USD", "input", default=0.543)
    transport_blade_cost_coeff2 = create_field(float, "USD", "input", default=-7.4903)
    transport_blade_cost_coeff3 = create_field(float, "USD", "input", default=-2847.5)
    transport_blade_cost_intercept = create_field(float, "USD", "input", default=103627)
    transport_hub_cost_intercept = create_field(float, "USD", "input", default=5000)
    transport_tower_cost_coeff = create_field(float, "USD", "input", default=34083)
    tower_section_mass_max = create_field(float, "USD", "input", default=80000)
    transport_misc_parts_cost_coeff = create_field(float, "USD", "input", default=0.025)

    # Unused attributes
    blade_has_carbon = base.blade_has_carbon.reuse(default=False)
    bearing_housing_fraction = base.bearing_housing_fraction.reuse(default=0)
    pitch_bearing_mass_coeff = base.pitch_bearing_mass_coeff.reuse(default=0)
    pitch_bearing_mass_intercept = base.pitch_bearing_mass_intercept.reuse(default=0)
    lss_mass_exp = base.lss_mass_exp.reuse(default=0)
    lss_mass_coeff = base.lss_mass_coeff.reuse(default=0)
    gearbox_torque_cost = base.gearbox_torque_cost.reuse(default=0)
    hss_mass_coeff = base.hss_mass_coeff.reuse(default=0)
    hss_mass_cost_coeff = base.hss_mass_cost_coeff.reuse(default=0)
    high_speed_shaft_mass = base.high_speed_shaft_mass.reuse(default=0)
    high_speed_shaft_cost = base.high_speed_shaft_cost.reuse(default=0)
    bedplate_mass_exp = base.bedplate_mass_exp.reuse(default=0)
    hvac_mass_coeff = base.hvac_mass_coeff.reuse(default=0)
    tower_mass_exp = base.tower_mass_exp.reuse(default=0)

    _all_result_names = base._all_result_names.reuse(default=ALL_RESULT_NAMES)
    _mass_result_name = base._mass_result_names.reuse(default=MASS_RESULT_NAMES)
    _cost_result_names = base._cost_result_names.reuse(default=COST_RESULT_NAMES)

    # TODO: transport cost tests
    # TODO: breakout transport cost methods to match updated base

    def __attrs_post_init__(self):
        """Updates the parameter mapping for new mass and cost relationships."""
        self.parameter_map["blade_mass"] = ("rotor_diameter", "blade_mass_coeff", "blade_mass_exp")
        self.parameter_map["pitch_system_mass"] = (
            "pitch_system_mass_coeff",
            "pitch_blade_mass_coeff",
            "num_blades",
            "blade_mass",
            "pitch_blade_mass_intercept",
            "mass_sys_offset",
        )
        self.parameter_map["low_speed_shaft_mass"] = (
            "rotor_diameter",
            "lss_mass_coeff1",
            "lss_mass_coeff2",
            "lss_mass_intercept",
        )
        self.parameter_map["gearbox_mass"] = (
            "rotor_torque",
            "gearbox_torque_density",
            "gearbox_torque_exp",
        )
        self.parameter_map["gearbox_cost"] = ("gearbox_mass", "gearbox_mass_cost_coeff")
        self.parameter_map["bedplate_mass"] = (
            "bedplate_mass_coeff",
            "rotor_diameter",
            "bedplate_mass_intercept",
        )
        self.parameter_map["hydraulic_cooling_mass"] = ("hydraulic_cooling_mass",)
        self.parameter_map["platform_mainframe_mass"] = (
            "bedplate_mass",
            "platform_mainframe_mass_coeff",
        )
        self.parameter_map["platform_mainframe_cost"] = (
            "platform_mainframe_mass",
            "platform_mainframe_mass_cost_coeff",
        )
        self.parameter_map["crane_mass"] = ("platform_mainframe_mass",)
        self.parameter_map["crane_cost"] = ("crane_mass_cost_coeff", "crane_mass")
        self.parameter_map["tower_mass"] = (
            "tower_mass_coeff",
            "tower_length",
            "rotor_diameter",
            "tower_mass_intercept",
        )
        self.parameter_map["transport_cost"] = (
            "transport_power_electronics_cost_coeff",
            "transport_drivetrain_cost_coeff1",
            "transport_drivetrain_cost_coeff2",
            "transport_blade_cost_coeff1",
            "transport_blade_cost_coeff2",
            "transport_blade_cost_coeff3",
            "transport_blade_cost_intercept",
            "transport_hub_cost_intercept",
            "transport_tower_cost_coeff",
            "tower_section_mass_max",
            "transport_misc_parts_cost_coeff",
        )
        # Removes unmodeled high speed shaft and adds crane
        self.parameter_map["nacelle_mass"] = (
            "low_speed_shaft_mass",
            "num_bearings",
            "bearing_mass",
            "gearbox_mass",
            "brake_mass",
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
            "crane_mass",
        )
        self.parameter_map["nacelle_cost"] = (
            "low_speed_shaft_cost",
            "num_bearings",
            "bearing_cost",
            "gearbox_cost",
            "brake_cost",
            "generator_cost",
            "bedplate_cost",
            "yaw_system_cost",
            "hydraulic_cooling_cost",
            "nacelle_cover_cost",
            "platform_mainframe_cost",
            "transformer_cost",
            "crane_cost",
        )
        super().__attrs_post_init__()

    def calculate_blade_mass(self):
        """Calculates and sets :py:attr:`blade_mass` if it was not provided by the user.

        .. math:: k * radius^b

        where:

        - :math:`k =` :py:attr:`blade_mass_coeff`
        - :math:`radius =` :py:attr:`rotor_diameter` / 2
        - :math:`b =` :py:attr:`blade_mass_exp`

        Args:
            blade_mass_coeff (float): :math:`k` in the mass equation above.
            rotor_diameter (float): Diameter of the swept area of the turbine blades.
            blade_mass_exp (float): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("blade_mass")
        if exists:
            return

        self.blade_mass = self.blade_mass_coeff * (self.rotor_diameter / 2) ** self.blade_mass_exp

    def calculate_pitch_system_mass(self):
        """Calculates and sets :py:attr:`pitch_system_mass` if it was not provided by the user.

        :math:`mass = k1*(k2*m_{blade}*n_{blades} + b1) + b2`

        where:

        - :math:`k1 =` :py:attr:`pitch_system_mass_coeff`
        - :math:`k2 =` :py:attr:`pitch_blade_mass_coeff`
        - :math:`n_{blades} =` :py:attr:`num_blades`
        - :math:`m_{blade} =` :py:attr:`blade_mass`
        - :math:`b1 =` :py:attr:`pitch_blade_mass_intercept`
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

        self.pitch_system_mass = (
            self.pitch_system_mass_coeff
            * (
                self.pitch_blade_mass_coeff * self.num_blades * self.blade_mass
                + self.pitch_blade_mass_intercept
            )
            + self.mass_sys_offset
        )

    def calculate_low_speed_shaft_mass(self):
        """Calculates and sets :py:attr:`low_speed_shaft_mass` if it was not provided by the user.

        :math:`m_{lss} = k1*rd^2 + k2*rd + b`.

        where:

        - :math:`k1 =` :py:attr:`lss_mass_coeff1`
        - :math:`rd =` :py:attr:`rotor_diameter`
        - :math:`k2 =` :py:attr:`lss_mass_coeff2`
        - :math:`b =` :py:attr:`lss_mass_intercept`

        Args:
            rotor_diameter (int, optional): Turbine rotor diameter, (:math:`m`).
            lss_mass_coeff1 (float): :math:`k1` in the polynomial low speed shaft mass equation.
            lss_mass_coeff2 (float): :math:`k2` in the polynomial low speed shaft mass equation.
            lss_mass_intercept (float): :math:`b1` in the low speed shaft mass equation.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("low_speed_shaft_mass")
        if exists:
            return

        self.low_speed_shaft_mass = (
            (self.lss_mass_coeff1 * self.rotor_diameter**2)
            + (self.lss_mass_coeff2 * self.rotor_diameter)
            + self.lss_mass_intercept
        )

    def calculate_gearbox_mass(self):
        """Calculates and sets :py:attr:`gearbox_mass` for the gearbox if it was not provided
        by the user.

        .. math:: k * torque ** b

        where:

        - :math:`k =` :py:attr:`gearbox_torque_density`
        - :math:`torque =` :py:attr:`rotor_torque`
        - :math:`b =` :py:attr:`gearbox_torque_exp`

        Args:
            rotor_torque (float): Turbine rotor torque at rated power (:math:`kNm`).
            gearbox_torque_density (float): :math:`k` in the mass equation above (:math:`N*m/kg`).
            gearbox_torque_exp (float): :math:`k` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("gearbox_mass")
        if exists:
            return

        self.gearbox_mass = self.gearbox_torque_density * self.rotor_torque**self.gearbox_torque_exp

    def calculate_gearbox_cost(self):
        """Calculates and sets :py:attr:`gearbox_cost` if it was not provided by the user.

        .. math:: k * m_{gearbox}

        where:

        - :math:`k =` :py:attr:`gearbox_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`gearbox_mass` (:math:`kg`).

        Args:
            gearbox_mass_cost_coeff (float): :math:`k` in the mass equation above.
            gearbox_mass (float): Main bearing mass (:math:`kg`). See
                :py:meth:`calculate_gearbox_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("gearbox_cost")
        if exists:
            return

        self.gearbox_cost = self.gearbox_mass * self.gearbox_mass_cost_coeff

    def calculate_brake_mass(self):
        """Calculates and sets :py:attr:`brake_mass` if it was not provided by the user.

        .. math:: k * power + b

        where:

        - :math:`k =` :py:attr:`brake_mass_coeff`
        - :math:`power =` :py:attr:`rated_power_kw`
        - :math:`b =` :py:attr:`brake_mass_intercept`

        Args:
            brake_mass_coeff (float): :math:`k` in the mass equation above (:math:`kg/kW`).
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
            brake_mass_intercept (bool): :math:`b` in the mass equation above (:math:`kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("brake_mass")
        if exists:
            return

        self.brake_mass = self.brake_mass_coeff * self.rated_power_kw + self.brake_mass_intercept

    def calculate_hydraulic_cooling_mass(self):
        """Sets :py:attr:`hydraulic_cooling_mass` as provided by the user.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("hydraulic_cooling_mass")
        if not exists:
            raise ValueError(
                "`hydraulic_cooling_mass` should be set by the user at initialization."
            )

    def calculate_bedplate_mass(self):
        """Calculates and sets :py:attr:`bedplate_mass` if it was not provided by the user.

        .. math:: k * rotor_diameter + b

        where:

        - :math:`b =` :py:attr:`bedplate_mass_coeff`
        - :math:`rotor_diameter =` :py:attr:`rotor_diameter`
        - :math:`b =` :py:attr:`bedplate_mass_intercept`

        Args:
            rotor_diameter (float): Turbine rotor diameter (:math:`m`).
            bedplate_mass_coeff (bool): :math:`b` in the mass equation above.
            bedplate_mass_intercept (bool): :math:`k` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("bedplate_mass")
        if exists:
            return

        self.bedplate_mass = (
            self.bedplate_mass_coeff * self.rotor_diameter + self.bedplate_mass_intercept
        )

    def calculate_platform_mainframe_mass(self):
        """Calculates and sets :py:attr:`platform_mainframe_mass` if it was not provided by the
        user.

        .. math::
            k * m_{bedplate}

        where:

        - :math:`k =` :py:attr:`platform_mainframe_mass_coeff`
        - :math:`m_{bedplate} =` :py:attr:`bedplate_mass`

        Args:
            platform_mainframe_mass_coeff (float): :math:`k` in the mass equation above.
            bedplate_mass (float): Bedplate mass (:math:`kg`). See
                :py:meth:`calculate_bedplate_mass` for details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("platform_mainframe_mass")
        if exists:
            return

        self.platform_mainframe_mass = self.platform_mainframe_mass_coeff * self.bedplate_mass

    def calculate_platform_mainframe_cost(self):
        r"""Calculates and sets :py:attr:`platform_mainframe_cost` if it was not provided by the
        user.

        .. math::
            k * m_{platform\_mainframe}

        where:

        - :math:`k =` :py:attr:`platform_mainframe_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`platform_mainframe_mass` (:math:`kg`).

        Args:
            platform_mainframe_mass_cost_coeff (float): Platform mainframe cost per kilogram
                (:math:`USD/kg`).
            platform_mainframe_mass (float): Platform mainframe mass (:math:`kg`).
                See :py:meth:`calculate_platform_mainframe_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("platform_mainframe_cost")
        if exists:
            return

        self.platform_mainframe_cost = (
            self.platform_mainframe_mass_cost_coeff * self.platform_mainframe_mass
        )

    def calculate_crane_mass(self):
        r"""Calculates and sets :py:attr:`crane_mass` if it was not provided by the user.

        .. math::
            m_{platform\_mainframe} & has\_crane \\
            0 & otherwise

        where:

        - :math:`m_{platform\_mainframe} =` :py:attr:`platform_mainframe_mass`
        - :math:`has\_crane =` :py:attr:`has_crane`

        Args:
            has_crane (bool): If True, set :py:attr:`crane_mass` to
                :py:attr:`platform_mainframe_mass`, otherwise 0.
            platform_mainframe_mass (float): Platform mainframe mass (:math:`kg`). See
                :py:meth:`calculate_platform_mainframe_mass` for details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("crane_mass")
        if exists:
            return

        self.crane_mass = self.platform_mainframe_mass if self.has_crane else 0.0

    def calculate_crane_cost(self):
        r"""Calculates and sets :py:attr:`crane_cost` if it was not provided by the user.

        .. math::
            k * m_{crane} & has\_crane \\
            0 & otherwise

        where:

        - :math:`k =` :py:attr:`crane_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m_{crane} =` :py:attr:`crane_mass` (:math:`kg`).
        - :math:`has\_crane =` :py:attr:`has_crane`

        Args:
            has_crane (bool): If True, set :py:attr:`crane_cost` to
                :py:attr:`crane_mass_cost_coeff` * :py:attr:`crane_mass`, otherwise 0.
            crane_mass_cost_coeff (float): Crane cost per kilogram (:math:`USD/kg`).
            crane_mass (float): Crane mass (:math:`kg`).
                See :py:meth:`calculate_platform_mainframe_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("crane_cost")
        if exists:
            return

        self.crane_cost = self.crane_mass_cost_coeff * self.crane_mass if self.has_crane else 0.0

    def calculate_tower_mass(self):
        r"""Calculates and sets :py:attr:`tower_mass` if it was not provided by the user.

        .. math:: k * H_{hub} * swept\_area + b

        where:

        - :math:`k =` :py:attr:`tower_mass_coeff`
        - :math:`H_{hub} =` :py:attr:`tower_length`
        - :math:`swept\_area = \pi * r^2` where :math:`r` = :py:attr:`rotor_diameter` / 2
        - :math:`b =` :py:attr:`tower_mass_intercept`

        Args:
            tower_mass_coeff (float): :math:`k` in the mass equation above (:math:`kg/m`).
            tower_length (float): For onshore turbines, this is the hub height (total length above
                ground). For offshore turbines, this is length from transition piece to hub height
                (:math:`m`).
            tower_mass_intercept (bool): :math:`b` in the mass equation above (:math:`kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("tower_mass")
        if exists:
            return

        self.tower_mass = (
            self.tower_mass_coeff * self.tower_length * (np.pi * (self.rotor_diameter / 2) ** 2)
            + self.tower_mass_intercept
        )

    def calculate_nacelle_mass(self):
        """Calculates and sets :py:attr:`nacelle_mass` (:math:`kg`) if it was not provided by the
        user.

        Sum of all above-tower components, excluding the blades (:py:meth:`calculate_rotor_mass`)
        and hub (:py:meth:`calculate_hub_system_mass`):

        - :py:attr:`low_speed_shaft_mass`
        - :py:attr:`bearing_mass` * :py:attr:`num_bearings`
        - :py:attr:`gearbox_mass`
        - :py:attr:`brake_mass`
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
        - :py:attr:`crane_mass`

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
            crane_mass (float): See :py:meth:`calculate_crane_mass` for more details.

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
                self.crane_mass,
            )
        )

    def calculate_nacelle_cost(self):
        """Calculates and sets :py:attr:`nacelle_cost`  (:math:`USD`) if it was not provided by the
        user.

        Sum of all above-tower components, excluding the blades (:py:meth:`calculate_rotor_cost`)
        and hub (:py:meth:`calculate_hub_system_cost`):

        - :py:attr:`low_speed_shaft_cost`
        - :py:attr:`bearing_cost` * :py:attr:`num_bearings`
        - :py:attr:`gearbox_cost`
        - :py:attr:`brake_cost`
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
        - :py:attr:`crane_cost`

        Args:
            low_speed_shaft_cost (float): See :py:meth:`calculate_low_speed_shaft_cost` for more
                details.
            num_bearings (int): Number of main bearings (:py:attr:`num_bearings`).
            bearing_cost (float): See :py:meth:`calculate_bearing_cost` for more details.
            gearbox_cost (float): See :py:meth:`calculate_gearbox_cost` for more details.
            brake_cost (float): See :py:meth:`calculate_brake_cost` for more details.
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
            crane_cost (float): See :py:meth:`calculate_crane_cost` for more details.

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
                self.crane_cost,
            )
        )

    def calculate_transport_cost(self):
        r"""Calculates and sets :py:attr:`platform_mainframe_cost` if it was not provided by the
        user.

        .. math::
            k * m_crane

        where:

        - :math:`k =` :py:attr:`crane_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`crane_mass` (:math:`kg`).

        Args:
            crane_mass_cost_coeff (float): Crane cost per kilogram (:math:`USD/kg`).
            crane_mass (float): Crane mass (:math:`kg`).
                See :py:meth:`calculate_platform_mainframe_mass` for more details.

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("transport_cost")
        if exists:
            return

        drivetrain_cost = (
            np.ceil(self.nacelle_mass / self.transport_drivetrain_cost_coeff1)
            * self.transport_drivetrain_cost_coeff2
        )
        power_electronics_cost = float(
            np.maximum(self.rated_power_kw - 30000, 0.0)
            * self.transport_power_electronics_cost_coeff
        )

        rotor_radius = self.rotor_diameter / 2.0
        blade_cost = self.num_blades * (
            self.transport_blade_cost_coeff1 * rotor_radius**3
            + self.transport_blade_cost_coeff2 * rotor_radius**2
            + self.transport_blade_cost_coeff3 * rotor_radius
            + self.transport_blade_cost_intercept
        )
        hub_cost = self.hub_mass + self.transport_hub_cost_intercept

        num_tower_sections = int(np.ceil(self.tower_mass / self.tower_section_mass_max))
        tower_cost = num_tower_sections * self.transport_tower_cost_coeff

        misc_parts_cost = self.transport_misc_parts_cost_coeff * self.turbine_mass

        self.transport_cost = (
            power_electronics_cost
            + drivetrain_cost
            + blade_cost
            + hub_cost
            + tower_cost
            + misc_parts_cost
        )

    def calculate_subsystem_mass(self):
        """Runs the base model's ``calculate_subsystem_mass``, then calculates additional
        subsystem masses added to the model.
        """
        super().calculate_subsystem_mass()
        self.calculate_crane_mass()

    def calculate_subsystem_cost(self):
        """Runs the base model's ``calculate_subsystem_mass``, then calculates additional
        subsystem costs added to the model.
        """
        super().calculate_subsystem_cost()
        self.calculate_crane_cost()

    def run(self):
        """Run the mass and cost calculations."""
        super().run()
        self.calculate_transport_cost()
