from .replicate_2015 import (
    rotor_angular_velocity_max,
    swept_area,
    rotor_radius,
    hub_mass,
    pitch_system_mass,
    spinner_mass,
    low_speed_shaft_mass,
    bearing_mass,
    rotor_torque_max,
    generator_mass,
    bedplate_mass,
    yaw_system_mass,
    hydraulic_cooling_mass,
    nacelle_cover_mass,
    platform_mainframe_mass,
    transformer_mass,
    tower_mass,
    hub_system_mass,
    rotor_mass,
    nacelle_mass,
    turbine_mass,
)


def blade_mass(rotor_diameter, blade_has_carbon, turbine_class):
    if turbine_class == 1:
        if blade_has_carbon:
            b = 2.47
        else:
            b = 2.56  # different to python version
    else:
        if blade_has_carbon:
            b = 2.44
        else:
            b = 2.50
    return 0.5 * (rotor_diameter / 2.0) ** b


def gearbox_mass(rotor_torque_max):
    return 113.0 * (rotor_torque_max / 1000.0) ** 0.71


def braking_system_mass(turbine_rating_kW):
    return 198.51 * turbine_rating_kW + 1.893


# spreadsheet doesn't have this
def high_speed_shaft_mass():
    return 0.0
