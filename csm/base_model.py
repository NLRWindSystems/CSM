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
    rotor_diameter: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "m", "io": "input"})
    rotor_torque: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "kN*m", "io": "input"})
    rotor_mass: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "m", "io": "output"})

    # nacelle
    nacelle_length: float = field(default=0.0, validator=validators.instance_of(float), metadata={"units": "m", "io": "input"})

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


    def calculate_rotor_torque(self):
        if next(self._has_values("rotor_torque")):
            return
        
        parameters = ("turbine_rating", "rotor_efficiency_max", "rotor_angular_velocity_max")
        self._validate_inputs(parameters=parameters)
        
        self.rotor_torque = (
            (self.turbine_rating * 1e3 / self.rotor_efficiency_ma)
            / self.rotor_angular_velocity_max
        )

    def run():
        self.calculate_rotor_torque()

    def get_results():
        results = {
            "rotor_torque": self.rotor_torque,
        }