import numpy as np

from csm.model.empirical_2020 import Empirical2020


class Empirical2030(Empirical2020):

    def blade_mass(rotor_diameter):
        return 18.45 * (rotor_diameter / 2.0) ** 1.59

    def hub_mass(blade_mass):
        return 3.46 * blade_mass - 25451.58

    def pitch_system_mass(num_blades, blade_mass):
        return (
            (0.11 * num_blades * blade_mass + 491.31)
            + (0.28 * (0.1295 * num_blades * blade_mass + 491.31))
            + 555.0
        )

    def nose_cone_mass(rotor_diameter):
        return 2.3255 * rotor_diameter + 204.65

    def low_speed_shaft_mass(rotor_diameter):
        return 2.1 * rotor_diameter**2 - 311.15 * rotor_diameter + 13108.0

    def main_bearing_mass(num_bearings, rotor_diameter):
        return num_bearings * 0.0001 * (rotor_diameter**3.4)

    def gearbox_mass(rotor_torque_max):
        return 300.0 * ((rotor_torque_max / 1000.0) ** 0.56)

    def braking_system_mass(turbine_rating_MW):
        return 198.51 * turbine_rating_MW + 1.893

    def generator_mass(turbine_rating_MW):
        return 0.85 * (1754.0 * turbine_rating_MW + 3503.6)

    def transformer_power_electronics_mass(turbine_rating_MW):
        return 1915.0 * turbine_rating_MW + 1910.0

    def yaw_system_mass(rotor_diameter):
        return 1.6 * (0.0007 * rotor_diameter**3.1571)

    def bedplate_mass(rotor_diameter):
        return 62373.0 * np.log(rotor_diameter) - 279192.0

    def railing_platform_mass(bedplate_mass):
        return 0.005 * bedplate_mass

    def crane_mass(railing_platform_mass):
        return railing_platform_mass

    def nacelle_cover_mass(turbine_rating_MW):
        return 1281.7 * turbine_rating_MW + 428.19

    def tower_mass(hub_height, swept_area):
        return 0.1 * hub_height * swept_area + 18560.0

    def blade_cost(blade_mass):
        return 0.85 * 15.9432 * blade_mass

    def hub_cost(hub_mass):
        return 0.85 * 4.2588 * hub_mass

    def pitch_system_cost(pitch_system_mass):
        return 0.85 * 24.1332 * pitch_system_mass

    def nose_cone_cost(nose_cone_mass):
        return 0.85 * 12.1212 * nose_cone_mass

    def low_speed_shaft_cost(low_speed_shaft_mass):
        return 0.85 * 12.9948 * low_speed_shaft_mass

    def main_bearing_cost(main_bearing_mass):
        return 0.85 * 4.914 * main_bearing_mass

    def gearbox_cost(gearbox_mass):
        return 0.85 * 14.0868 * gearbox_mass

    def braking_system_cost(braking_system_mass):
        return 0.85 * 7.4256 * braking_system_mass

    def generator_cost(generator_mass):
        return 0.85 * 13.5408 * generator_mass

    def transformer_power_electronics_cost(transformer_power_electronics_mass):
        return 0.85 * 20.5296 * transformer_power_electronics_mass

    def yaw_system_cost(yaw_system_mass):
        return 0.85 * 9.0636 * yaw_system_mass

    def bedplate_cost(bedplate_mass):
        return 0.85 * 3.1668 * bedplate_mass

    def railing_platform_cost(railing_platform_mass):
        return 0.85 * 18.6732 * railing_platform_mass

    def crane_cost(crane_mass):
        return 0.85 * 4.368 * crane_mass

    def hvac_cost(hvac_mass):
        return 0.85 * 135.408 * hvac_mass

    def nacelle_cover_cost(nacelle_cover_mass):
        return 0.85 * 6.2244 * nacelle_cover_mass

    def tower_cost(tower_mass):
        return 0.8 * 3.1668 * tower_mass

    def blade_transport_cost(num_blades, rotor_radius):
        return num_blades * np.where(
            rotor_radius < 70.0,
            (
                0.543 * rotor_radius**3
                - 7.4093 * rotor_radius**2
                - 2847.5 * rotor_radius
                + 103627
            ),
            (
                -0.0269 * rotor_radius**3
                + 39.953 * rotor_radius**2
                - 2947.9 * rotor_radius
                + 69268
            ),
        )
