import numpy as np

from csm.model.empirical_2024_offshore import Empirical2024Offshore


class Empirical2024Onshore(Empirical2024Offshore):

    def blade_mass(rotor_diameter):
        return 373.51 * rotor_diameter - 33_858.0

    def gearbox_cost(gearbox_mass):
        return 6.6417 * gearbox_mass - 3037.0

    def num_tower_sections(hub_height):
        return int(np.round(0.0191 * hub_height**1.1645, 0))

    def tower_base_diameter(hub_height):
        return 1.4365 * hub_height**0.2459

    def tower_top_base_diameter_ratio(tower_base_diameter):
        return -0.1471 * tower_base_diameter + 1.3901

    def gearbox_mass(rotor_torque_max):
        return 4838.0 * rotor_torque_max / 1e6 + 9141.7

    def gearbox_cost(gearbox_mass):
        return 6.6417 * gearbox_mass - 3037.0
