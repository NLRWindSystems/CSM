from csm.model.empirical_2024_offshore import Empirical2024Offshore


class Empirical2024Onshore(Empirical2024Offshore):

    def gearbox_mass(rotor_torque_max_MNm):
        return 4838.0 * rotor_torque_max_MNm + 9141.7

    def blade_mass(rotor_diameter):
        return 373.51 * rotor_diameter - 33_858.0

    def gearbox_cost(gearbox_mass):
        return 6.6417 * gearbox_mass - 3037.0
