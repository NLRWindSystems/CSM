from attrs import define, fields

from csm.models.utils import create_field
from csm.models.base_model import CSMBase


base = fields(CSMBase)


from csm.models import Land2020NLR


@define
class Land2021NLR(Land2020NLR):
    # untouched
    # spinner: k	2.3255	b	204.65
    # low speed shaft: a	2.1906	b	-311.15	c	13108
    # bearing: k	1.0E-04	b	3.5
    # brake: k	198.51	b	1.893
    # generator: k	1673.1	b	3932.7
    # bedplate: k	737.88	b	-68066
    # nacelle cover: k	1915	b	1910
    # platform mainframe: k	0.005
    # crane mass: no change

    blade_mass_coeff = base.blade_mass_coeff.reuse(default=8.3612)
    blade_mass_coeff2 = base.blade_mass_coeff.reuse(default=-620.03)
    blade_mass_intercept = create_field(float, "unitless", "input", default=17847)

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
        self.blade_mass = (
            self.blade_mass_coeff * self.rotor_radius**2
            + self.blade_mass_coeff2 * self.rotor_radius
            + self.blade_mass_intercept
        )

    def calculate_hub_mass(self):
        # m = k*P^b
        # k	8104.7	b	1.1377
        ...

    def calculate_pitch_system_mass(self):
        # included in pitch system, don't individually calculate
        ...

    def calculate_gearbox_mass(self):
        # m = T/k	T = rotor torque, Nm
        # k	132.5
        ...

    def calculate_yaw_system_mass(self):
        # m = 1.6*k*RD^b
        # k	7.0E-04	b	3.1571
        ...

    def calculate_hydraulic_cooling_mass(self):
        # k	221
        ...

    def calculate_tower_mass(self):
        # m = a*(hh*A)^2 + b*hh*A + c
        # hh = hub height, m A = swept area, m2
        # a	0.000000043	b	0.064588	c	48275
        ...
