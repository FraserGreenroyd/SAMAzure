"""
Description:
    Load an analsyis grid, sky matrix and surfaces json, and prepare and run
    the radiance simulation for Daylight Factor and Daylight Autonomy.
    To run enter the command:
    python 02_RunRadianceJSON.py <path to analysis grid json> <path to surfaces JSON file> <path to sky matrix JSON file>
Arguments:
    path [string]: JSON config file (and referenced IDF within that config file)
Returns:
    Radiance simulation recipe/s [file objects]: Radiance simulation input/s

Annotations:
"""

# Load the necesasary packages
import json
import os
import sys
sys.path.insert(0, 'ladybug')
sys.path.insert(0, 'honeybee')
from honeybee.schedule import Schedule
from honeybee.radiance.recipe.daylightfactor.gridbased import GridBased as GridBasedDF
from honeybee.radiance.recipe.annual.gridbased import GridBased as GridBasedAnnual
from honeybee.futil import bat_to_sh


def load_json(path):
    """
    Description:
        Load a JSON file into a dictionary object
    Arguments:
        path [string]: The location of the JSON file being loaded
    Returns:
        dictionary [dict]: Dictionary containing contents of loaded JSON file
    """
    with open(path) as data_file:
        return json.load(data_file)

# Gather the paths to the provided resources
ANALYSIS_GRID_PATH = sys.argv[1]
SURFACES_PATH = sys.argv[2]
SKY_MTX_PATH = sys.argv[3]

# Load the data from the constituent parts
SKY_MTX = load_json(SKY_MTX_PATH)
print("\nSky matrix loaded from {0:}\n".format(SKY_MTX_PATH))

SURFACES = load_json(SURFACES_PATH)
print("Surfaces (context geometry) loaded from {0:}\n".format(SURFACES_PATH))

ANALYSIS_GRID = load_json(ANALYSIS_GRID_PATH)
ZONE_NAME = ANALYSIS_GRID["analysis_grids"][0]["name"]
print("Analysis grid for {0:} loaded from {1:}\n".format(ZONE_NAME, ANALYSIS_GRID_PATH))

# Define configurations for the Annual and DF simulations
ANNUAL_CONFIG = {
    "type": "gridbased",
    "id": "annual",
    "simulation_type": 0,
    "rad_parameters": {
        "gridbased_parameters":
        "-I -aa 0.25 -dj 0.0 -ds 0.5 -dr 3 -ss 0.0 -dp 64 -ad 5000 -st 0.85 -lw 2e-06 -as 128 -dc 0.25 -dt 0.5 -ab 3 -c 1 -lr 4 -ar 16"
    }
}

DF_CONFIG = {
    "rad_parameters": {
        "gridbased_parameters":
        "-aa 0.25 -dj 0.0 -ds 0.5 -ss 0.0 -dp 64 -ad 512 -st 0.85 -lw 0.05 -as 128 -dc 0.25 -dt 0.5 -ab 2 -lr 4 -dr 3 -ar 16"
    },
    "type": "gridbased",
    "id": "daylight_factor"
}

# Create recipes from JSON origin string
DF_RECIPE_JSON = {k: v for d in [DF_CONFIG, ANALYSIS_GRID, SURFACES] for k, v in d.items()}
ANNUAL_RECIPE_JSON = {k: v for d in [ANNUAL_CONFIG, ANALYSIS_GRID, SURFACES, SKY_MTX] for k, v in d.items()}

# Create Daylight Factor recipe from JSON origin string
DF_RECIPE = GridBasedDF.from_json(DF_RECIPE_JSON)
print("Daylight Factor recipe prepared\n")

# Generate Daylight Factor bat and sh files
DF_BAT_FILE = DF_RECIPE.write("HoneybeeRecipeJSONs", str(DF_RECIPE.analysis_grids[0].name))
DF_SHELL_FILE = bat_to_sh(DF_BAT_FILE)
print("Daylight Factor recipe converted to Radiance case\n")

# Run the Daylight Factor calculation
print("Running Daylight Factor simulation...\n")
if os.name == 'nt':
    DF_RECIPE.run(DF_BAT_FILE)
else:
    DF_RECIPE.run(DF_SHELL_FILE)
print("Daylight Factor simulation complete!\n")

# Get the X, Y, Z coordinates for the analysis points
X, Y, Z = list(zip(*[i["location"] for i in DF_RECIPE.results()[0].to_json()["analysis_points"]]))

# Get the Daylight Factor values corresponding with the analysis points
DF = [point["values"][0][0][6324][0] for point in DF_RECIPE.results()[0].to_json()["analysis_points"]]

################################################
################################################
# # THIS IS A TEMPORARY SECTION TO CHECK DF RESULTS
RESULTS = {
    "ZONE": ZONE_NAME,
    "X": X,
    "Y": Y,
    "Z": Z,
    "DF": DF
}
with open("{0:}/{1:}_results.json".format("HoneybeeRecipeJSONs", str(DF_RECIPE.analysis_grids[0].name)), "w") as f:
    json.dump(RESULTS, f)
print("Temporary results written to {0:}_results.json".format(os.path.abspath(str(DF_RECIPE.analysis_grids[0].name)+".json")))
################################################
################################################

# # Create Annual recipe from JSON origin string
# ANNUAL_RECIPE = GridBasedAnnual.from_json(ANNUAL_RECIPE_JSON)
# print("Annual recipe prepared\n")

# # Generate Annual bat and sh files
# ANNUAL_BAT_FILE = ANNUAL_RECIPE.write("HoneybeeRecipeJSONs", str(ANNUAL_RECIPE.analysis_grids[0].name))
# ANNUAL_SHELL_FILE = bat_to_sh(ANNUAL_BAT_FILE)
# print("Annual recipe converted to Radiance case\n")

# # Run the Daylight Factor calculation
# print("Running Annual simulation...\n")
# if os.name == 'nt':
#     ANNUAL_RECIPE.run(ANNUAL_BAT_FILE)
# else:
#     ANNUAL_RECIPE.run(ANNUAL_SHELL_FILE)
# print("Annual simulation complete!\n")

# # Generate an occupancy schedule for the annual metrics calculation
# OCCUPANCY_SCHEDULE = Schedule.from_workday_hours(occ_hours=(8, 17), off_hours=(12, 13), weekend=(6, 7), default_value=1)

# # Get the annual metrics from the annual simulation
# DA, CDA, UDI, UDI_LESS, UDI_MORE = ANNUAL_RECIPE.results()[0].annual_metrics(300, (100, 2000), None, OCCUPANCY_SCHEDULE)
# print("Daylight autonomy metrics calculated\n")

# # Write the results to a single JSON file
# RESULTS = {
#     "ZONE": ZONE_NAME,
#     "X": X,
#     "Y": Y,
#     "Z": Z,
#     "DF": DF,
#     "DA": DA,
#     "CDA": CDA,
#     "UDI_LESS": UDI_LESS,
#     "UDI": UDI,
#     "UDI_MORE": UDI_MORE,
# }

# # Write results to single summary file
# with open("{0:}_results.json".format(ZONE_NAME), "w") as f:
#     json.dump(RESULTS, f)
# print("Results written to {0:}_results.json".format(str(ANNUAL_RECIPE.analysis_grids[0].name)))
