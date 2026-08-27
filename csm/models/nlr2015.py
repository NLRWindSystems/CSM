"""Experimental generic new model generation and 2015 replication."""

from attrs import define, fields

from csm.models.base_model import CSMBase


base = fields(CSMBase)


@define
class Land2015NLR(CSMBase):
    r"""Replication of the original Excel-based CSM model created in 2006 and modified in 2015 with
    updates for land-based turbines in 2015. Scaling factor updates from 2020 and 2024 made in the
    WISDEM implementation have been carried over for consistency. For complete details on all
    arguments, attributes, and methods please see the :py:class:`csm.models.base_model.CSMBase`
    documentation. All listed attributes below describe the models defaults and any relevant
    contextual information.

    Original (2006) model defaults:

    - :py:attr:`pitch_bearing_mass_coeff`
    - :py:attr:`pitch_bearing_mass_intercept`
    - :py:attr:`bearing_housing_fraction`
    - :py:attr:`mass_sys_offset`
    - :py:attr:`pitch_system_mass_cost_coeff`
    - :py:attr:`yaw_mass_coeff`
    - :py:attr:`yaw_mass_exp`
    - :py:attr:`hvac_mass_coeff`
    - :py:attr:`hvac_mass_coeff`
    - :py:attr:`hvac_mass_cost_coeff`
    - :py:attr:`nacelle_cover_mass_coeff`
    - :py:attr:`nacelle_cover_mass_intercept`
    - :py:attr:`nacelle_cover_mass_cost_coeff`
    - :py:attr:`electrical_connection_cost_coeff`
    - :py:attr:`controls_cost_coeff`
    - :py:attr:`platform_mainframe_mass_coeff`
    - :py:attr:`platform_mainframe_mass_cost_coeff`
    - :py:attr:`crane_mass`
    - :py:attr:`crane_cost`

    2020 & 2024 model updates:

    - :py:attr:`brake_mass_cost_coeff` (2020)
    - :py:attr:`gearbox_torque_density` (2024)



    Args:
        num_blades (int, optional): Number of turbine blades. Defaults to 3.
        rated_power_kw (float): Turbine rated power (:math:`kW`).
        rotor_diameter (float): Diameter of the swept area of the turbine blades (:math:`m`).
        turbine_class (int): Turbine classification; use 1 for IEC Wind-Class I, 2 for
            IEC Wind-Class II or III.
        num_bearings (int): Number of main bearings.
        max_tip_speed (float): Maximum allowable blade tip speed (:math:`m/s`).
        tower_length (float): For onshore turbines, this is the hub height (total length above
            ground). For offshore turbines, this is length from transition piece to hub height
            (:math:`m`).
        blade_has_carbon (bool): Use True if the blade has carbon, False if not.
        blade_mass_coeff (float): :math:`k` in the blade mass equation from
            :py:meth:`calculate_blade_mass`. Defaults to 0.5.
        blade_mass_cost_coeff (float): Blade cost per kilogram (:math:`USD/kg`). Defaults to 14.6.
        blade_mass (float): Blade mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_blade_mass`.
        blade_cost (float): Blade cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_blade_cost`.
        hub_mass_coeff (float): :math:`k` in the hub mass equation from
            :py:meth:`calculate_hub_mass`. Defaults to 2.3.
        hub_mass_intercept (bool): :math:`b` in the hub mass equation from
            :py:meth:`calculate_hub_mass`. Defaults to .
        hub_mass_cost_coeff (float): Hub cost per kilogram (:math:`USD/kg`) from
            :py:meth:`calculate_hub_cost`. Defaults to .
        hub_mass (float): Hub mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_hub_mass`.
        hub_cost (float): Hub cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_hub_cost`.
        pitch_bearing_mass_coeff (float): :math:`k` in the pitch bearing mass equation from
            :py:meth:`calculate_pitch_system_mass`. Defaults to 0.1295.
        pitch_bearing_mass_intercept (float): :math:`b1` in the pitch bearing mass equation from
            :py:meth:`calculate_pitch_system_mass`. Defaults to 491.31.
        bearing_housing_fraction (float): Mass of the housing for the bearing as a fraction of
            the bearing mass. :math:`h` in the pitch system mass equation from
            :py:meth:`calculate_pitch_system_mass`. Defaults to 0.3280.
        mass_sys_offset (float): :math:`b2` in the pitch system mass equation from
            :py:meth:`calculate_pitch_system_mass`. Defaults to 555.
        pitch_system_mass_cost_coeff (float): Pitch system cost per kilogram (:math:`USD/kg`) from
            :py:meth:`calculate_pitch_system_cost`. Not updated in 2015, so is the original $22.1
            :math:`USD/kg` Defaults to 22.1.
        pitch_system_mass (float): Pitch system mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_pitch_system_mass`.
        pitch_system_cost (float): Pitch system cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_pitch_system_cost`.
        spinner_mass_coeff (float): :math:`k` in the mass equation above from
            :py:meth:`calculate_spinner_mass`. Defaults to 15.5.
        spinner_mass_intercept (bool): :math:`b` in the mass equation above from
            :py:meth:`calculate_spinner_mass`. Defaults to -980.0.
        spinner_mass_cost_coeff (float): Spinner cost per kilogram (:math:`USD/kg`) from
            :py:meth:`calculate_spinner_cost`. Defaults to 11.1.
        spinner_mass (float): Spinner mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_spinner_mass`.
        spinner_cost (float): Spinner cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_spinner_cost`.
        lss_mass_coeff (float): :math:`k` in the low speed shaft mass equation from
            :py:meth:`calculate_low_speed_shaft_mass`. Defaults to 13.0.
        lss_mass_exp (float): :math:`b1` in the low speed shaft mass equation from
            :py:meth:`calculate_low_speed_shaft_mass`. Defaults to 0.65.
        lss_mass_intercept (float): :math:`b2` in the low speed shaft mass equation from
            :py:meth:`calculate_low_speed_shaft_mass`. Defaults to 775.
        lss_mass_cost_coeff (float): Low speed shaft cost per kilogram (:math:`USD/kg`). Defaults to
            11.9.
        low_speed_shaft_mass (float): Low speed shaft mass (:math:`kg`). If not provided,
            calculated in :py:meth:`calculate_low_speed_shaft_mass`.
        low_speed_shaft_cost (float): Low speed shaft cost (:math:`USD`). If not provided,
            calculated in :py:meth:`calculate_low_speed_shaft_cost`.
        bearing_mass_coeff (float): :math:`k` in the bearing mass equation from
            :py:meth:`calculate_bearing_mass`. Defaults to 0.0001.
        bearing_mass_exp (bool): :math:`b` in the bearing mass equation from
            :py:meth:`calculate_bearing_mass`. Defaults to 3.5.
        bearing_mass_cost_coeff (float): Main bearing cost per kilogram (:math:`USD/kg`). Defaults
            to 4.5.
        bearing_mass (float): Main bearing mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_bearing_mass`.
        bearing_cost (float): Main bearing cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_bearing_cost`.
        efficiency_max (float): Maximum possible drivetrain efficiency. Defaults to 1.0.
        gearbox_torque_density (float): Gearbox torque per kilogram of mass from
            :py:meth:`calculate_gearbox_mass` and :py:meth:`calculate_gearbox_cost`
            (:math:`N*m/kg`). Defaults to 200.
        gearbox_torque_cost (float): Gearbox cost per unit of torque (:math:`USD/kN/m`) from
            :py:meth:`calculate_gearbox_cost`. Defaults to 50.
        rated_rpm (float): Rated RPM of the turbine based on the :py:attr:`max_tip_speed`
            and :py:attr:`rotor_diameter`. If not provided, calculated in
            :py:meth:`calculate_rotor_torque`.
        rotor_torque (float): Maximum torque produced under normal operations of the turbine
            (kNm). If not provided, calculated in :py:meth:`calculate_rotor_torque`.
        gearbox_mass (float): Gearbox mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_gearbox_mass`.
        gearbox_cost (float): Gearbox cost (:math:`USD`). If not provided, calculated in\
                :py:meth:`calculate_gearbox_cost`.
        brake_mass_coeff (bool): :math:`k` in the brake mass equation from
            :py:meth:`calculate_brake_mass`. Defaults to 0.00122.
        brake_mass_cost_coeff (float): Brake cost per kilogram (:math:`USD/kg`). Defaults to 3.6254.
        brake_mass (float): Brake mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_brake_mass`.
        brake_cost (float): Brake cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_brake_cost`.
        hss_mass_coeff (float): Mass scaling coefficient, :math:`k` in the mass equation. Defaults
            to 0.19894.
        hss_mass_cost_coeff (float): High speed shaft cost, per kilogram of mass, :math:`k` in the
            equation above (:math:`USD/kg`). Defaults to 6.8.
        high_speed_shaft_mass (float): High speed shaft mass (:math:`kg`).
            If not provided, calculated in :py:meth:`calculate_high_speed_shaft_mass`.
        high_speed_shaft_cost (float): High speed shaft cost (:math:`USD`).
            If not provided, calculated in :py:meth:`calculate_high_speed_shaft_cost`.
        generator_mass_coeff (float): :math:`k` in the generator mass equation above (:math:`kg/kW`)
            from :py:meth:`calculate_generator_mass`. Defaults to 2.3.
        generator_mass_intercept (bool): :math:`b` in the generator mass equation above (:math:`kg`)
            from :py:meth:`calculate_generator_mass`. Defaults to 3400.
        generator_mass_cost_coeff (float): generator cost per kilogram (:math:`USD/kg`). Defaults to
            12.4.
        generator_mass (float): Generator mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_generator_mass`.
        generator_cost (float): Generator cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_generator_cost`.
        bedplate_mass_exp (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_bedplate_mass`. Defaults to 2.2.
        bedplate_mass_cost_coeff (float): bedplate cost per kilogram (:math:`USD/kg`). Defaults to
            2.9.
        bedplate_mass (float): Bedplate mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_bedplate_mass`.
        bedplate_cost (float): Bedplate cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_bedplate_cost`.
        yaw_system_non_bearing_mass_coeff (float): :math:`k1` in the mass equation from
            :py:meth:`calculate_yaw_system_mass` to account for non-bearing mass. Defaults to 1.5.
        yaw_system_mass_coeff (float): :math:`k2` in the mass equation from
            :py:meth:`calculate_yaw_system_mass`. Defaults to 0.0009.
        yaw_system_mass_exp (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_yaw_system_mass`. Defaults to 3.314.
        yaw_system_mass_cost_coeff (float): Yaw system cost per kilogram (:math:`USD/kg`). Defaults
            to 8.3.
        yaw_system_mass (float): Yaw system mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_yaw_system_mass`.
        yaw_system_cost (float): Yaw system cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_yaw_system_cost`.
        hvac_mass_coeff (float): Mass scaling coefficient. Defaults to 0.08.
        hvac_mass_cost_coeff (float): Hydraulic cooling cost, per kilogram of mass. Defaults to 124.
        hydraulic_cooling_mass (float): Hydraulic cooling mass (:math:`kg`). If not provided,
            calculated in :py:meth:`calculate_hydraulic_cooling_mass`.
        hydraulic_cooling_cost (float): Hydraulic cooling cost (:math:`USD`). If not provided,
            calculated in :py:meth:`calculate_hydraulic_cooling_cost`.
        nacelle_cover_mass_coeff (float): :math:`k` in the mass equation from
            :py:meth:`calculate_nacelle_cover_mass`. Defaults to 1.2817.
        nacelle_cover_mass_intercept (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_nacelle_cover_mass`. Defaults to 428.19.
        nacelle_cover_mass_cost_coeff (float): Nacelle cover cost per kilogram (:math:`USD/kg`).
            Defaults to 5.7.
        nacelle_cover_mass (float): nacelle_cover mass (:math:`kg`). If not provided, calculated
            in :py:meth:`calculate_nacelle_cover_mass`.
        nacelle_cover_cost (float): nacelle_cover mass (:math:`USD`). If not provided, calculated
            in :py:meth:`calculate_nacelle_cover_cost`.
        platform_mainframe_mass_coeff (float): :math:`k` from
            :py:meth:`calculate_platform_mainframe_mass`. Defaults to 0.125.
        has_crane (bool): If True, apply :py:attr:`crane_mass` to
            :py:meth:`calculate_platform_mainframe_mass` and :py:attr:`crane_cost` to
            :py:meth:`calculate_platform_mainframe_cost`, otherwise ignore. Defaults to False.
        crane_mass (bool): Mass of onboard crane, if :py:attr:`has_crane`, :math:`m_{crane}` from
            :py:meth:`calculate_platform_mainframe_mass`. Defaults to 3000.
        crane_cost (bool): Cost of onboard crane, if :py:attr:`has_crane`, :math:`b` in the
            mass equation above. Defaults to 12000.
        platform_mainframe_mass_cost_coeff (float): Platform mainframe cost per kilogram
            (:math:`USD/kg`). Defaults to 17.1.
        platform_mainframe_mass (float): Platform mainframe mass (:math:`kg`).
            If not provided, calculated in :py:meth:`calculate_platform_mainframe_mass`.
        platform_mainframe_cost (float): Platform mainframe cost (:math:`USD`).
            If not provided, calculated in :py:meth:`calculate_platform_mainframe_cost`.
        controls_mass (float): Controls mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_controls_mass`.
        controls_cost_coeff (float): Controls cost per kilowatt of capacity
            (:math:`USD/kW`). Defaults to 21.15.
        controls_cost (float): Controls cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_controls_cost`.
        electrical_connection_mass (float): Electrical connection mass (:math:`kg`). If not
            provided, calculated in :py:meth:`calculate_electrical_connection_mass`.
        electrical_connection_cost_coeff (float): Electrical connection cost per
            kilowatt (:math:`USD/kW`). Defaults to 41.85.
        electrical_connection_cost (float): Electrical connection cost (:math:`USD`). If not
            provided, calculated in :py:meth:`calculate_electrical_connection_cost`.
        converter_mass (float): Power converter mass (:math:`kg`). If not provided, calculated
            in :py:meth:`calculate_converter_mass`.
        converter_mass_cost_coeff (float): Power converter cost per kilogram (:math:`USD/kg`). If
            not provided, calculated in :py:meth:`calculate_converter_cost`.
        converter_cost (float): Power converter cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_converter_cost`.
        transformer_mass_coeff (float): :math:`k` in the mass equation from
            :py:meth:`calculate_transformer_mass`. Defaults to 1.915.
        transformer_mass_intercept (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_transformer_mass`. Defaults to 1910.
        transformer_mass_cost_coeff (float): Transformer cost per kilogram (:math:`USD/kg`).
            Defaults to 18.8.
        transformer_mass (float): Transformer cover mass (:math:`kg`). If not provided, calculated
            in :py:meth:`calculate_transformer_mass`.
        transformer_cost (float): Transformer cover cost (:math:`USD`). If not provided, calculated
            in :py:meth:`calculate_transformer_cost`.
        tower_mass_coeff (float): :math:`k` in the mass from :py:meth:`calculate_tower_mass`
            (:math:`kg/m`). Defaults to 19.828.
        tower_mass_exp (bool): :math:`b` in the mass equation from
            :py:meth:`calculate_tower_mass`. Defaults to .
        tower_mass_cost_coeff (float): Tower cover cost per kilogram (:math:`USD/kg`). Defaults
            to 2.9.
        tower_mass (float): Tower mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_tower_mass`.
        tower_cost (float): Tower cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_tower_cost`.
        nacelle_mass (float): Total nacelle mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_nacelle_mass`.
        nacelle_cost (float): Total nacelle cost (US). If not provided, calculated in
            :py:meth:`calculate_nacelle_cost`.
        hub_system_mass (float): Total hub system mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_hub_system_mass`.
        hub_system_cost (float): Total hub system cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_hub_system_cost`.
        rotor_mass (float): Total rotor mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_rotor_mass`.
        rotor_cost (float): Total rotor cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_rotor_cost`.
        turbine_mass (float): Total turbine mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_turbine_mass`.
        turbine_cost (float): Total turbine cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_turbine_cost`.
        turbine_cost (float): Total turbine cost, normalized by
            :py:attr:`rated_power_kw` (:math:`USD/kW`).
    """

    efficiency_max = base.efficiency_max.reuse(default=1.0)
    blade_mass_coeff = base.blade_mass_coeff.reuse(default=0.5)
    blade_mass_cost_coeff = base.blade_mass_cost_coeff.reuse(default=14.6)
    hub_mass_coeff = base.hub_mass_coeff.reuse(default=2.3)
    hub_mass_intercept = base.hub_mass_intercept.reuse(default=1320.0)
    hub_mass_cost_coeff = base.hub_mass_cost_coeff.reuse(default=3.9)
    pitch_bearing_mass_coeff = base.pitch_bearing_mass_coeff.reuse(default=0.1295)
    pitch_bearing_mass_intercept = base.pitch_bearing_mass_intercept.reuse(default=491.31)
    bearing_housing_fraction = base.bearing_housing_fraction.reuse(default=0.3280)
    mass_sys_offset = base.mass_sys_offset.reuse(default=555.0)
    pitch_system_mass_cost_coeff = base.pitch_system_mass_cost_coeff.reuse(default=22.1)
    spinner_mass_coeff = base.spinner_mass_coeff.reuse(default=15.5)
    spinner_mass_intercept = base.spinner_mass_intercept.reuse(default=-980.0)
    spinner_mass_cost_coeff = base.spinner_mass_cost_coeff.reuse(default=11.1)
    lss_mass_coeff = base.lss_mass_coeff.reuse(default=13.0)
    lss_mass_exp = base.lss_mass_exp.reuse(default=0.65)
    lss_mass_intercept = base.lss_mass_intercept.reuse(default=775.0)
    lss_mass_cost_coeff = base.lss_mass_cost_coeff.reuse(default=11.9)
    bearing_mass_coeff = base.bearing_mass_coeff.reuse(default=0.0001)
    bearing_mass_exp = base.bearing_mass_exp.reuse(default=3.5)
    bearing_mass_cost_coeff = base.bearing_mass_cost_coeff.reuse(default=4.5)
    gearbox_torque_density = base.gearbox_torque_density.reuse(default=200)
    gearbox_torque_cost = base.gearbox_torque_cost.reuse(default=50)
    brake_mass_coeff = base.brake_mass_coeff.reuse(default=0.00122)
    brake_mass_cost_coeff = base.brake_mass_cost_coeff.reuse(default=3.6254)
    hss_mass_coeff = base.hss_mass_coeff.reuse(default=0.19894)
    hss_mass_cost_coeff = base.hss_mass_cost_coeff.reuse(default=6.8)
    generator_mass_coeff = base.generator_mass_coeff.reuse(default=2.3)
    generator_mass_intercept = base.generator_mass_intercept.reuse(default=3400)
    generator_mass_cost_coeff = base.generator_mass_cost_coeff.reuse(default=12.4)
    bedplate_mass_exp = base.bedplate_mass_exp.reuse(default=2.2)
    bedplate_mass_cost_coeff = base.bedplate_mass_cost_coeff.reuse(default=2.9)
    yaw_system_non_bearing_mass_coeff = base.yaw_system_non_bearing_mass_coeff.reuse(default=1.5)
    yaw_system_mass_coeff = base.yaw_system_mass_coeff.reuse(default=0.0009)
    yaw_system_mass_exp = base.yaw_system_mass_exp.reuse(default=3.314)
    yaw_system_mass_cost_coeff = base.yaw_system_mass_cost_coeff.reuse(default=8.3)
    hvac_mass_coeff = base.hvac_mass_coeff.reuse(default=0.08)
    hvac_mass_cost_coeff = base.hvac_mass_cost_coeff.reuse(default=124)
    nacelle_cover_mass_coeff = base.nacelle_cover_mass_coeff.reuse(default=1.2817)
    nacelle_cover_mass_intercept = base.nacelle_cover_mass_intercept.reuse(default=428.19)
    nacelle_cover_mass_cost_coeff = base.nacelle_cover_mass_cost_coeff.reuse(default=5.7)
    platform_mainframe_mass_coeff = base.platform_mainframe_mass_coeff.reuse(default=0.125)
    has_crane = base.has_crane.reuse(default=False)
    crane_mass = base.crane_mass.reuse(default=3000)
    platform_mainframe_mass_cost_coeff = base.platform_mainframe_mass_cost_coeff.reuse(default=17.1)
    crane_cost = base.crane_cost.reuse(default=12000.0)
    controls_cost_coeff = base.controls_cost_coeff.reuse(default=21.15)
    converter_mass_cost_coeff = base.converter_mass_cost_coeff.reuse(default=18.8)
    electrical_connection_cost_coeff = base.electrical_connection_cost_coeff.reuse(default=41.85)
    transformer_mass_coeff = base.transformer_mass_coeff.reuse(default=1.9150)
    transformer_mass_intercept = base.transformer_mass_intercept.reuse(default=1910.0)
    transformer_mass_cost_coeff = base.transformer_mass_cost_coeff.reuse(default=18.8)
    tower_mass_coeff = base.tower_mass_coeff.reuse(default=19.828)
    tower_mass_exp = base.tower_mass_exp.reuse(default=2.0282)
    tower_mass_cost_coeff = base.tower_mass_cost_coeff.reuse(default=2.9)
