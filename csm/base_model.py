"""Provides the ``CSMBase`` base model, which serves as the basis for all inputs and outputs
that subsequent subclasses will use.

New models should take the following form to implement
model-specific defaults while maintaining all input validation, metadata, and functionality from
the base model.

```python
from attrs import define, fields

from csm.base_model import CSMBase

base = fields(CSMBase)

@define
class CustomModel(CSMBase):
    rotor_efficiency_max: float = base.rotor_efficiency_max.evolve(default=1.0)
```
"""

import math
from typing import Any
from collections.abc import Generator

import pandas as pd
from attrs import field, define, fields, validators


@define
class CSMBase:
    """Base cost and scaling model that defines universally required inputs and calculations.

    Args:
        blade_mass_coeff (float): :math:`k` in the blade mass equation from
            :py:method:`calculate_blade_mass`.
        rotor_diameter (float): Diameter of the swept area of the turbine blades.
        turbine_class (int): Turbine classification; use 1 for IEC Wind-Class I, 2 fo
            IEC Wind-Class II or III.
        blade_has_carbon (bool): Use True if the blade has carbon, False if not.
        blade_mass_cost_coeff (float): Blade cost per kilogram (USD/kg).
        blade_mass (float): Blade mass (kg).
        hub_mass_coeff (float): :math:`k` in the hub mass equation from
            :py:method:`calculate_hub_mass`.
        hub_mass_intercept (bool): :math:`b` in the hub mass equation from
            :py:method:`calculate_hub_mass`.
        hub_mass_cost_coeff (float): Hub cost per kilogram (USD/kg).
        rotor_diameter (float): Turbine rotor diameter (:math:`m`).
        rated_power_kw (float): Turbine rated power (:math:`kW`).
        efficiency_max (float): Maximum possible drivetrain efficiency.
        max_tip_speed (float): Maximum allowable blade tip speed (:math:`m/s`).

    Attributes
    ----------
        blade_mass (float): Blade mass (:math:`kg`). See :py:method:`calculate_blade_mass`
            for details.
        hub_mass (float): Hub mass (kg). See :py:method:`calculate_hub_mass`
                for more details.
    """

    # turbine general
    turbine_class: int = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(int)),
        metadata={"units": "unitless", "io": "input"},
    )
    rated_power_kw: int = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(int)),
        metadata={"units": "W", "io": "input"},
    )

    # blades
    blade_has_carbon: bool = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(bool)),
        metadata={"units": "unitless", "io": "input"},
    )
    blade_mass_coeff: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "unitless", "io": "input"},
    )
    blade_mass_cost_coeff: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "USD/kg", "io": "input"},
    )
    blade_mass: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "kg", "io": "both"},
    )
    blade_cost: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "USD", "io": "both"},
    )

    # hub
    hub_mass_coeff: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "unitless", "io": "input"},
    )
    hub_mass_intercept: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "unitless", "io": "input"},
    )
    hub_mass_cost_coeff: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "USD/kg", "io": "input"},
    )
    hub_mass: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "kg", "io": "both"},
    )
    hub_cost: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "USD", "io": "both"},
    )

    # rotor
    rotor_diameter: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "m", "io": "input"},
    )
    efficiency_max: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "unitless", "io": "input"},
    )
    max_tip_speed: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "m/s", "io": "input"},
    )
    rated_rpm: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "rpm", "io": "both"},
    )
    rotor_torque: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "MN*m", "io": "both"},
    )
    rotor_mass: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "m", "io": "output"},
    )

    # nacelle
    nacelle_length: float = field(  # type: ignore
        default=None,
        validator=validators.optional(validators.instance_of(float)),
        metadata={"units": "m", "io": "both"},
    )

    # next
    # blade_mass: float = field(
    #     default=None,
    #     validator=validators.optional(validators.instance_of(float)),
    #     metadata={"units": "kg", "io": "both"},
    # )

    # NOTE: temporary while prototyping
    power_converter_cost: float = field(default=1000.0)
    nacelle_cost: float = field(default=1000.0)
    turbine_production_cost: float = field(default=1000.0)
    tower_flange_material_cost: float = field(default=1000.0)
    tower_flange_production_cost: float = field(default=1000.0)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Creates a new instance from a dictionary with simplified and intuitive error messages
        for extraneous and missing attributes.

        Args:
            data (dict): The data dictionary to be mapped.

        Returns
        -------
            cls: An instance of :py:class:`CSMBase` or one of its subclasses.
        """
        inputs = set(data)
        attributes = {el.name for el in cls.__attrs_attrs__ if el.init}
        required = {el.name for el in cls.__attrs_attrs__ if el.init and el.default is None}

        extra = inputs.difference(attributes)
        if len(extra):
            msg = (
                f"The initialization for {cls.__name__} was given extraneous "
                f"inputs: {', '.join(extra)}"
            )
            raise AttributeError(msg)

        missing = inputs.difference(required)
        if missing:
            msg = (
                f"The class definition for {cls.__name__} is missing the following inputs: "
                f"{missing}"
            )
            raise AttributeError(msg)
        return cls(**data)

    def _has_values(self, *args) -> Generator[bool]:
        """Checks if the user provided values for a given :py:attr:`arg` (True), or if they are
        model defaults (False).

        Yields
        ------
            Generator[bool]: Booleans indicating valid values have been implemented or provided
                by the user (True) or if the base class defaults are present (False).
        """
        for arg in args:
            default = getattr(fields(CSMBase), arg).default
            value = getattr(self, arg)
            yield value != default

    def _validate_inputs(self, parameters: tuple[str, ...]) -> None:
        """Validates if the required parameters to calculate an attribute's value have been
        populated by a subclass or provided by the user.

        Args:
            parameters (list[str]): List of class attributes to check for valid inputs.

        Raises
        ------
            ValueError: Raised if any of the required :py:attr:`parameters` have not been
            provided by the user or a subclass.
        """
        has_values = tuple(self._has_values(*parameters))
        if not all(has_values):
            missing = [
                name for exists, name in zip(has_values, parameters, strict=True) if not exists
            ]
            raise ValueError(f"Inputs for the following variables required: {', '.join(missing)}")

    def calculate_blade_mass(self):
        """Calculates and sets :py:attr:`blade_mass` if it was not provided by the user.

        .. math:: k * diameter^b

        where:

        - :math:`k =` :py:attr:`blade_mass_coeff`
        - :math:`diameter =` :py:attr:`rotor_diameter` / 2
        - :math:`b =`
          - 2.47 if :py:attr:`turbine_class` is 1 and :py:attr:`blade_has_carbon` is True
          - 2.54 if :py:attr:`turbine_class` is 1 and :py:attr:`blade_has_carbon` is False
          - 2.44 if :py:attr:`turbine_class` > 1 and :py:attr:`blade_has_carbon` is True
          - 2.5 if :py:attr:`turbine_class` > 1 and :py:attr:`blade_has_carbon` is False
          - 2.5 if :py:attr:`turbine_class` < 1

        Args:
            blade_mass_coeff (float): :math:`k` in the mass equation above.
            rotor_diameter (float): Diameter of the swept area of the turbine blades.
            turbine_class (int): Turbine classification; use 1 for IEC Wind-Class I, 2 fo
                IEC Wind-Class II or III.
            blade_has_carbon (bool): Use True if the blade has carbon, False if not.

        Raises
        ------
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("blade_mass")):
            return

        parameters = ("rotor_diameter", "turbine_class", "blade_has_carbon", "blade_mass_coeff")
        self._validate_inputs(parameters=parameters)

        match self.turbine_class:
            case 1:
                _exp = {"carbon": 2.47, "no_carbon": 2.54}
            case _ if self.turbine_class > 1:
                _exp = {"carbon": 2.44, "no_carbon": 2.5}
            case _:
                _exp = {"carbon": 2.5, "no_carbon": 2.5}
        exp = _exp["carbon" if self.blade_has_carbon else "no_carbon"]
        self.blade_mass = self.blade_mass_coeff * (self.rotor_diameter / 2) ** exp

    def calculate_blade_cost(self):
        """Calculates and sets :py:attr:`blade_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`blade_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`blade_mass`

        Args:
            blade_mass_cost_coeff (float): Blade cost per kilogram (USD/kg).
            blade_mass (float): Blade mass (kg).

        Raises
        ------
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("blade_cost")):
            return

        parameters = ("blade_mass", "blade_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

        self.blade_cost = self.blade_mass_cost_coeff * self.blade_mass

    def calculate_hub_mass(self):
        """Calculates and sets :py:attr:`hub_mass` if it was not provided by the user.

        .. math:: k * m_{blade} + b

        where:

        - :math:`k =` :py:attr:`hub_mass_coeff`
        - :math:`m_{blade} =` :py:attr:`blade_mass`
        - :math:`b =` :py:attr:`hub_mass_intercept`

        Args:
            hub_mass_coeff (float): :math:`k` in the mass equation above.
            blade_mass (float): Blade mass (:math:`kg`). See :py:method:`calculate_blade_mass`
                for details.
            hub_mass_intercept (bool): :math:`b` in the mass equation above.

        Raises
        ------
            ValueError: Raised if the required parameters have not been provided or calculated.
        """
        if next(self._has_values("hub_mass")):
            return

        parameters = ("blade_mass", "hub_mass_coeff", "hub_mass_intercept")
        self._validate_inputs(parameters=parameters)

        self.hub_mass = self.hub_mass_coeff * self.blade_mass + self.hub_mass_intercept

    def calculate_hub_cost(self):
        """Calculates and sets :py:attr:`hub_cost` if it was not provided by the user.

        .. math:: k * m

        where:

        - :math:`k =` :py:attr:`hub_mass_cost_coeff` (:math:`USD/kg`)
        - :math:`m =` :py:attr:`hub_mass` (:math:`kg`).

        Args:
            hub_mass_cost_coeff (float): Hub cost per kilogram (USD/kg).
            hub_mass (float): Hub mass (kg). See :py:method:`calculate_hub_mass`
                for more details.

        Raises
        ------
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if next(self._has_values("hub_cost")):
            return

        parameters = ("hub_mass", "hub_mass_cost_coeff")
        self._validate_inputs(parameters=parameters)

        self.hub_cost = self.hub_mass_cost_coeff * self.hub_mass

    def calculate_rotor_torque(self):
        """Calculates and sets :py:attr:`rated_rpm` and :py:attr:`rotor_torque` if they were not
        provided by the user.

        Args:
            rotor_diameter (float): Turbine rotor diameter (:math:`m`).
            rated_power_kw (float): Turbine rated power (:math:`kW`).
            efficiency_max (float): Maximum possible drivetrain efficiency.
            max_tip_speed (float): Maximum allowable blade tip speed (:math:`m/s`).

        Raises
        ------
            ValueError: Raised if any of the required parameters have not been provided.
        """
        if all(self._has_values("rated_rpm", "rotor_torque")):
            return

        parameters = ("rotor_diameter", "rated_power_kw", "efficiency_max", "max_tip_speed")
        self._validate_inputs(parameters=parameters)

        rated_hub_power = self.rated_power_kw / self.efficiency_max
        rotor_speed = self.max_tip_speed / (0.5 / self.rotor_diameter)
        self.rated_rpm = rotor_speed / (2.0 * math.pi) * 60.0
        self.rotor_torque = rated_hub_power / rotor_speed

    def run(self):
        """Run the mass and cost calculations."""
        # self.calculate_rotor_torque()
        self.calculate_blade_mass()
        self.calculate_hub_mass()

        self.calculate_blade_cost()
        self.calculate_hub_cost()

        self.calculate_rotor_torque()

    def get_results(self) -> dict[str, float]:
        """Gathers the core results."""
        results = {
            "rotor_torque": self.rotor_torque,
            "blade_mass": self.blade_mass,
            "blade_cost": self.blade_cost,
            "hub_mass": self.hub_mass,
            "hub_cost": self.hub_cost,
        }
        return results

    def get_mass_results(self) -> dict[str, float]:
        """Gathers all the mass-specific outputs into a dictionary of attribute: value."""
        results = {
            "blade_mass": self.blade_mass,
            "hub_mass": self.hub_mass,
        }
        return results

    def get_cost_results(self) -> dict[str, float]:
        """Gathers all the cost-specific outputs into a dictionary of attribute: value."""
        results = {
            "blade_cost": self.blade_cost,
            "hub_cost": self.hub_cost,
        }
        return results

    def irs_mpc_breakdown(
        self,
        turbine_production_cost: float,
        tower_flange_material_cost: float,
        tower_flange_production_cost: float,
        *,
        with_category: bool = False,
    ) -> pd.DataFrame:
        """Calculates the base cost breakdown for the United States IRS manufactured product
        component tables.

        Component mapping is as follows:

        - Wind turbine
          - Blades: model-calculated :py:attr:`blade_cost`. See :py:method:`calculate_blade_cost`
            for complete details.
          - Rotor Hub: model-calculated :py:attr:`hub_cost`. See :py:method:`calculate_hub_cost`
            for complete details.
          - Nacelle: model-calculated :py:attr:`nacelle_cost`.
            See :py:method:`calculate_nacelle_cost for complete details.
          - Power Converter: model-calculated :py:attr:`power_converter_cost`. See
            :py:method:`calculate_power_converter_cost` for complete details.
          - Production: user-provided :py:attr:`turbine_production_cost`
        - Wind Tower Flanges
          - Material: user-provided :py:attr:`tower_flange_material_cost`
          - Production: user-provided :py:attr:`tower_flange_production_cost`
        - Tower: not counted steel or iron product
        - Steel or iron productions in foundation: not counted steel or iron product

        Args:
            turbine_production_cost (float): Costs associated with production (i.e., not materials)
                of the wind turbine.
            tower_flange_material_cost (float): The materials cost for the tower flange.
            tower_flange_production_cost (float): The production cost for the tower flange.
            with_category (bool, optional: If True, return the DataFrame with the ``category``
                column intact, otherwise drop the column to produce an IRS-ready output. Defaults
                to False.

        Returns
        -------
            pd.DataFrame: Data Frame with indices for the APCs and MPCs, and columns for the
                mapping category (if :py:attr:`with_category`), "cost" (total USD), and "Value"
                (component cost / total cost * 100).
        """
        costs = {
            "blade": self.blade_cost,
            "hub": self.hub_cost,
            "nacelle": self.nacelle_cost,
            "power_converter": self.power_converter_cost,
            "turbine_production": turbine_production_cost,
            "tower_flange_material": tower_flange_material_cost,
            "tower_flange_production": tower_flange_production_cost,
        }
        apc_map = {
            "blade": "Wind Turbine",
            "hub": "Wind Turbine",
            "nacelle": "Wind Turbine",
            "power_converter": "Wind Turbine",
            "turbine_production": "Wind Turbine",
            "tower_flange_material": "Wind Tower Flange",
            "tower_flange_production": "Wind Tower Flange",
        }
        mpc_map = {
            "blade": "Blade",
            "hub": "Hub",
            "nacelle": "Nacelle",
            "power_converter": "Power Converter",
            "turbine_production": "Production",
            "tower_flange_material": "Material",
            "tower_flange_production": "Production",
        }
        breakdown = pd.DataFrame.from_dict(costs, orient="index", columns=["cost"])
        breakdown.index.name = "category"
        breakdown = breakdown.assign(
            Value=breakdown.cost / breakdown.cost.sum() * 100,
            APC=breakdown.index.str.replace(apc_map),
            MPC=breakdown.index.str.replace(mpc_map),
        )
        breakdown = breakdown.reset_index(drop=False).set_index(["APC", "MPC"])

        total = breakdown.sum().to_frame(name="Total").T.set_index(pd.Index(["-"]), append=True)
        total.index.names = ["APC", "MPC"]
        total.loc[("Total", "-"), "category"] = "-"

        empty = ["-", 0.0, 0.0]
        steel_ix = pd.MultiIndex.from_arrays(
            [["Tower", "Steel or iron products in foundation"], ["-", "-"]], names=("APC", "MPC")
        )
        steel = pd.DataFrame([empty, empty], columns=breakdown.columns, index=steel_ix)

        breakdown = pd.concat((breakdown, steel, total))
        if with_category:
            return breakdown
        return breakdown.replace(0, "-").drop(columns=["category"])

    def total_domestic_content(
        self,
        turbine_production_cost: float,
        tower_flange_material_cost: float,
        tower_flange_production_cost: float,
        domestic: list[str],
        *,
        return_table: bool = False,
    ) -> float | pd.DataFrame:
        """Calculates the total, valid domestic content production percentage based on the domestic
        or allowed-foreign entity produced components provided in :py:attr:`domestic` that align
        with :py:method:`irs_mpc_breakdown`.

        Note:
            MPC domestic content only counts towards the domestic content production percentage if
            all of the MPCs in an APC have been domestically produced. See IRS notices 2023-38 and
            2026-15 for complete details prior to calculation of the final proportion.

        Args:
            turbine_production_cost (float): Costs associated with production (i.e., not materials)
                of the wind turbine.
            tower_flange_material_cost (float): The materials cost for the tower flange.
            tower_flange_production_cost (float): The production cost for the tower flange.
            domestic (list[str]): List of the components aligning with the ``category`` column
                of :py:method:`irs_mpc_breakdown`.
            return_table (bool, optional): If True, return the DataFrame from
                :py:method:`irs_mpc_breakdown` with the additional column ``Domestic`` that shows
                the total domestic content percentage the counts for the IRS domestic content
                production calculation. Defaults to False.

        Returns
        -------
            float | pd.DataFrame: Returns the total valid domestic content as a percent, or the
                DataFrame breakdown by category.
        """
        breakdown = self.irs_mpc_breakdown(
            turbine_production_cost=turbine_production_cost,
            tower_flange_material_cost=tower_flange_material_cost,
            tower_flange_production_cost=tower_flange_production_cost,
            with_category=True,
        )
        domestic_map = dict.fromkeys(breakdown.category, 0)
        domestic_map |= dict.fromkeys(domestic, 1)
        breakdown = breakdown.assign(Domestic=breakdown.category.map(domestic_map))

        for apc in ("Wind Turbine", "Wind Tower Flange"):
            component = breakdown.loc[apc, "Domestic"]
            if component.size != component.sum():
                breakdown.loc[apc, "Domestic"] = 0.0

        breakdown.Domestic = breakdown.Domestic * (breakdown.Value / 100)
        breakdown.loc["Total", "Domestic"] = breakdown.Domestic.sum()
        breakdown.Domestic *= 100
        if return_table:
            return breakdown
        return breakdown.loc["Total", "Domestic"].squeeze()
