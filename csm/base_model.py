from typing import Generator
import attrs
from attrs import field, define, validators, fields


@define
class CSMBase:
    """Base cost and scaling model that defines universally required inputs and calculations."""

    # turbine general
    turbine_class: int = field(default=0, validator=validators.instance_of(int), metadata={"units": "unitless", "io": "input"})
    rated_power_kw: int = field(default=0, validator=validators.instance_of(int), metadata={"units": "W", "io": "input"})
    rotor_efficiency_max: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "unitless", "io": "input"})
    rotor_angular_velocity_max: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "unitless", "io": "input"})
    
    # blades
    blade_has_carbon: bool = field(default=False, validator=validators.instance_of(bool), metadata={"units": "unitless", "io": "input"})
    blade_mass_coeff: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "unitless", "io": "input"})
    blade_mass_cost_coeff: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "USD/kg", "io": "input"})
    blade_cost_external: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "USD", "io": "input"})
    blade_mass: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "kg", "io": "both"})
    blade_cost: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "USD", "io": "both"})
    
    # rotor
    rotor_diameter: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "m", "io": "input"})
    rotor_mass: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "m", "io": "output"})
    rotor_torque: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "kN*m", "io": "both"})

    # nacelle
    nacelle_length: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "m", "io": "both"})
    
    # next
    blade_mass: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "kg", "io": "both"})

    def _has_values(self, *args) -> Generator[bool, ...]:
        """Checks if the user provided values for a given :py:attr:`arg` (True), or if they are
        model defaults (False).

        Yields:
            Generator[bool, ...]: Booleans indicating valid values have been implemented or provided
                by the user (True) or if the base class defaults are present (False).
        """
        for arg in args:
            default = getattr(fields(CSMBase), arg).default
            value = getattr(self, arg)
            yield value != default

    def _validate_inputs(self, parameters: tuple[str]) -> None:
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
            missing = [name for exists, name in zip(has_values, parameters) if not exists]
            raise ValueError(f"Inputs for the following variables required: {', '.join(missing)}")

    def calculate_blade_mass(self):
        if next(self._has_values("blade_mass")):
            return

        parameters = ("rotor_diameter", "turbine_class", "blade_has_carbon", "blade_mass_coeff")
        self._validate_inputs(parameters=parameters)

        match self.turbine_class:
            case 1:
                _exp = {"carbon": 2.47, "no_carbon": 2.54}
            case _ if self.turbine_class > 1:
                _exp = {"carbon": 2.44, "no_carbon": 2.5}
            case _ :
                _exp = {"carbon": 2.5, "no_carbon": 2.5}
        exp = _exp["carbon" if self.blade_has_carbon else "no_carbon"]
        self.blade_mass = self.blade_mass_coeff * (self.rotor_diameter / 2) ** exp

    def calculate_blade_cost(self):
        if next(self._has_values("blade_cost")):
            return

        parameters = ("blade_mass", "blade_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

        self.blade_cost = self.blade_mass_cost_coeff * self.blade_mass


    def calculate_rotor_torque(self):
        if next(self._has_values("rotor_torque")):
            return
        
        parameters = ("rated_power_kw", "rotor_efficiency_max", "rotor_angular_velocity_max")
        self._validate_inputs(parameters=parameters)
        
        self.rotor_torque = (
            (self.rated_power_kw * 1e3 / self.rotor_efficiency_ma)
            / self.rotor_angular_velocity_max
        )

    def run(self):
        """Run the mass and cost calculations."""
        self.calculate_rotor_torque()
        self.calculate_blade_mass()

        self.calculate_blade_cost()

    def get_results(self) -> dict[str, float]:
        """Gathers the core results."""
        results = {
            "rotor_torque": self.rotor_torque,
            "blade_mass": self.blade_mass,
            "blade_cost": self.blade_cost,
        }
        return results
