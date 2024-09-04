from csm.model.replicate_2015 import Replicate2015


class Replicate2015Excel(Replicate2015):

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
