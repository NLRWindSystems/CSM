from attrs import fields, define, field

from csm.base_model import CSMBase

base = fields(CSMBase)

@define
class Land2015NLR(CSMBase):
    rotor_efficiency_max: float = base.rotor_efficiency_max.evolve(default=1.0)
    blade_mass_coeff: float = base.blade_mass_coeff.evolve(default=0.5)
    blade_mass_cost_coeff: float = base.blade_mass_cost_coeff.evolve(default=14.6)
    hub_mass_coeff: float = base.hub_mass_coeff.evolve(default=2.3)
    hub_mass_intercept: float = base.hub_mass_intercept.evolve(default=1320.0)
    hub_mass_cost_coeff: float = base.hub_mass_cost_coeff.evolve(default=3.9)
