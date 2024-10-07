import numpy as np
import pandas as pd

from csm.model._base import CSMMixin


class Empirical2020(CSMMixin):

    def rotor_torque_max(
        turbine_rating_MW, rotor_efficiency_max, rotor_angular_velocity_max
    ):
        return (turbine_rating_MW * 1e6 / rotor_efficiency_max) / (
            rotor_angular_velocity_max
        )

    def blade_mass(rotor_radius):
        return 9.2157 * rotor_radius**1.7679

    def hub_mass(blade_mass):
        return 3.5793 * blade_mass - 25451.58

    def pitch_system_mass(num_blades, blade_mass):
        return 1.328 * (0.1295 * num_blades * blade_mass + 491.31) + 555.0

    def nose_cone_mass(rotor_diameter):
        return 2.3255 * rotor_diameter + 204.65

    def low_speed_shaft_mass(rotor_diameter):
        return 2.1906 * rotor_diameter**2 - 311.15 * rotor_diameter + 13108.0

    def main_bearing_mass(num_bearings, rotor_diameter):
        return num_bearings * 0.0001 * (rotor_diameter**3.5)

    def gearbox_mass(rotor_torque_max):
        return 156.46 * ((rotor_torque_max / 1000.0) ** 0.6566)

    def braking_system_mass(turbine_rating_MW):
        return 198.51 * turbine_rating_MW + 1.893

    def generator_mass(turbine_rating_MW):
        return 1754.0 * turbine_rating_MW + 3503.6

    def transformer_power_electronics_mass(turbine_rating_MW):
        return 1915.0 * turbine_rating_MW + 1910.0

    def yaw_system_mass(rotor_diameter):
        return 1.6 * (0.0007 * rotor_diameter**3.1571)

    def bedplate_mass(rotor_diameter):
        return 737.88 * rotor_diameter - 68066.0

    def railing_platform_mass(bedplate_mass):
        return 0.005 * bedplate_mass

    def crane_mass(railing_platform_mass):
        return railing_platform_mass

    def hvac_mass():
        return 221.0

    def nacelle_cover_mass(turbine_rating_MW):
        return 1281.7 * turbine_rating_MW + 428.19

    def nacelle_mass(
        low_speed_shaft_mass,
        main_bearing_mass,
        gearbox_mass,
        braking_system_mass,
        generator_mass,
        bedplate_mass,
        yaw_system_mass,
        hvac_mass,
        nacelle_cover_mass,
        railing_platform_mass,
        transformer_power_electronics_mass,
        crane_mass,
    ):
        return (
            low_speed_shaft_mass
            + main_bearing_mass
            + gearbox_mass
            + braking_system_mass
            + generator_mass
            + bedplate_mass
            + yaw_system_mass
            + hvac_mass
            + nacelle_cover_mass
            + railing_platform_mass
            + transformer_power_electronics_mass
            + crane_mass
        )

    def tower_mass(hub_height, swept_area):
        return 0.152 * hub_height * swept_area - 14281.0

    def rotor_mass(num_blades, blade_mass, hub_mass, pitch_system_mass, nose_cone_mass):
        return num_blades * blade_mass + hub_mass + pitch_system_mass + nose_cone_mass

    def turbine_mass(rotor_mass, nacelle_mass, tower_mass):
        return rotor_mass + nacelle_mass + tower_mass

    def nacelle_length(turbine_rating_MW):
        if turbine_rating_MW < 7.0:
            return -0.3038 * turbine_rating_MW**2 + 4.3685 * turbine_rating_MW - 0.7658
        else:
            return 15.0

    def nacelle_surface_area(nacelle_length):
        return nacelle_length * 4.5

    def hub_surface_area():
        return 16.0

    def blade_surface_area(rotor_radius):
        return (rotor_radius - 2.0) * 2.5

    def nacelle_lift_height(hub_height):
        return hub_height + 2.0

    def tower_section_data(tower_mass, hub_height, num_tower_sections) -> pd.DataFrame:
        # Assume all tower sections are of equal height
        section_height = hub_height / num_tower_sections

        # Ratio between the diameters of the top and bottom of the tower
        top_bottom_ratio = 0.6

        # Assume the diameter of the tower decreases linearly from the base to the hub and the mass of the sections decrease accordingly
        section_mass_relative = np.linspace(
            start=1.0, stop=top_bottom_ratio, num=num_tower_sections
        )
        section_mass_relative /= section_mass_relative.sum()

        section_number = np.arange(num_tower_sections) + 1

        return pd.DataFrame(
            data={
                "height": section_height,
                "mass": section_mass_relative * tower_mass,
                "surface_area": 4.3 * section_height,
            },
            index=pd.Index(section_number, name="tower_section_id"),
        )

    def blade_cost(blade_mass):
        return 15.9432 * blade_mass

    def hub_cost(hub_mass):
        return 4.2588 * hub_mass

    def pitch_system_cost(pitch_system_mass):
        return 24.1332 * pitch_system_mass

    def nose_cone_cost(nose_cone_mass):
        return 12.1212 * nose_cone_mass

    def rotor_cost(num_blades, blade_cost, hub_cost, pitch_system_cost, nose_cone_cost):
        return num_blades * blade_cost + hub_cost + pitch_system_cost + nose_cone_cost

    def low_speed_shaft_cost(low_speed_shaft_mass):
        return 12.9948 * low_speed_shaft_mass

    def main_bearing_cost(main_bearing_mass):
        return 4.914 * main_bearing_mass

    def gearbox_cost(gearbox_mass):
        return 14.0868 * gearbox_mass

    def braking_system_cost(braking_system_mass):
        return 7.4256 * braking_system_mass

    def generator_cost(generator_mass):
        return 13.5408 * generator_mass

    def transformer_power_electronics_cost(transformer_power_electronics_mass):
        return 20.5296 * transformer_power_electronics_mass

    def yaw_system_cost(yaw_system_mass):
        return 9.0636 * yaw_system_mass

    def bedplate_cost(bedplate_mass):
        return 3.1668 * bedplate_mass

    def railing_platform_cost(railing_platform_mass):
        return 18.6732 * railing_platform_mass

    def crane_cost(crane_mass):
        return 4.368 * crane_mass

    def hvac_cost(hvac_mass):
        return 135.408 * hvac_mass

    def nacelle_cover_cost(nacelle_cover_mass):
        return 6.2244 * nacelle_cover_mass

    def controls_cost(turbine_rating_MW):
        return 1092.0 * turbine_rating_MW * 21.15

    def electrical_connection_cost(turbine_rating_MW):
        return 1092.0 * turbine_rating_MW * 41.85

    def nacelle_cost(
        low_speed_shaft_cost,
        main_bearing_cost,
        gearbox_cost,
        braking_system_cost,
        generator_cost,
        transformer_power_electronics_cost,
        yaw_system_cost,
        bedplate_cost,
        railing_platform_cost,
        crane_cost,
        hvac_cost,
        nacelle_cover_cost,
        controls_cost,
        electrical_connection_cost,
    ):
        return (
            low_speed_shaft_cost
            + main_bearing_cost
            + gearbox_cost
            + braking_system_cost
            + generator_cost
            + transformer_power_electronics_cost
            + yaw_system_cost
            + bedplate_cost
            + railing_platform_cost
            + crane_cost
            + hvac_cost
            + nacelle_cover_cost
            + controls_cost
            + electrical_connection_cost
        )

    def tower_cost(tower_mass):
        return 3.1668 * tower_mass

    def turbine_cost(rotor_cost, nacelle_cost, tower_cost):
        return rotor_cost + nacelle_cost + tower_cost

    def nacelle_drivetrain_transport_cost(nacelle_mass):
        return np.ceil(nacelle_mass / 90000.0) * 45000.0

    def nacelle_power_electronics_cost(turbine_rating_MW):
        return np.maximum(turbine_rating_MW - 3.0, 0.0) * 9000.0

    def blade_transport_cost(rotor_radius):
        return (
            0.543 * rotor_radius**3
            - 7.4093 * rotor_radius**2
            - 2847.5 * rotor_radius
            + 103627.0
        )

    def num_tower_sections(tower_mass):
        return int(np.ceil(tower_mass / 80000.0))

    def tower_transport_cost(num_tower_sections):
        return 34083.0 * num_tower_sections

    def hub_transport_cost(hub_mass):
        return hub_mass + 5000.0

    def parts_shipped_loose_cost(turbine_mass):
        return turbine_mass * 0.025

    def transport_cost(
        nacelle_drivetrain_transport_cost,
        nacelle_power_electronics_cost,
        num_blades,
        blade_transport_cost,
        tower_transport_cost,
        hub_transport_cost,
        parts_shipped_loose_cost,
    ):
        return (
            nacelle_drivetrain_transport_cost
            + nacelle_power_electronics_cost
            + num_blades * blade_transport_cost
            + tower_transport_cost
            + hub_transport_cost
            + parts_shipped_loose_cost
        )

    def system_cost(
        turbine_cost,
        transport_cost,
        BOS_cost,
    ):
        return turbine_cost + transport_cost + BOS_cost

    def system_specific_cost_per_kW(
        system_cost,
        turbine_rating_MW,
    ):
        return system_cost / (turbine_rating_MW * 1e3)
