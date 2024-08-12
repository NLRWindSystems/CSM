from .__core__ import (
    rotor_angular_velocity_max,
    rotor_torque_max,
    rotor_radius,
)


def turbine_rating(turbine_rating_MW):
    return turbine_rating_MW * 1e6


def gearbox_mass(rotor_torque_max):
    return rotor_torque_max / 200.0


def gearbox_cost(turbine_rating_MW):
    return turbine_rating_MW * 79178.0


def tower_base_diameter(hub_height):
    return 0.057 * hub_height + 4.2396


def tower_top_diameter(tower_base_diameter):
    return 0.6 * tower_base_diameter
