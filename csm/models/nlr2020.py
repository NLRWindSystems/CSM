"""Experimental generic new model generation and 2015 replication."""

from attrs import define, fields

from csm.models.utils import create_field
from csm.models.base_model import CSMBase


base = fields(CSMBase)


@define
class Land2020NLR(CSMBase):
    r"""NLR 2020 empirically-based model. For complete details on all arguments, attributes, and
    methods, please see the :py:class:`csm.models.base_model.CSMBase` documentation. All listed
    attributes below describe the models defaults and any relevant contextual information.

    Below the args will solely be the inputs that do not have a default value chose for the 2020
    analysis year, and the parameters section will list the default values and any contextual
    information when available.

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
        turbine_class (int): Unused in the 2020 model. Defaults to 1.
        blade_mass_coeff (float): Defaults to 9.2157.
        blade_mass_exp (float): Defaults to 1.7679.
        blade_mass_cost_coeff (float): Defaults to 15.9432.
        blade_mass (float):
            ..math::
                blade\_mass = blade\_mass\_coeff * (\frac{rotor\_diameter}{2}) ^ {blade\_mass\_exp}
        hub_mass_coeff (float): Defaults to 3.5793.
        hub_mass_intercept (float): Defaults to -25451.58.
        hub_mass_cost_coeff (float): Defaults to 4.2588.
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
        low_speed_shaft_mass (float):

            .. math::
                low\_speed\_shaft\_mass = lss\_mass\_coeff1 * {rotor\_diameter} ^ 2
                + lss\_mass\_coeff2 * {rotor\_diameter}
                + {lss\_mass\_intercept}

        low_speed_shaft_cost (float):

            .. math::
                low\_speed\_shaft\_cost = {low\_speed\_shaft\_mass} * {spinner\_mass\_cost\_coeff}

        bearing_mass_coeff (float): Defaults to 0.0001.
        bearing_mass_exp (float): Defaults to 3.5.
        bearing_mass_cost_coeff (float): Defaults to 4.914 :math:`USD/kg`.
        gearbox_torque_density (float): In 2024, modern 5-7MW gearboxes are able to reach 200 Nm/kg.
        gearbox_torque_cost (float): In 2024, modern 5-7MW gearboxes cost approximately $50/kNm.
        brake_mass_cost_coeff (float): In 2020, updated to $3.6254 USD/kg. Regression based sizing
            derived by J.Keller under FOA 1981 support project.
        hss_mass_coeff (float): High speed shaft is not modeled for 2020. Defaults to 0
        hss_mass_cost_coeff (float): High speed shaft is not modeled for 2020. Defaults to 0
        generator_mass_coeff (float): Defaults to 1754.
        generator_mass_intercept (float): Defaults to 3503.6.
        generator_mass_cost_coeff (float): Defaults to 13.5408 :math:`USD/kg`.
        bedplate_mass_exp (float): Unused in the 2020 model. Defaults to 0.
        bedplate_mass_coeff (float): Defaults to 737.88.
        bedplate_mass_intercept (float): Defaults to -68066.
        bedplate_mass_cost_coeff (float): Defaults to 3.1668 :math:`USD/kg`.
        bedplate_mass (float):

            .. math::
                bedplate\_mass = bedplate\_mass\_coeff * rotor\_diameter + bedplate\_mass\_intercept

        yaw_system_non_bearing_mass_coeff (float): Defaults to 1.6.
        yaw_system_mass_coeff (float): Defaults to 0.0007.
        yaw_system_mass_exp (float): Defaults to 3.1571.
        yaw_system_mass_cost_coeff (float): Defaults to 9.0636 :math:`USD/kg`.
        hvac_mass_coeff (float): Not used in 2020. Defaults to 0.
        hvac_mass_cost_coeff (float): Defaults to 135.408 :math:`USD/kg`.
        hvac_mass (float): Defaults to 221 :math:`kg`.
        nacelle_cover_mass_coeff (float): Defaults to 1281.7 :math:`kg/kW`.
        nacelle_cover_mass_intercept (float): Defaults to 428.19.
        nacelle_cover_mass_cost_coeff (float): Defaults to 6.2244 :math:`USD/kg`.
        platform_mainframe_mass_coeff (float): Defaults to 0.005.
        platform_mainframe_mass_cost_coeff (float): Defaults to 18.6732 :math:`USD/kg`.
        platform_mainframe_mass (float):
            :math:`platform\_mainframe\_mass = platform\_mainframe\_mass\_coeff * bedplate\_mass`
        platform_mainframe_cost (float):

            ..math::
                platform\_mainframe\_cost = platform\_mainframe\_mass\_cost\_coeff
                * platform\_mainframe\_mass

        crane_mass_cost_coeff (float): Defaults to 4.368 :math:`USD/kg`.
        crane_mass (float): If not provided, defaults to :py:attr:`platform_mainframe_mass`.
    """

    turbine_class = base.turbine_class.reuse(default=1)
    blade_mass_coeff = base.blade_mass_coeff.reuse(default=9.2157)
    blade_mass_exp = create_field(float, "unitless", "input", default=1.7679)
    blade_mass_cost_coeff = base.blade_mass_cost_coeff.reuse(default=15.9432)
    hub_mass_coeff = base.hub_mass_coeff.reuse(default=3.5793)
    hub_mass_intercept = base.hub_mass_intercept.reuse(default=-25451.58)
    hub_mass_cost_coeff = base.hub_mass_cost_coeff.reuse(default=4.2588)
    pitch_bearing_mass_coeff = base.pitch_bearing_mass_coeff.reuse(default=0.1295)
    pitch_bearing_mass_intercept = base.pitch_bearing_mass_intercept.reuse(default=491.31)
    bearing_housing_fraction = base.bearing_housing_fraction.reuse(default=0.3280)
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
    gearbox_mass_exp = create_field(float, "unitless", "input", default=0.6566)
    gearbox_torque_cost = base.gearbox_torque_cost.reuse(default=14.0868)
    brake_mass_coeff = base.brake_mass_coeff.reuse(default=198.51)
    brake_mass_intercept = create_field(float, units="unitless", io_type="input", default=1.893)
    brake_mass_cost_coeff = base.brake_mass_cost_coeff.reuse(default=7.4256)
    hss_mass_coeff = base.hss_mass_coeff.reuse(default=0)
    hss_mass_cost_coeff = base.hss_mass_cost_coeff.reuse(default=0)
    high_speed_shaft_mass = base.hss_mass_cost_coeff.reuse(default=0)
    high_speed_shaft_cost = base.hss_mass_cost_coeff.reuse(default=0)
    generator_mass_coeff = base.generator_mass_coeff.reuse(default=1754)
    generator_mass_intercept = base.generator_mass_intercept.reuse(default=3503.6)
    generator_mass_cost_coeff = base.generator_mass_cost_coeff.reuse(default=13.5408)
    bedplate_mass_exp = base.bedplate_mass_exp.reuse(default=0)
    bedplate_mass_coeff = create_field(float, "unitless", "input", default=737.88)
    bedplate_mass_intercept = create_field(float, "unitless", "input", default=-68066)
    bedplate_mass_cost_coeff = base.bedplate_mass_cost_coeff.reuse(default=3.1668)
    yaw_system_non_bearing_mass_coeff = base.yaw_system_non_bearing_mass_coeff.reuse(default=1.6)
    yaw_system_mass_coeff = base.yaw_system_mass_coeff.reuse(default=0.0007)
    yaw_system_mass_exp = base.yaw_system_mass_exp.reuse(default=3.1571)
    yaw_system_mass_cost_coeff = base.yaw_system_mass_cost_coeff.reuse(default=9.0636)
    hvac_mass_coeff = base.hvac_mass_coeff.reuse(default=0)
    hvac_mass_cost_coeff = base.hvac_mass_cost_coeff.reuse(default=135.408)
    hvac_mass = base.hvac_mass_coeff.reuse(default=221)
    nacelle_cover_mass_coeff = base.nacelle_cover_mass_coeff.reuse(default=1281.7)
    nacelle_cover_mass_intercept = base.nacelle_cover_mass_intercept.reuse(default=428.19)
    nacelle_cover_mass_cost_coeff = base.nacelle_cover_mass_cost_coeff.reuse(default=6.2244)
    has_crane = base.has_crane.reuse(default=True)
    platform_mainframe_mass_coeff = base.platform_mainframe_mass_coeff.reuse(default=0.005)
    platform_mainframe_mass_cost_coeff = base.platform_mainframe_mass_cost_coeff.reuse(
        default=18.6732
    )
    crane_mass = base.crane_mass.reuse(default=3000)
    crane_mass_cost_coeff = create_field(float, "USD/kg", "input", default=4.368)
    # transformer_mass_coeff = base.transformer_mass_coeff.reuse(default=1.9150)
    # transformer_mass_intercept = base.transformer_mass_intercept.reuse(default=1910.0)
    # transformer_mass_cost_coeff = base.transformer_mass_cost_coeff.reuse(default=18.8)
    # tower_mass_coeff = base.tower_mass_coeff.reuse(default=19.828)
    # tower_mass_exp = base.tower_mass_exp.reuse(default=2.0282)
    # tower_mass_cost_coeff = base.tower_mass_cost_coeff.reuse(default=2.9)

    def __attrs_post_init__(self):
        """Updates the parameter mapping for new mass and cost relationships."""
        self.parameter_map["blade_mass"] = ("rotor_diameter", "blade_mass_coeff", "blade_mass_exp")
        self.parameter_map["low_speed_shaft_mass"] = (
            "rotor_diameter",
            "lss_mass_coeff1",
            "lss_mass_coeff2",
            "lss_mass_intercept",
        )
        self.parameter_map["gearbox_mass"] = (
            "rotor_torque",
            "gearbox_torque_density",
            "gearbox_mass_exp",
        )
        self.parameter_map["bedplate_mass"] = (
            "bedplate_mass_coeff",
            "rotor_diameter",
            "bedplate_mass_intercept",
        )
        self.parameter_map["hvac_mass"] = ("hvac_mass",)
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

        # Removes unmodeled high speed shaft
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

        .. math:: k * (torque * 1000) ** b

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

        self.gearbox_mass = (
            self.gearbox_torque_density * (self.rotor_torque * 1e3) ** self.gearbox_torque_exp
        )

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

    def calculate_hvac_mass(self):
        """Sets :py:attr:`hvac_mass` as provided by the user.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("hvac_mass")
        if not exists:
            raise ValueError("`hvac_mass` should be set by the user at initialization.")

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
        r"""Calculates and sets :py:attr:`platform_mainframe_mass` if it was not provided by the
        user.

        .. math::
            m_{platform\_mainframe}

        where:

        - :math:`m_{platform\_mainframe} =` :py:attr:`platform_mainframe_mass`

        Args:
            platform_mainframe_mass (float): Platform mainframe mass (:math:`kg`). See
                :py:meth:`calculate_platform_mainframe_mass` for details.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("crane_mass")
        if exists:
            return

        self.crane_mass = self.platform_mainframe_mass

    def calculate_crane_cost(self):
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
        exists = self._prepare_calculation("crane_cost")
        if exists:
            return

        self.crane_cost = self.crane_mass_cost_coeff * self.crane_mass
