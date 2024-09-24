import numpy as np

from csm.model.empirical_2020 import Empirical2020


class Empirical2024Offshore(Empirical2020):

    def tower_mass(hub_height, water_depth, rotor_diameter):
        x = (hub_height + water_depth) * rotor_diameter**2
        return 0.0841 * x + 383329.0

    def nacelle_mass(tower_mass):
        return 0.1565 * tower_mass + 437246.0

    def blade_mass(rotor_diameter):
        return 177.53 * rotor_diameter**1.0954

    def monopile_mass(water_depth):
        return 579824.0 * np.exp(0.0307 * water_depth)

    def gearbox_mass(rotor_torque_max):
        return 3487.9 * np.exp(0.0184 * rotor_torque_max / 1e6)

    def monopile_cost(monopile_mass):
        return 2.2599 * monopile_mass + 590463.0

    def tower_cost(tower_mass):
        return 2.4036 * tower_mass + 310177.0

    def gearbox_cost(gearbox_mass):
        return 94.425 * gearbox_mass - 147064.0
