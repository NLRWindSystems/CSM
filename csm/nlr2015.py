import attrs
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


# TODO: Determine if there is a way to use evolve and make_class together with a workaround
# NOTE: The below does not function while evolve and make_class remain incompatible

def generate_new_model(name: str, default_map: dict[str, Any]):
    field_map = {el: f for el in default_map if (f := getattr(base, el)) is not None}
    missing = set(default_map).difference(field_map)
    if missing:
        raise ValueError(f"Incompatible inputs provided: {', '.join(missing)}")
    cls = attrs.make_class(
        name,
        {k: field_map[k].evolve(default=val) for k, val in default_map.items()}
    )
    return cls