from csm.model._base import CSMMixin


class Replicate2015(CSMMixin):

    def rotor_torque_max(
        turbine_rating_kW, rotor_efficiency_max, rotor_angular_velocity_max
    ):
        return (turbine_rating_kW * 1000.0 / rotor_efficiency_max) / (
            rotor_angular_velocity_max
        )

    def nacelle_length():
        return 15.0

    def hub_system_mass(hub_mass, pitch_system_mass, spinner_mass):
        return hub_mass + pitch_system_mass + spinner_mass

    def rotor_mass(num_blades, blade_mass, hub_system_mass):
        return num_blades * blade_mass + hub_system_mass

    def nacelle_mass(
        low_speed_shaft_mass,
        num_bearings,
        bearing_mass,
        gearbox_mass,
        high_speed_shaft_mass,
        braking_system_mass,
        generator_mass,
        bedplate_mass,
        yaw_system_mass,
        hydraulic_cooling_mass,
        nacelle_cover_mass,
        platform_mainframe_mass,
        transformer_mass,
    ):
        return (
            low_speed_shaft_mass
            + num_bearings * bearing_mass
            + gearbox_mass
            + high_speed_shaft_mass
            + braking_system_mass
            + generator_mass
            + bedplate_mass
            + yaw_system_mass
            + hydraulic_cooling_mass
            + nacelle_cover_mass
            + platform_mainframe_mass
            + transformer_mass
        )

    def turbine_mass(rotor_mass, nacelle_mass, tower_mass):
        return rotor_mass + nacelle_mass + tower_mass

    def blade_mass(rotor_diameter, blade_has_carbon, turbine_class):
        if turbine_class == 1:
            if blade_has_carbon:
                b = 2.47
            else:
                b = 2.54
        else:
            if blade_has_carbon:
                b = 2.44
            else:
                b = 2.50
        return 0.5 * (rotor_diameter / 2.0) ** b

    def hub_mass(blade_mass):
        return 2.3 * blade_mass + 1320.0

    def pitch_system_mass(blade_mass, num_blades):
        pitch_bearing_mass = 0.1295 * blade_mass * num_blades + 491.31
        return 1.328 * pitch_bearing_mass + 555.0

    def spinner_mass(rotor_diameter):
        return 15.5 * rotor_diameter - 980.0

    def low_speed_shaft_mass(blade_mass, turbine_rating_kW):
        return 13.0 * (blade_mass * turbine_rating_kW * 1e-3) ** 0.65 + 775.0

    def bearing_mass(rotor_diameter):
        return 0.0001 * rotor_diameter**3.5

    def gearbox_mass(rotor_torque_max):
        return rotor_torque_max / 200.0

    def braking_system_mass(rotor_torque_max):
        return 0.00122 * rotor_torque_max

    def high_speed_shaft_mass(turbine_rating_kW):
        return 0.19894 * turbine_rating_kW

    def generator_mass(turbine_rating_kW):
        return 2.3 * turbine_rating_kW + 3400.0

    def bedplate_mass(rotor_diameter):
        return rotor_diameter**2.2

    def yaw_system_mass(rotor_diameter):
        return 1.5 * (0.0009 * rotor_diameter**3.314)

    def hydraulic_cooling_mass(turbine_rating_kW):
        return 0.08 * turbine_rating_kW

    def nacelle_cover_mass(turbine_rating_kW):
        return 1.2817 * turbine_rating_kW + 428.19

    def platform_mainframe_mass(bedplate_mass, onboard_crane_present):
        if onboard_crane_present:
            onboard_crane_mass = 3000.0
        else:
            onboard_crane_mass = 0.0
        return 0.125 * bedplate_mass + onboard_crane_mass

    def transformer_mass(turbine_rating_kW):
        return 1.9150 * turbine_rating_kW + 1910.0

    def tower_mass(hub_height):
        return 19.828 * hub_height**2.0282

    def gearbox_cost(gearbox_mass):
        return gearbox_mass * 12.9
