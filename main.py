from csm import CSM, run_config

if __name__ == "__main__":

    # Def get list of available CSM models
    print(CSM.get_available_models())

    # Create model from name
    model = CSM.from_name("Empirical2020")
    print(model)

    # Any values that could be used to calculate a parameter will work
    print(model.calculate("blade_cost", rotor_diameter=162))
    print(model.calculate("blade_cost", rotor_radius=81))

    # Function relationships only work one way.
    # We can calculate rotor radius in terms of rotor diameter
    # but we cannot do the opposite
    # model.calculate("rotor_diameter", rotor_radius=81)

    # Get all the required inputs to calculate every parameter in a model
    print(model.get_inputs())
    # Get all the outputs from a model
    print(model.get_outputs())

    # Display an equation for a parameter
    model.display_function("blade_cost")

    # What input parameters are required to calculate a certain output
    print(model.required_inputs_to_calculate("blade_cost"))
    print(model.required_inputs_to_calculate("tower_section_data"))

    # Both rotor diameter and blade mass can be used to calculate blade cost.
    # Since using blade mass requries less work, it will be used regardless of
    # the order of the kwargs
    print(model.calculate("blade_cost", rotor_diameter=162, blade_mass=20_000))
    print(model.calculate("blade_cost", blade_mass=20_000, rotor_diameter=162))

    # Sample data
    data = {
        "num_bearings": 2,
        "rotor_diameter": 162,
        "rotor_efficiency_max": 1,
        "tip_speed_max": 90,
        "turbine_rating_MW": 6.2,
        "num_blades": 3,
        "BOS_cost": 0,
        "hub_height": 150,
    }

    # Functions can return dataframes
    print(model.calculate("tower_section_data", data))

    # Calculate each output individually
    for p in model.get_outputs():
        print(f"{p:s} = {model.calculate(p, data)}")

    # Calculate all output parmeters in a more efficient way than looping over them
    # individually
    print(model.calculate_all(data))

    # Alternatively, we can read a parameter config file and run all possible
    # combinations of parameters
    result = run_config()
    print(result)
