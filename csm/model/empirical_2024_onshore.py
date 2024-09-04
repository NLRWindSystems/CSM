from csm.model.empirical_2024_offshore import Empirical2024Offshore


class Empirical2024Onshore(Empirical2024Offshore):

    def gearbox_mass(is_direct_drive, rotor_torque_max_MNm):
        if is_direct_drive:
            return 0.0
        else:
            return 4838.0 * rotor_torque_max_MNm + 9141.7

    def blade_mass(rotor_diameter):
        return 373.51 * rotor_diameter - 33_858.0

    def gearbox_cost(is_direct_drive, gearbox_mass):
        if is_direct_drive:
            return 0.0
        else:
            return 6.6417 * gearbox_mass - 3037.0
