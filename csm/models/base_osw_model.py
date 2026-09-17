"""Minimal cost and scaling base model for offshore wind (OSW) turbines.

Deliberately much smaller than :py:class:`csm.models.base_model.CSMBase`: OSW's empirical and
benchmark data (see :py:mod:`csm.tools.experimental.build_custom_osw_model`) covers only four
top-level assemblies — Blade, Rotor, Tower, Nacelle — with no subcomponent breakdown (no Hub,
Pitch System, Gearbox, Generator, etc.), so there is nothing to decompose a turbine into the way
the land-based models do. Rotor already represents the complete rotor assembly (blades, hub, and
everything else that turns); Blade is a standalone diagnostic formula, not summed into anything.
Turbine mass/cost are the plain sum of Rotor + Nacelle + Tower.

Coefficients here are all placeholder defaults (1.0/0.0) — a real model comes from subclassing
this with fitted values, the way :py:mod:`csm.tools.experimental.build_custom_osw_model` generates
``csm/models/nlr2024_osw_fb.py`` and ``csm/models/nlr2024_osw_fl.py``. Do not use ``OSWBase``
directly.
"""

from attrs import define, validators

from csm.models.utils import create_field


@define
class OSWBase:
    """Offshore wind mass/cost scaling: Blade and Rotor as power laws in rotor diameter, Tower as
    a power law in hub height, Nacelle as linear in rated power — the same power-law/linear
    formula families :py:mod:`csm.models.nlr2026` uses throughout, just with each of these four
    assemblies fit directly against its own empirical rows instead of being built up from
    subcomponents. Cost is a plain per-kilogram rate against each assembly's own mass, fit
    separately per offshore type (fixed-bottom vs. floating) by the subclasses this generates.
    """

    # Inputs.
    rotor_diameter: float = create_field(
        float, "m", "input", additional_validators=[validators.gt(0)]
    )
    hub_height: float = create_field(float, "m", "input", additional_validators=[validators.gt(0)])
    rated_power_kw: float = create_field(
        float, "kW", "input", additional_validators=[validators.gt(0)]
    )

    # Mass coefficients — shared between fixed-bottom and floating (see module docstring).
    blade_mass_coeff: float = create_field(float, "unitless", "input", default=1.0)
    blade_mass_exp: float = create_field(float, "unitless", "input", default=1.0)
    rotor_mass_coeff: float = create_field(float, "unitless", "input", default=1.0)
    rotor_mass_exp: float = create_field(float, "unitless", "input", default=1.0)
    tower_mass_coeff: float = create_field(float, "unitless", "input", default=1.0)
    tower_mass_exp: float = create_field(float, "unitless", "input", default=1.0)
    nacelle_mass_coeff: float = create_field(float, "unitless", "input", default=1.0)
    nacelle_mass_intercept: float = create_field(float, "unitless", "input", default=0.0)

    # Cost coefficients — offshore-type specific; each subclass supplies its own fitted values.
    rotor_mass_cost_coeff: float = create_field(float, "USD/kg", "input", default=1.0)
    nacelle_mass_cost_coeff: float = create_field(float, "USD/kg", "input", default=1.0)
    tower_mass_cost_coeff: float = create_field(float, "USD/kg", "input", default=1.0)

    # Outputs.
    blade_mass: float = create_field(float, "kg", "both", additional_validators=[validators.ge(0)])
    rotor_mass: float = create_field(float, "kg", "both", additional_validators=[validators.ge(0)])
    tower_mass: float = create_field(float, "kg", "both", additional_validators=[validators.ge(0)])
    nacelle_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    rotor_cost: float = create_field(float, "USD", "both", additional_validators=[validators.ge(0)])
    nacelle_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )
    tower_cost: float = create_field(float, "USD", "both", additional_validators=[validators.ge(0)])
    turbine_mass: float = create_field(
        float, "kg", "both", additional_validators=[validators.ge(0)]
    )
    turbine_cost: float = create_field(
        float, "USD", "both", additional_validators=[validators.ge(0)]
    )

    def calculate_blade_mass(self):
        """Blade mass (kg): a power law in rotor radius, the same shape
        :py:attr:`csm.models.nlr2026.Land2026NLR.blade_mass_coeff` uses.
        """
        if self.blade_mass is not None:
            return
        self.blade_mass = self.blade_mass_coeff * (self.rotor_diameter / 2) ** self.blade_mass_exp

    def calculate_rotor_mass(self):
        """Rotor mass (kg): the complete rotor assembly (blades, hub, everything that turns),
        fit directly as a power law in rotor diameter rather than summed from subcomponents.
        """
        if self.rotor_mass is not None:
            return
        self.rotor_mass = self.rotor_mass_coeff * self.rotor_diameter**self.rotor_mass_exp

    def calculate_tower_mass(self):
        """Tower mass (kg): a power law in hub height."""
        if self.tower_mass is not None:
            return
        self.tower_mass = self.tower_mass_coeff * self.hub_height**self.tower_mass_exp

    def calculate_nacelle_mass(self):
        """Nacelle mass (kg): linear in rated power, the same shape
        :py:attr:`csm.models.nlr2026.Land2026NLR.generator_mass_coeff` uses.
        """
        if self.nacelle_mass is not None:
            return
        self.nacelle_mass = (
            self.nacelle_mass_coeff * self.rated_power_kw + self.nacelle_mass_intercept
        )

    def calculate_rotor_cost(self):
        """Rotor cost (USD): a fixed rate per kilogram of :py:attr:`rotor_mass`."""
        if self.rotor_cost is not None:
            return
        self.calculate_rotor_mass()
        self.rotor_cost = self.rotor_mass_cost_coeff * self.rotor_mass

    def calculate_nacelle_cost(self):
        """Nacelle cost (USD): a fixed rate per kilogram of :py:attr:`nacelle_mass`."""
        if self.nacelle_cost is not None:
            return
        self.calculate_nacelle_mass()
        self.nacelle_cost = self.nacelle_mass_cost_coeff * self.nacelle_mass

    def calculate_tower_cost(self):
        """Tower cost (USD): a fixed rate per kilogram of :py:attr:`tower_mass`."""
        if self.tower_cost is not None:
            return
        self.calculate_tower_mass()
        self.tower_cost = self.tower_mass_cost_coeff * self.tower_mass

    def calculate_turbine_mass(self):
        """Turbine mass (kg): Rotor + Nacelle + Tower (Blade is not included — it's already
        counted inside Rotor).
        """
        if self.turbine_mass is not None:
            return
        self.calculate_rotor_mass()
        self.calculate_nacelle_mass()
        self.calculate_tower_mass()
        self.turbine_mass = self.rotor_mass + self.nacelle_mass + self.tower_mass

    def calculate_turbine_cost(self):
        """Turbine cost (USD): Rotor + Nacelle + Tower cost."""
        if self.turbine_cost is not None:
            return
        self.calculate_rotor_cost()
        self.calculate_nacelle_cost()
        self.calculate_tower_cost()
        self.turbine_cost = self.rotor_cost + self.nacelle_cost + self.tower_cost

    def run(self):
        """Computes every mass and cost attribute not already provided by the caller."""
        self.calculate_blade_mass()
        self.calculate_rotor_mass()
        self.calculate_tower_mass()
        self.calculate_nacelle_mass()
        self.calculate_rotor_cost()
        self.calculate_nacelle_cost()
        self.calculate_tower_cost()
        self.calculate_turbine_mass()
        self.calculate_turbine_cost()
