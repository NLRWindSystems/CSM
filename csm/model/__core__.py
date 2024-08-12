import numpy as np

"""This file is intended to contain functions that apply to all cost and scaling models
For example, the relationship between rotor radius and rotor diameter is not model dependent
Import these functions into CSM models to avoid duplicating them
"""


def rotor_angular_velocity_max(tip_speed_max, rotor_radius):
    return tip_speed_max / rotor_radius


def rotor_angular_velocity_max_rpm(rotor_angular_velocity_max):
    return rotor_angular_velocity_max / (2.0 * np.pi) * 60.0


def rotor_torque_max(turbine_rating, rotor_efficiency_max, rotor_angular_velocity_max):
    return (turbine_rating / rotor_efficiency_max) / (rotor_angular_velocity_max)


def rotor_radius(rotor_diameter):
    return rotor_diameter / 2.0


def swept_area(rotor_radius):
    return np.pi * rotor_radius**2
