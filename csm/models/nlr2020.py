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
        has_crane (bool): If True, apply :py:attr:`crane_mass` to
            :py:meth:`calculate_platform_mainframe_mass` and :py:attr:`crane_cost` to
            :py:meth:`calculate_platform_mainframe_cost`, otherwise ignore.
        crane_mass (bool): Mass of onboard crane, if :py:attr:`has_crane`, :math:`m_{crane}` from
            :py:meth:`calculate_platform_mainframe_mass`.
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
            :math:`blade\_mass\_coeff * (\frac{rotor\_diameter}{2}) ^ {blade\_mass\_exp}`
        blade_cost (float): :math:`{blade\_mass} * {blade\_mass\_cost\_coeff}`
        hub_mass_coeff (float): Defaults to 3.5793.
        hub_mass_intercept (float): Defaults to -25451.58.
        hub_mass_cost_coeff (float): Defaults to 4.2588.
        hub_mass (float): :math:`{hub\_mass\_coeff} * {blade\_mass} + {hub\_mass\_intercept}`.
        hub_cost (float): :math:`{hub\_mass} * {hub\_mass_cost\_coeff}`.
        pitch_bearing_mass_coeff (float): Not updated in 2015 or 2020. Defaults to 0.1295.
        pitch_bearing_mass_intercept (float): Not updated in 2015 or 2020. Defaults to 491.31 kg.
        bearing_housing_fraction (float): Not updated in 2015 or 2020. Defaults to 0.3280.
        mass_sys_offset (float): Not updated in 2015 or 2020. Defaults to 555.0 kg.
        pitch_system_mass_cost_coeff (float): Not updated in 2015 or 2020. Defaults to $22.1 USD/kg.
        pitch_system_mass (float):
            .. math::
                bearing\_mass = {pitch\_bearing\_mass\_coeff}*{blade\_mass}*{num\_blades}
                + {pitch\_bearing\_mass\_intercept} \\
                {pitch\_system\_mass} = (1+{bearing\_housing\_fraction})*{bearing\_mass}
                + {mass\_sys\_offset}

        pitch_system_cost (float): :math:`{pitch_system\_mass} * {pitch_system\_mass\_cost\_coeff}`
        spinner_mass_coeff (float): Defaults to 2.3255 :math:`kg/m^2`.
        spinner_mass_intercept (float): Defaults to 204.65 :math:`kg`.
        spinner_mass_cost_coeff (float): Defaults to 12.1212 :math:`USD/kg`.
        spinner_mass (float):
            :math:`spinner\_mass\_coeff * {rotor\_diameter} + {spinner\_mass\_intercept}`
        spinner_cost (float): :math:`{spinner\_mass} * {spinner\_mass\_cost\_coeff}`
        gearbox_torque_density (float): In 2024, modern 5-7MW gearboxes are able to reach 200 Nm/kg.
        gearbox_torque_cost (float): In 2024, modern 5-7MW gearboxes cost approximately $50/kNm.
        brake_mass_cost_coeff (float): In 2020, updated to $3.6254 USD/kg. Regression based sizing
            derived by J.Keller under FOA 1981 support project.
        hss_mass_coeff (float): High speed shaft is not modeled for 2020. Defaults to 0
        hss_mass_cost_coeff (float): High speed shaft is not modeled for 2020. Defaults to 0
        hvac_mass_coeff (float): Not updated in 2015, so is the original 0.08.
        hvac_mass_cost_coeff (float): Not updated in 2015, so is the original 124 USD/kg.
        platforms_mass_coeff (float): Not updated in 2015, so the original 0.125.
        crane_mass (float): Not updated in 2015, so the original 3000.
        platforms_mass_cost_coeff (float): Not updated in 2015, so the original 17.1.
        crane_cost (float): Not updated in 2015, so the original 12000.
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
    generator_mass_coeff = base.generator_mass_coeff.reuse(default=1754)
    generator_mass_intercept = base.generator_mass_intercept.reuse(default=3503.6)
    generator_mass_cost_coeff = base.generator_mass_cost_coeff.reuse(default=13.5408)
    # bedplate_mass_exp = base.bedplate_mass_exp.reuse(default=2.2)
    # bedplate_mass_cost_coeff = base.bedplate_mass_cost_coeff.reuse(default=2.9)
    # yaw_system_non_bearing_mass_coeff = base.yaw_system_non_bearing_mass_coeff.reuse(default=1.5)
    # yaw_system_mass_coeff = base.yaw_system_mass_coeff.reuse(default=0.0009)
    # yaw_system_mass_exp = base.yaw_system_mass_exp.reuse(default=3.314)
    # yaw_system_mass_cost_coeff = base.yaw_system_mass_cost_coeff.reuse(default=8.3)
    # hvac_mass_coeff = base.hvac_mass_coeff.reuse(default=0.08)
    # hvac_mass_cost_coeff = base.hvac_mass_cost_coeff.reuse(default=124)
    # nacelle_cover_mass_coeff = base.nacelle_cover_mass_coeff.reuse(default=1.2817)
    # nacelle_cover_mass_intercept = base.nacelle_cover_mass_intercept.reuse(default=428.19)
    # nacelle_cover_mass_cost_coeff = base.nacelle_cover_mass_cost_coeff.reuse(default=5.7)
    # platform_mainframe_mass_coeff = base.platform_mainframe_mass_coeff.reuse(default=0.125)
    # has_crane = base.has_crane.reuse(default=False)
    # crane_mass = base.crane_mass.reuse(default=3000)
    # platform_mainframe_mass_cost_coeff = base.platform_mainframe_mass_cost_coeff.reuse(default=17.1)  # noqa: E501
    # crane_cost = base.crane_cost.reuse(default=12000.0)
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
