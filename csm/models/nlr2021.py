from csm.models import Land2020NLR


class Land2021NLR(Land2020NLR):
    # untouched
    # spinner: k	2.3255	b	204.65
    # low speed shaft: a	2.1906	b	-311.15	c	13108
    # bearing: k	1.0E-04	b	3.5
    # brake: k	198.51	b	1.893
    # generator: k	1673.1	b	3932.7
    # bedplate: k	737.88	b	-68066
    # nacelle cover: k	1915	b	1910
    # platform mainframe: k	0.005
    # crane mass: no change

    def calculate_blade_mass(self):
        # m = a*(RD/2)^2 + b*(RD/2) + c
        # a	8.3612	b	-620.03	c	17847
        ...

    def calculate_hub_mass(self):
        # m = k*P^b
        # k	8104.7	b	1.1377
        ...

    def calculate_pitch_system_mass(self):
        # included in pitch system, don't individually calculate
        ...

    def calculate_gearbox_mass(self):
        # m = T/k	T = rotor torque, Nm
        # k	132.5
        ...

    def calculate_yaw_system_mass(self):
        # m = 1.6*k*RD^b
        # k	7.0E-04	b	3.1571
        ...

    def calculate_hydraulic_cooling_mass(self):
        # k	221
        ...

    def calculate_tower_mass(self):
        # m = a*(hh*A)^2 + b*hh*A + c
        # hh = hub height, m A = swept area, m2
        # a	0.000000043	b	0.064588	c	48275
        ...

    def calculate__mass(self):
        # f
        # m
        ...
