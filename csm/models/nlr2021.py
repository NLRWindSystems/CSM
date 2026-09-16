"""Provides the ``Land2021NLR`` model."""

from attrs import define, fields

from csm.models.utils import create_field
from csm.models.nlr2020 import Land2020NLR


base = fields(Land2020NLR)


@define
class Land2021NLR(Land2020NLR):
    r"""NLR 2021 empirically-based model used for development of the IRS Safe Harbor tables.

    Unused parameters from the base model:

    - :py:attr:`turbine_class`
    - :py:attr:`blade_has_carbon`
    - :py:attr:`hub_mass_intercept`
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
    - :py:attr:`converter_mass_cost_coeff`
    - :py:attr:`tower_mass_exp`

    Unused parameters from the 2020 model:

    - :py:attr:`pitch_system_mass_cost_coeff`

    Not updated from the 2015 model:

    - :py:attr:`pitch_bearing_mass_coeff`
    - :py:attr:`pitch_bearing_mass_intercept`
    - :py:attr:`bearing_housing_fraction`
    - :py:attr:`mass_sys_offset`

    Updated scaling relationships:

    - :py:attr:`blade_mass`
    - :py:attr:`pitch_system_mass`
    - :py:attr:`gearbox_mass`
    - :py:attr:`converter_cost`
    - :py:attr:`tower_mass`

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
        blade_mass_coeff (float): :math:`k_1` in the blade mass equation from
            :py:meth:`calculate_blade_mass`. Defaults to 8.3612.
        blade_mass_coeff2 (float): :math:`k_2` in the blade mass equation from
            :py:meth:`calculate_blade_mass`. Defaults to -620.03.
        blade_mass_intercept (float):  :math:`b` in the blade mass equation from
            :py:meth:`calculate_blade_mass`. Defaults to 17847.
        blade_mass_cost_coeff (float): Defaults to 15.9432.
        blade_mass (float): Blade mass (:math:`kg`). If not provided, calculated in
            :py:meth:`calculate_blade_mass`.
        blade_cost (float): Blade cost (:math:`USD`). If not provided, calculated in
            :py:meth:`calculate_blade_cost`.
        hub_mass_coeff (float): Defaults to 8104.7.
        hub_mass_exp (float): Defaults to 1.1377.
        hub_mass_cost_coeff (float): Defaults to 5.96232.
        pitch_bearing_mass_coeff (float): Not updated in 2015 or 2020. Defaults to 0.1295.
        pitch_bearing_mass_intercept (float): Not updated in 2015 or 2020. Defaults to 491.31 kg.
        bearing_housing_fraction (float): Not updated in 2015 or 2020. Defaults to 0.3280.
        mass_sys_offset (float): Not updated in 2015 or 2020. Defaults to 555.0 kg.
        pitch_system_mass_cost_coeff (float): Not updated in 2015 or 2020. Defaults to $22.1 USD/kg.
        spinner_mass_coeff (float): Defaults to 2.3255 :math:`kg/m`.
        spinner_mass_intercept (float): Defaults to 204.65 :math:`kg`.
        spinner_mass_cost_coeff (float): Defaults to 12.1212 :math:`USD/kg`.
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
        gearbox_torque_density (float): Updated to 132.5 Nm/kg.
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
        generator_mass_coeff (float): Defaults to 1.6731.
        generator_mass_intercept (float): Defaults to 3932.7.
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
        hvac_mass_coeff (float): Not used in 2020. Defaults to 0.
        hvac_mass_cost_coeff (float): Defaults to 135.408 :math:`USD/kg`.
        yaw_system_mass (float): Yaw system mass (:math:`kg`). See
            :py:meth:`calculate_yaw_system_mass` for more details.
        yaw_system_cost (float): Yaw system cost (:math:`USD`). See
            :py:meth:`calculate_yaw_system_cost` for more details.
        hydraulic_cooling_mass (float): Defaults to 221 :math:`kg`.
        hydraulic_cooling_cost (float): Hydraulic cooling cost (:math:`USD`). See
            :py:meth:`calculate_hydraulic_cooling_cost` for more details.
        nacelle_cover_mass_coeff (float): Defaults to 1.915 :math:`kg/kW`.
        nacelle_cover_mass_intercept (float): Defaults to 1910.
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
        converter_power_cost_coeff (float): Defaults to 50 :math:`USD/kW`.
        converter_mass (float): Power converter mass (:math:`kg`). See
            :py:meth:`calculate_converter_mass` for more details.
        converter_cost (float): Power converter cost (:math:`USD`). See
        controls_cost_coeff (float): 23.0958 :math:`USD/kW`.
        controls_mass (float): Controls mass (:math:`kg`). Defaults to 0 :math:`kg`.
        controls_cost (float): Controls cost (:math:`USD`). See
            :py:meth:`calculate_controls_cost` for more details.
        electrical_connection_cost_coeff (float): Defaults to 45.7002 :math:`USD/kW`.
        electrical_connection_mass (float): Electrical connection mass (:math:`kg`). See
            :py:meth:`calculate_electrical_connection_mass` for more details.
        electrical_connection_cost (float): Electrical connection cost (:math:`USD`). See
            :py:meth:`calculate_electrical_connection_cost` for more details.
            :py:meth:`calculate_converter_cost` for more details.
        tower_mass_coeff (float): Defaults to 0.000000043 :math:`kg/m`.
        tower_mass_coeff2 (float): Defaults to 0.064588.
        tower_mass_intercept (bool): Defaults to 48275.
        tower_mass_cost_coeff (float): Defaults to 3.1668 :math:`USD/kg`.
        tower_mass (float): Tower mass (:math:`kg`). See
            :py:meth:`calculate_tower_mass` for more details.
        tower_cost (float): Tower cost (:math:`USD`). See
            :py:meth:`calculate_tower_cost` for more details.
        transport_blade_cost_coeff (float): See :py:attr:`calculate_blade_transport_cost` for more
            details. Defaults to 0.543.
        transport_blade_cost_coeff2 (float): See :py:attr:`calculate_blade_transport_cost` for more
            details. Defaults to -7.4903.
        transport_blade_cost_coeff3 (float): See :py:attr:`calculate_blade_transport_cost` for more
            details. Defaults to -2847.5.
        transport_blade_cost_intercept (float): See :py:attr:`calculate_blade_transport_cost` for
            more details. Defaults to 103627 :math:`USD`.
        blade_transport_cost (float): Total blade transportation cost (:math:`USD`). See
            :py:meth:`calculate_blade_transport_cost` for more details.
        transport_hub_cost_intercept (float): See :py:attr:`calculate_hub_transport_cost` for more
            details. Defaults to 5000.
        hub_transport_cost (float): Total hub transportation cost (:math:`USD`). See
            :py:meth:`calculate_hub_transport_cost` for more details.
        transport_power_electronics_cost_coeff (float): See
            :py:attr:`calculate_power_electronics_transport_cost` for more details. Defaults to
            9 :math:`USD/kW`.
        power_electronics_transport_cost (float): Total power_electronics transportation cost
            (:math:`USD`). See :py:meth:`calculate_power_electronics_transport_cost` for more
            details.
        transport_drivetrain_cost_coeff (float): See :py:attr:`calculate_drivetrain_transport_cost`
            for more details. Defaults to 9000 :math:`kg`.
        transport_drivetrain_cost_coeff2 (float): See :py:attr:`calculate_drivetrain_transport_cost`
            for more details. Defaults to 45000 :math:`USD`.
        drivetrain_transport_cost (float): Total drivetrain transportation cost (:math:`USD`). See
            :py:meth:`calculate_drivetrain_transport_cost` for more details.
        tower_section_mass_max (float): Maximum mass of each tower section. See
            :py:attr:`calculate_num_tower_sections` for more details. Defaults to 80000
            :math:`kg`.
        num_tower_sections (float): Total number of tower sections. See
            :py:attr:`calculate_tower_transport_cost` for more details if not providing directly.
        transport_tower_cost_coeff (float): Transportation cost for a single tower section. See
            :py:attr:`calculate_tower_transport_cost` for more details. Defaults to 34083
            :math:`USD`.
        tower_transport_cost (float): Total tower transportation cost (:math:`USD`). See
            :py:meth:`calculate_tower_transport_cost` for more details.
        transport_misc_parts_cost_coeff (float): See :py:attr:`calculate__transport_cost` for more
            details. Defaults to 0.025 :math:`USD/kg`.
        parts_transport_cost (float): Total transportation cost of miscellaneous parts
            (:math:`USD`). See :py:meth:`calculate_parts_transport_cost` for more details.
        transport_cost (float): Total transportation cost (:math:`USD`). See
            :py:meth:`calculate_transport_cost` for more details.
        blade_mass_exp (float): Unused in the 2021 model. Defaults to 0.
        pitch_bearing_mass_coeff (float): The pitch system is incorporated into the hub for 2021,
            so it is not explicitly modeled for 2020 and later models. Defaults to 0.
        pitch_bearing_mass_intercept (float): The pitch system is incorporated into the hub for
            2021, so it is not explicitly modeled for 2020 and later models. Defaults to 0.
        bearing_housing_fraction (float): The pitch system is incorporated into the hub for 2021,
            so it is not explicitly modeled for 2020 and later models. Defaults to 0.
        mass_sys_offset (float): The pitch system is incorporated into the hub for 2021,
            so it is not explicitly modeled for 2020 and later models. Defaults to 0.
        pitch_system_mass_cost_coeff (float): The pitch system is incorporated into the hub for
            2021, so it is not explicitly modeled for 2020 and later models. Defaults to 0.
        mass_sys_offset (float): The pitch system is incorporated into the hub for
            2021, so it is not explicitly modeled for 2020 and later models. Defaults to 0.
        pitch_system_mass (float): The pitch system is incorporated into the hub for
            2021, so it is not explicitly modeled for 2020 and later models. Defaults to 0.
        pitch_system_cost (float): The pitch system is incorporated into the hub for
            2021, so it is not explicitly modeled for 2020 and later models. Defaults to 0.
        gearbox_torque_exp (float): Not used int the 2021 model. Defaults to 0.
        hss_mass_coeff (float): High speed shaft is not modeled for 2020 and later models.
            Defaults to 0
        hss_mass_cost_coeff (float): High speed shaft is not modeled for 2020 and later models.
            Defaults to 0
    """

    blade_mass_coeff = base.blade_mass_coeff.reuse(default=8.3612)
    blade_mass_coeff2: float = create_field(float, "unitless", "input", default=-620.03)
    blade_mass_intercept: float = create_field(float, "unitless", "input", default=17847)
    hub_mass_coeff = base.hub_mass_coeff.reuse(default=8104.7)
    hub_mass_exp = create_field(float, "unitless", "input", default=1.1377)
    hub_mass_cost_coeff = base.hub_mass_cost_coeff.reuse(default=5.96232)
    gearbox_torque_density = base.gearbox_torque_density.reuse(default=132.5)
    generator_mass_coeff = base.generator_mass_coeff.reuse(default=1.6731)
    generator_mass_intercept = base.generator_mass_intercept.reuse(default=3932.7)
    nacelle_cover_mass_coeff = base.nacelle_cover_mass_coeff.reuse(default=1.915)
    nacelle_cover_mass_intercept = base.nacelle_cover_mass_intercept.reuse(default=1910)
    converter_power_cost_coeff = create_field(float, "USD/kW", "input", default=50)
    tower_mass_coeff = base.tower_mass_coeff.reuse(default=0.000000043)
    tower_mass_coeff2: float = create_field(float, "unitless", "input", default=0.064588)
    tower_mass_intercept: float = create_field(float, "unitless", "input", default=48275)

    # unused attributes
    hub_mass_intercept = base.hub_mass_intercept.reuse(default=0)
    converter_mass_cost_coeff = base.converter_mass_cost_coeff.reuse(default=0)
    pitch_blade_mass_coeff = base.pitch_blade_mass_coeff.reuse(default=0)
    pitch_system_mass_coeff = base.pitch_system_mass_coeff.reuse(default=0)
    pitch_blade_mass_intercept = base.pitch_blade_mass_intercept.reuse(default=0)
    mass_sys_offset = base.mass_sys_offset.reuse(default=0)
    pitch_system_mass = base.pitch_system_mass.reuse(default=0)
    pitch_system_cost = base.pitch_system_cost.reuse(default=0)
    gearbox_torque_exp = base.gearbox_torque_exp.reuse(default=0)

    def __attrs_post_init__(self):
        """Updates the parameter mapping for new mass and cost relationships."""
        self.parameter_map["blade_mass"] = (
            "rotor_diameter",
            "blade_mass_coeff",
            "blade_mass_coeff2",
            "blade_mass_intercept",
        )
        self.parameter_map["pitch_system_mass"] = ("pitch_system_mass",)
        self.parameter_map["hub_mass"] = (
            "rated_power_kw",
            "hub_mass_coeff",
            "hub_mass_exp",
        )
        self.parameter_map["gearbox_mass"] = ("rotor_torque", "gearbox_mass_coeff")
        self.parameter_map["converter_cost"] = ("converter_power_cost_coeff", "rated_power_kw")
        self.parameter_map["tower_mass"] = (
            "rotor_diameter",
            "tower_length",
            "tower_mass_coeff",
            "tower_mass_coeff2",
            "tower_mass_intercept",
        )
        super().__attrs_post_init__()

    def calculate_blade_mass(self):
        """Calculates and sets :py:attr:`blade_mass` if it was not provided by the user.

        .. math:: k_1 * r^2 + k_2 * r + b

        where:

        - :math:`k_1 =` :py:attr:`blade_mass_coeff`
        - :math:`k_2 =` :py:attr:`blade_mass_coeff2`
        - :math:`r =` :py:attr:`rotor_diameter` / 2
        - :math:`b =` :py:attr:`blade_mass_intercept`

        Args:
            blade_mass_coeff (float): :math:`k_1` in the mass equation above.
            blade_mass_coeff2 (float): :math:`k_2` in the mass equation above.
            rotor_diameter (float): Diameter of the swept area of the turbine blades.
            blade_mass_intercept (float): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("blade_mass")
        if exists:
            return

        self.blade_mass = (
            self.blade_mass_coeff * self.rotor_radius**2
            + self.blade_mass_coeff2 * self.rotor_radius
            + self.blade_mass_intercept
        )

    def calculate_hub_mass(self):
        """Calculates and sets :py:attr:`hub_mass` if it was not provided by the user.

        .. math:: k * power ^ b

        where:

        - :math:`k =` :py:attr:`hub_mass_coeff`
        - :math:`power =` :py:attr:`rated_power_mw`
        - :math:`b =` :py:attr:`hub_mass_exp`

        Args:
            hub_mass_coeff (float): :math:`k` in the mass equation above (:math:`kg/kW`).
            rated_power_mw (float): Turbine nameplate capacity (rated power) (:math:`MW`).
            hub_mass_exp (bool): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("hub_mass")
        if exists:
            return

        self.hub_mass = self.hub_mass_coeff * self.rated_power_mw**self.hub_mass_exp

    def calculate_gearbox_mass(self):
        r"""Calculates and sets :py:attr:`gearbox_mass` for the gearbox if it was not provided
        by the user.

        .. math:: \tau * 1000 / k

        where:

        - :math:`\tau =` :py:attr:`rotor_torque`
        - :math:`k =` :py:attr:`gearbox_torque_density`

        Args:
            rotor_torque (float): Turbine rotor torque at rated power (:math:`kNm`).
            gearbox_torque_density (float): :math:`k` in the mass equation above (:math:`N*m/kg`).

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("gearbox_mass")
        if exists:
            return

        self.gearbox_mass = self.rotor_torque * 1000 / self.gearbox_torque_density

    def calculate_converter_cost(self):
        """Calculates and sets :py:attr:`converter_cost` if it was not provided by the user.

        .. math:: k * power

        where:

        - :math:`k =` :py:attr:`converter_power_cost_coeff` (:math:`USD/kW`)
        - :math:`power =` :py:attr:`rated_power_kW` (:math:`kW`).

        Args:
            converter_power_cost_coeff (float): Power converter cost per kW of capacity
                (:math:`USD/kW`).
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).

        Raises:
            ValueError: Raised if any of the required parameters have not been provided.
        """
        exists = self._prepare_calculation("converter_cost")
        if exists:
            return

        self.converter_cost = self.converter_power_cost_coeff * self.rated_power_kw

    def calculate_tower_mass(self):
        """Calculates and sets :py:attr:`tower_mass` if it was not provided by the user.

        .. math:: k_1 * (A * H_{hub})^2 + k_2 * A * H_{hub} + b

        where:

        - :math:`k_1 =` :py:attr:`tower_mass_coeff`
        - :math:`A =` :py:attr:`swept_area`
        - :math:`H_{hub} =` :py:attr:`tower_length`
        - :math:`k_2 =` :py:attr:`tower_mass_coeff2`
        - :math:`b =` :py:attr:`tower_mass_intercept`

        Args:
            tower_mass_coeff (float): :math:`k` in the mass equation above.
            tower_mass_coeff2 (float): :math:`k` in the mass equation above.
            rotor_diameter (float): Diameter of the rotor swept area; used to calculate
                :py:attr:`swept_area`.
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
            self.tower_mass_coeff * (self.tower_length * self.swept_area) ** 2
            + self.tower_mass_coeff2 * self.tower_length * self.swept_area
            + self.tower_mass_intercept
        )
