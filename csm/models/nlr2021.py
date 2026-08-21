from attrs import define, fields

from csm.models import Land2020NLR
from csm.models.utils import create_field


base = fields(Land2020NLR)


@define
class Land2021NLR(Land2020NLR):
    # untouched
    # nacelle cover: k	1915	b	1910
    # platform mainframe: k	0.005
    # crane mass: no change

    blade_mass_coeff = base.blade_mass_coeff.reuse(default=8.3612)
    blade_mass_coeff2 = base.blade_mass_coeff.reuse(default=-620.03)
    blade_mass_intercept = create_field(float, "unitless", "input", default=17847)
    hub_mass_coeff = base.hub_mass_coeff.reuse(default=3.5793)
    hub_mass_exp = create_field(float, "unitless", "input", default=-25451.58)
    pitch_blade_mass_coeff = base.pitch_blade_mass_coeff.reuse(default=0)
    pitch_system_mass_coeff = base.pitch_system_mass_coeff.reuse(default=0)
    pitch_blade_mass_intercept = base.pitch_blade_mass_intercept.reuse(default=0)
    pitch_system_mass = base.pitch_system_mass.reuse(default=0)
    pitch_system_cost = base.pitch_system_cost.reuse(default=0)
    gearbox_torque_density = base.gearbox_torque_density.reuse(default=132.5)
    gearbox_torque_exp = base.gearbox_torque_exp.reuse(default=0)
    generator_mass_coeff = base.generator_mass_coeff.reuse(default=1.6731)
    generator_mass_intercept = base.generator_mass_intercept.reuse(default=3932.7)

    def __attrs_post_init__(self):
        """Updates the parameter mapping for new mass and cost relationships."""
        self.parameter_map["blade_mass"] = (
            "rotor_diameter",
            "blade_mass_coeff",
            "blade_mass_coeff2",
            "blade_mass_intercept",
        )
        self.parameter_map["pitch_system_mass"] = "pitch_system_mass"
        self.parameter_map["hub_mass"] = (
            "rated_power_kw",
            "hub_mass_coeff",
            "hub_mass_exp",
        )
        self.parameter_map["gearbox_mass"] = ("rotor_torque", "gearbox_mass_coeff")
        self.parameter_map["yaw_system_mass"] = (
            "rotor_diameter",
            "yaw_system_mass_coeff",
            "yaw_system_mass_coeff2",
            "yaw_system_mass_exp",
        )
        self.parameter_map["hydraulic_cooling_mass"] = ("hydraulic_cooling_mass",)
        self.parameter_map["tower_mass"] = (
            "rotor_diameter",
            "tower_length",
            "tower_mass_coeff",
            "tower_mass_coeff2",
            "tower_mass_intercept",
        )

    def calculate_blade_mass(self):
        """Calculates and sets :py:attr:`blade_mass` if it was not provided by the user.

        .. math:: k1 * radius^2 + k2 * radius + b

        where:

        - :math:`k1 =` :py:attr:`blade_mass_coeff`
        - :math:`k2 =` :py:attr:`blade_mass_coeff2`
        - :math:`radius =` :py:attr:`rotor_diameter` / 2
        - :math:`b =` :py:attr:`blade_mass_intercept`

        Args:
            blade_mass_coeff (float): :math:`k1` in the mass equation above.
            blade_mass_coeff2 (float): :math:`k2` in the mass equation above.
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
        # m = k*P^b
        # k	8104.7	b	1.1377
        """Calculates and sets :py:attr:`hub_mass` if it was not provided by the user.

        .. math:: k * power ^ b

        where:

        - :math:`k =` :py:attr:`hub_mass_coeff`
        - :math:`power =` :py:attr:`rated_power_kw`
        - :math:`b =` :py:attr:`hub_mass_exp`

        Args:
            hub_mass_coeff (float): :math:`k` in the mass equation above (:math:`kg/kW`).
            rated_power_kw (float): Turbine nameplate capacity (rated power) (:math:`kW`).
            hub_mass_exp (bool): :math:`b` in the mass equation above.

        Raises:
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        exists = self._prepare_calculation("hub_mass")
        if exists:
            return

        self.hub_mass = self.hub_mass_coeff * self.rated_power_kw**self.hub_mass_exp

    def calculate_gearbox_mass(self):
        """Calculates and sets :py:attr:`gearbox_mass` for the gearbox if it was not provided
        by the user.

        .. math:: torque * 1000 / k

        where:

        - :math:`torque =` :py:attr:`rotor_torque`
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

    def calculate_hydraulic_cooling_mass(self):
        # k	221
        exists = self._prepare_calculation("hydraulic_cooling_mass")
        if exists:
            return

    def calculate_tower_mass(self):
        # m = a*(hh*A)^2 + b*hh*A + c
        # hh = hub height, m A = swept area, m2
        # a	0.000000043	b	0.064588	c	48275
        exists = self._prepare_calculation("tower_mass")
        if exists:
            return
