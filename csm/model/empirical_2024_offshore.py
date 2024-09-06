import numpy as np

from csm.model._base import CSMMixin


class Empirical2024Offshore(CSMMixin):

    def rotor_radius(rotor_diameter):
        return rotor_diameter / 2.0

    def rotor_angular_velocity_max(tip_speed_max, rotor_radius):
        return tip_speed_max / rotor_radius

    def rotor_angular_velocity_max_rpm(rotor_angular_velocity_max):
        return rotor_angular_velocity_max * 180.0 / np.pi

    def rotor_torque_max_MNm(
        turbine_rating_MW, rotor_efficiency_max, rotor_angular_velocity_max
    ):
        return (turbine_rating_MW / rotor_efficiency_max) / (rotor_angular_velocity_max)

    ##
    def gearbox_mass(is_direct_drive, rotor_torque_max_MNm):
        if is_direct_drive:
            return 0.0
        else:
            return 5149.8 * rotor_torque_max_MNm + 121.58

    def blade_mass(rotor_diameter):
        return 387.52 * rotor_diameter - 27755.0

    def gearbox_cost(is_direct_drive, gearbox_mass):
        if is_direct_drive:
            return 0.0
        else:
            # return 1.2902 * gearbox_mass - 42.127
            return 62.490 * gearbox_mass - 6922742.647
