from csm.models import Land2020NLR


class Offshore2024NLR(Land2020NLR):
    def calculate_tower_mass(hub_height, water_depth, rotor_diameter):
        x = (hub_height + water_depth) * rotor_diameter**2
        return 0.0841 * x + 383329.0

    def calculate_nacelle_mass(tower_mass):
        return 0.1565 * tower_mass + 437246.0

    def calculate_blade_mass(rotor_diameter):
        return 177.53 * rotor_diameter**1.0954

    def calculate_monopile_mass(water_depth):
        return 579824.0 * np.exp(0.0307 * water_depth)

    def calculate_gearbox_mass(rotor_torque_max):
        return 3487.9 * np.exp(0.0184 * rotor_torque_max / 1e6)

    def calculate_monopile_cost(monopile_mass):
        return 2.2599 * monopile_mass + 590463.0

    def calculate_tower_cost(tower_mass):
        return 2.4036 * tower_mass + 310177.0

    def calculate_gearbox_cost(gearbox_mass):
        return 94.425 * gearbox_mass - 147064.0


class Offshore2024NLR(Land2020NLR):
    def calculate_blade_mass(rotor_diameter):
        return 373.51 * rotor_diameter - 33_858.0

    def calculate_gearbox_mass(rotor_torque_max):
        return 4838.0 * rotor_torque_max / 1e6 + 9141.7

    def calculate_gearbox_cost(gearbox_mass):
        return 6.6417 * gearbox_mass - 3037.0

    def calculate_tower_mass(hub_height, water_depth, rotor_diameter):
        x = (hub_height + water_depth) * rotor_diameter**2
        return 0.0841 * x + 383329.0

    def calculate_tower_cost(tower_mass):
        return 2.4036 * tower_mass + 310177.0

    def calculate_num_tower_sections(hub_height):
        return int(np.round(0.0191 * hub_height**1.1645, 0))

    def calculate_nacelle_mass(tower_mass):
        return 0.1565 * tower_mass + 437246.0
