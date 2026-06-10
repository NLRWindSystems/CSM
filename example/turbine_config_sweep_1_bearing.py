import pandas as pd
import numpy as np
from csm import CSM

# 1. Define the turbine technical configurations
turbines_specs = {
    "ATB T3 (3.3MW)": {
        "turbine_rating_MW": 3.3,
        "rotor_diameter": 148.0,
        "hub_height": 100.0, 
        "tip_speed_max": 90.0, ## limited by noise regulations, typically 85-90 m/s, use 90
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9, 
        "BOS_cost": 0.0
    },
    "ATB T1 (6.0MW)": {
        "turbine_rating_MW": 6.0,
        "rotor_diameter": 170.0,
        "hub_height": 115.0,
        "tip_speed_max": 90.0, ## limited by noise regulations, typically 85-90 m/s, use 90
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9, 
        "BOS_cost": 0.0
    },
    # https://www.siemensgamesa.com/global/en/home/products-and-services/onshore/wind-turbine-sg-4-4-164.html
    # https://en.wind-turbine-models.com/turbines/2758-siemens-gamesa-sg-5-2-165
    "SG 5.2-165": {
        "turbine_rating_MW": 5.2,
        "rotor_diameter": 165.0,
        "hub_height": 105.0, # specs says flexible, assuming 105m
        "tip_speed_max": 90.0, ## limited by noise regulations, typically 85-90 m/s, use 90
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9, 
        "BOS_cost": 0.0
    }, 
    # https://www.siemensgamesa.com/global/en/home/products-and-services/onshore/wind-turbine-sg-7-0-170.html
    # https://en.wind-turbine-models.com/turbines/2475-siemens-gamesa-sg-7-0-170
    "SG 7.0-170": {
        "turbine_rating_MW": 7.0,
        "rotor_diameter": 170.0,
        "hub_height": 135.0, # selected among 110.5, 115, 135, 155, 165, 185
        "tip_speed_max": 90.0, ## limited by noise regulations, typically 85-90 m/s, use 90
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0
    },
    # https://www.vestas.com/en/energy-solutions/onshore-wind-turbines/4-mw-platform/v150-4-5-mw
    # https://en.wind-turbine-models.com/turbines/2445-vestas-v150-4-5
    "V150-4.5": {
        "turbine_rating_MW": 4.5,
        "rotor_diameter": 150.0,
        "hub_height": 105.0, # selected among 90 and 105 m options
        "tip_speed_max": 82.0, ## shows up on wind-turbine-model specs
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0
    }
}

# 2. Instantiate cost models
models = {
    "Empirical2020": CSM.from_name("Empirical2020"),
    "Empirical2024Onshore": CSM.from_name("Empirical2024Onshore")
}

all_results = {}

# 3. Run full model configurations
for tx_name, inputs in turbines_specs.items():
    for model_name, model_obj in models.items():
        outputs = model_obj.calculate_all(**inputs)
        all_results[(tx_name, model_name)] = outputs

df_raw = pd.DataFrame(all_results)

# 4. Process the Prioritized Hybrid calculations per turbine configuration
final_columns = {}
turbines = list(turbines_specs.keys())

for tx in turbines:
    m2020 = df_raw[(tx, "Empirical2020")].copy()
    m2024 = df_raw[(tx, "Empirical2024Onshore")].copy()
    
    # Initialize the hybrid series
    hybrid = m2020.copy()
    
    # Direct prioritization: If 2024 is different from 2020 (meaning an onshore update exists)
    # and it is not a missing/NaN/offshore foundation value, prioritize it.
    for idx in hybrid.index:
        if idx not in ["monopile_mass", "monopile_cost", "water_depth"]:
            if pd.notna(m2024[idx]) and m2024[idx] != m2020[idx]:
                hybrid[idx] = m2024[idx]

    # --- PURE BOTTOM-UP RE-SUMMATION OF CATEGORY TOTALS ---
    # 1. Rotor Mass & Cost
    hybrid["rotor_mass"] = (hybrid["num_blades"] * hybrid["blade_mass"]) + hybrid["hub_mass"] + hybrid["pitch_system_mass"] + hybrid["nose_cone_mass"]
    hybrid["rotor_cost"] = (hybrid["num_blades"] * hybrid["blade_cost"]) + hybrid["hub_cost"] + hybrid["pitch_system_cost"] + hybrid["nose_cone_cost"]
    
    # 2. Nacelle Mass & Cost
    hybrid["nacelle_mass"] = (
        hybrid["low_speed_shaft_mass"] + hybrid["main_bearing_mass"] + hybrid["gearbox_mass"] +
        hybrid["braking_system_mass"] + hybrid["generator_mass"] + hybrid["bedplate_mass"] +
        hybrid["yaw_system_mass"] + hybrid["hvac_mass"] + hybrid["nacelle_cover_mass"] +
        hybrid["railing_platform_mass"] + hybrid["transformer_power_electronics_mass"] + hybrid["crane_mass"]
    )
    
    hybrid["nacelle_cost"] = (
        hybrid["low_speed_shaft_cost"] + hybrid["main_bearing_cost"] + hybrid["gearbox_cost"] +
        hybrid["braking_system_cost"] + hybrid["generator_cost"] + hybrid["transformer_power_electronics_cost"] +
        hybrid["yaw_system_cost"] + hybrid["bedplate_cost"] + hybrid["railing_platform_cost"] +
        hybrid["crane_cost"] + hybrid["hvac_cost"] + hybrid["nacelle_cover_cost"] +
        hybrid["controls_cost"] + hybrid["electrical_connection_cost"]
    )
    
    # 3. Turbine Mass & Cost
    hybrid["turbine_mass"] = hybrid["rotor_mass"] + hybrid["nacelle_mass"] + hybrid["tower_mass"]
    hybrid["turbine_cost"] = hybrid["rotor_cost"] + hybrid["nacelle_cost"] + hybrid["tower_cost"]
    
    # 4. Transport Cost
    hybrid["transport_cost"] = (
        hybrid["nacelle_drivetrain_transport_cost"] + hybrid["nacelle_power_electronics_cost"] +
        (hybrid["num_blades"] * hybrid["blade_transport_cost"]) + hybrid["tower_transport_cost"] +
        hybrid["hub_transport_cost"] + hybrid["parts_shipped_loose_cost"]
    )
    
    # 5. System Cost & Specific Cost Metrics
    hybrid["system_cost"] = hybrid["turbine_cost"] + hybrid["transport_cost"] + hybrid["BOS_cost"]
    hybrid["system_specific_cost_per_kW"] = hybrid["system_cost"] / (hybrid["turbine_rating_MW"] * 1e3)

    # Map variables back to columns
    final_columns[(tx, "Empirical2020")] = m2020
    final_columns[(tx, "Empirical2024Onshore")] = m2024
    final_columns[(tx, "Prioritized_Hybrid")] = hybrid

df_final_raw = pd.DataFrame(final_columns)

# 5. Define Hierarchical Presentation Mapping with Double Indents (4 spaces per level)
hierarchical_structure = [
    # --- GLOBAL SYSTEM COST BREAKDOWN ---
    ("system_cost", "SYSTEM COST"),
    ("BOS_cost", "    BOS_cost"),
    ("transport_cost", "    transport_cost"),
    ("nacelle_drivetrain_transport_cost", "        nacelle_drivetrain_transport_cost"),
    ("nacelle_power_electronics_cost", "        nacelle_power_electronics_cost"),
    ("blade_transport_cost", "        blade_transport_cost"),
    ("tower_transport_cost", "        tower_transport_cost"),
    ("hub_transport_cost", "        hub_transport_cost"),
    ("parts_shipped_loose_cost", "        parts_shipped_loose_cost"),
    ("turbine_cost", "    turbine_cost"),
    
    # --- TURBINE COST BREAKDOWN ---
    ("rotor_cost", "        rotor_cost"),
    ("blade_cost", "            blade_cost"),
    ("hub_cost", "            hub_cost"),
    ("pitch_system_cost", "            pitch_system_cost"),
    ("nose_cone_cost", "            nose_cone_cost"),
    ("nacelle_cost", "        nacelle_cost"),
    ("low_speed_shaft_cost", "            low_speed_shaft_cost"),
    ("main_bearing_cost", "            main_bearing_cost"),
    ("gearbox_cost", "            gearbox_cost"),
    ("braking_system_cost", "            braking_system_cost"),
    ("generator_cost", "            generator_cost"),
    ("transformer_power_electronics_cost", "            transformer_power_electronics_cost"),
    ("yaw_system_cost", "            yaw_system_cost"),
    ("bedplate_cost", "            bedplate_cost"),
    ("railing_platform_cost", "            railing_platform_cost"),
    ("crane_cost", "            crane_cost"),
    ("hvac_cost", "            hvac_cost"),
    ("nacelle_cover_cost", "            nacelle_cover_cost"),
    ("controls_cost", "            controls_cost"),
    ("electrical_connection_cost", "            electrical_connection_cost"),
    ("tower_cost", "        tower_cost"),
    
    # --- TURBINE MASS BREAKDOWN ---
    ("turbine_mass", "TURBINE MASS"),
    ("rotor_mass", "    rotor_mass"),
    ("blade_mass", "        blade_mass"),
    ("hub_mass", "        hub_mass"),
    ("pitch_system_mass", "        pitch_system_mass"),
    ("nose_cone_mass", "        nose_cone_mass"),
    ("nacelle_mass", "    nacelle_mass"),
    ("low_speed_shaft_mass", "        low_speed_shaft_mass"),
    ("main_bearing_mass", "        main_bearing_mass"),
    ("gearbox_mass", "        gearbox_mass"),
    ("braking_system_mass", "        braking_system_mass"),
    ("generator_mass", "        generator_mass"),
    ("transformer_power_electronics_mass", "        transformer_power_electronics_mass"),
    ("yaw_system_mass", "        yaw_system_mass"),
    ("bedplate_mass", "        bedplate_mass"),
    ("railing_platform_mass", "        railing_platform_mass"),
    ("crane_mass", "        crane_mass"),
    ("hvac_mass", "        hvac_mass"),
    ("nacelle_cover_mass", "        nacelle_cover_mass"),
    ("tower_mass", "    tower_mass"),
    
    # --- DIMENSIONS AND OTHER METRICS ---
    ("system_specific_cost_per_kW", "SPECIFIC METRICS / DIMENSIONS"),
    ("turbine_rating_MW", "    turbine_rating_MW"),
    ("rotor_diameter", "    rotor_diameter"),
    ("rotor_radius", "    rotor_radius"),
    ("hub_height", "    hub_height"),
    ("swept_area", "    swept_area"),
    ("rotor_angular_velocity_max", "    rotor_angular_velocity_max"),
    ("rotor_angular_velocity_max_rpm", "    rotor_angular_velocity_max_rpm"),
    ("rotor_torque_max", "    rotor_torque_max"),
    ("nacelle_length", "    nacelle_length"),
    ("nacelle_surface_area", "    nacelle_surface_area"),
    ("blade_surface_area", "    blade_surface_area"),
    ("hub_surface_area", "    hub_surface_area"),
    ("nacelle_lift_height", "    nacelle_lift_height"),
    ("num_tower_sections", "    num_tower_sections"),
    ("tower_base_diameter", "    tower_base_diameter"),
    ("tower_top_base_diameter_ratio", "    tower_top_base_diameter_ratio"),
]

# Ensure we map only indices available inside data arrays
valid_structure = [(raw, display) for raw, display in hierarchical_structure if raw in df_final_raw.index]
raw_indices = [item[0] for item in valid_structure]
display_names = [item[1] for item in valid_structure]

# Reindex and clean presentation labels
df_hierarchical = df_final_raw.reindex(raw_indices)
df_hierarchical.index = display_names
df_hierarchical.index.name = "Component / Parameter Hierarchy"

# Save execution matrix using UTF-8 BOM encoding for proper spreadsheet visualization
df_hierarchical.to_csv("turbine_config_csm_sweep_1_bearing.csv", encoding="utf-8-sig")

print("The updated hybrid data frame has been generated and written to 'turbine_config_csm_sweep_1_bearing.csv'")