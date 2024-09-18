import numpy as np

from csm.model._base import CSMMixin


class Empirical2024Offshore(CSMMixin):

    def rotor_angular_velocity_max(tip_speed_max, rotor_radius):
        return tip_speed_max / rotor_radius

    def rotor_torque_max(
        turbine_rating, rotor_efficiency_max, rotor_angular_velocity_max
    ):
        return (turbine_rating * 1e6 / rotor_efficiency_max) / (
            rotor_angular_velocity_max
        )

    def tower_mass(hub_height, water_depth, rotor_diameter):
        x = (hub_height + water_depth) * rotor_diameter**2
        return 0.0841 * x + 383329.0

    def nacelle_mass(tower_mass):
        return 0.1565 * tower_mass + 437246.0

    def blade_mass(rotor_diameter):
        return 177.53 * rotor_diameter**1.0954

    def monopile_mass(water_depth):
        return 579824.0 * np.exp(0.0307 * water_depth)

    def gearbox_mass(rotor_torque_max, is_direct_drive):
        if is_direct_drive:
            return 0.0
        else:
            return 3487.9 * np.exp(0.0184 * rotor_torque_max / 1e6)

    def gearbox_cost(gearbox_mass, is_direct_drive):
        if is_direct_drive:
            return 0.0
        else:
            return 94.425 * gearbox_mass - 147064.0
