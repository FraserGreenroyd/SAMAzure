"""
Description:
    Load an analysis grid, sky matrix and surfaces json, and prepare and run
    the radiance simulation for Daylight Factor and Daylight Autonomy.
    To run enter the command:
    python 02_RunRadianceJSON.py <path to analysis grid json> <path to surfaces JSON file> <path to sky matrix JSON file>
Arguments:
    path [string]: JSON config file (and referenced IDF within that config file)
Returns:
    Radiance simulation recipe/s [file objects]: Radiance simulation input/s
Annotations:
    TODO - Update DF and Annual Radiance simulation parameters for detailed simulation
    TODO - All results saved as JSON file
"""

import argparse
import json
import sys
sys.path.insert(0, 'ladybug')
sys.path.insert(0, 'honeybee')

from honeybee.radiance.recipe.daylightfactor.gridbased import GridBased as GridBased_DaylightFactor
from honeybee.radiance.recipe.annual.gridbased import GridBased as GridBased_Annual
from honeybee.schedule import Schedule
from honeybee.futil import bat_to_sh

##############################################
# Helper text to assist in running this file #
##############################################

parser = argparse.ArgumentParser(
    description='''Run a Radiance Daylight Factor and Annual simulation using Honeybee analysis grid, sky matrix and context geometry, outputting summary results to a user specified location.''',
    epilog="""Best of luck""")
parser.add_argument('analysis_grid.json', type=str, default=None, help='')
parser.add_argument('surfaces.json', type=str, default=None, help='')
parser.add_argument('sky_mtx.json', type=str, default=None, help='')
parser.add_argument('output_summary_results.json', type=str, default=None, help='')
args = parser.parse_args()

##########################################
# FREQUENTLY USED FUNCTIONS DEFINED HERE #
##########################################

def load_json(path):
    with open(path) as data_file:
        return json.load(data_file)

####################################################
# Gather arguments and paths to provided resources #
####################################################

analysis_grid_path = sys.argv[1]
surfaces_path = sys.argv[2]
sky_matrix_path = sys.argv[3]
summary_results_path = sys.argv[4]

################################
# Load the data from arguments #
################################

sky_mtx = load_json(sky_matrix_path)
print("\nSky matrix loaded from {0:}\n".format(sky_matrix_path))

surfaces = load_json(surfaces_path)
print("Context geometry loaded from {0:}\n".format(surfaces_path))

analysis_grid = load_json(analysis_grid_path)
zone_name = analysis_grid["analysis_grids"][0]["name"]
print("Analysis grid for {0:} loaded from {1:}\n".format(zone_name, analysis_grid_path))

##############################################
# Configure the simulation types and quality #
##############################################

low_quality = "-aa 0.25 -dj 0.0 -ds 0.5 -dr 1 -ss 0.0 -dp 64 -ad 512 -st 0.85 -as 128 -dc 0.25 -dt 0.5 -ab 2 -lw 0.05 -lr 4 -ar 16"
medium_quality = "-aa 0.2 -dj 0.5 -ds 0.25 -dr 1 -ss 0.7 -dp 256 -ad 2048 -st 0.5 -as 2048 -dc 0.5 -dt 0.25 -ab 3 -lw 0.01 -lr 6 -ar 64"
high_quality = "-aa 0.1 -dj 1.0 -ds 0.05 -dr 3 -ss 1.0 -dp 512 -ad 4096 -st 0.15 -as 4096 -dc 0.75 -dt 0.15 -ab 6 -lw 0.005 -lr 8 -ar 128"

annual_config = {
    "type": "gridbased", "id": "annual", "simulation_type": 0,
    "rad_parameters": {
        "gridbased_parameters": low_quality
    }
}

df_config = {
    "type": "gridbased", "id": "daylight_factor",
    "rad_parameters": {
        "gridbased_parameters": low_quality
    }
}

######################################
# Run the Daylight Factor simulation #
######################################

# Prepare Daylight Factor recipe from JSON origin string
df_recipe_json = {k: v for d in [df_config, analysis_grid, surfaces] for k, v in d.items()}
df_recipe = GridBased_DaylightFactor.from_json(df_recipe_json)
print("Daylight Factor recipe prepared\n")

df_bat_file = df_recipe.write(str(df_recipe.analysis_grids[0].name), "daylightfactor")
df_shell_file = bat_to_sh(df_bat_file)
print("Daylight Factor recipe converted to Radiance case\n")

# Run Daylight Factor simulation
if "win" in sys.platform.lower() and "dar" not in sys.platform.lower():
    df_recipe.run(df_bat_file, False)
else:
    df_recipe.run(df_shell_file, False)

##############################
#  Run the Annual simulation #
##############################

# Prepare Annual recipe from JSON origin string
annual_recipe_json = {k: v for d in [annual_config, analysis_grid, surfaces, sky_mtx] for k, v in d.items()}
annual_recipe = GridBased_Annual.from_json(annual_recipe_json)
print("Annual recipe prepared\n")

annual_bat_file = annual_recipe.write(str(annual_recipe.analysis_grids[0].name), "annual")
annual_shell_file = bat_to_sh(annual_bat_file)
print("Annual recipe converted to Radiance case\n")

# Run Annual simulation
if "win" in sys.platform.lower() and "dar" not in sys.platform.lower():
    annual_recipe.run(annual_bat_file, False)
else:
    annual_recipe.run(annual_shell_file, False)

##############################
# Simulation post processing #
##############################

# Obtain the x, y, z coordinates for the analysis points
x, y, z = [list(elem) for elem in list(zip(*[i["location"] for i in df_recipe.results()[0].to_json()["analysis_points"]]))]
print("Analysis point coordinates obtained")

# Obtain the Daylight Factor values corresponding with the analysis points
df = [i["values"][0][0].values()[0][0] for i in df_recipe.results()[0].to_json()["analysis_points"]]
print("Daylight Factor results obtained")

# Generate an occupancy schedule for the annual metrics calculation
occupancy_schedule = Schedule.from_workday_hours(occ_hours=(8, 17), off_hours=(12, 13), weekend=(6, 7), default_value=1)
print("Annual occupancy schedule defined\n")

# Obtain the annual metrics values corresponding with the analysis points
da, cda, udi, udi_less, udi_more = annual_recipe.results()[0].annual_metrics(300, (100, 2000), None, occupancy_schedule)
print("Daylight autonomy metrics calculated\n")

# Write the results to a single JSON file
summary_results = {"ZONE": zone_name, "X": x, "Y": y, "Z": z, "DF": df, "DA": da, "CDA": cda, "UDI_LESS": udi_less, "UDI": udi, "UDI_MORE": udi_more}

# Write results to single summary file
with open("{0:}".format(summary_results_path), "w") as f:
    json.dump(summary_results, f)
print("Results written to {0:}".format(summary_results_path))

# Print the results in the terminal
# print(json.dumps(RESULTS, indent=4))
