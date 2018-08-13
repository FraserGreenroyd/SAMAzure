# TODO - Update DF and Annual Radiance simulation parameters for detailed simulation
# TODO - Fix error at Adding zone1\annual\gridbased_annual\result/scene..default.ill and zone1\annual\gridbased_annual\result\sun..scene..default.ill to result files for zone1

# from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import json
import os
import sys

sys.path.insert(0, 'ladybug')
sys.path.insert(0, 'honeybee')

from honeybee.radiance.recipe.daylightfactor.gridbased import GridBased as GridBased_DaylightFactor
from honeybee.radiance.recipe.annual.gridbased import GridBased as GridBased_Annual
from honeybee.schedule import Schedule
from honeybee.futil import bat_to_sh


# ************************************************** #
# ***   Public methods                           *** #
# ************************************************** #

def load_json(path):
    """
    Load a JSON file into a dictionary object
    :type path: Path to JSON file
    :return: Dictionary representing content of JSON file
    """
    with open(path) as data_file:
        return json.load(data_file)

# ************************************************** #
# ***   Main execution                           *** #
# ************************************************** #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Radiance case from a Honeybee recipe generated using inputs")
    parser.add_argument("-p", "--analysisPoints", help="Path to the JSON analysis points to simulate")
    parser.add_argument("-sm", "--skyMatrix", help="Path to the sky matrix")
    parser.add_argument("-s", "--surfaces", help="Path to the context opaque and transparent surfaces")
    parser.add_argument("-o", "--outputSummary", help="Path to the target output directory for summary results")
    parser.add_argument("-q", "--quality", type=str,
                        help="Optional simulation quality ['low', 'medium', 'high']. Default is 'low'")
    args = parser.parse_args()

    analysis_grid_path = args.analysisPoints
    surfaces_path = args.surfaces
    sky_matrix_path = args.skyMatrix
    summary_results_path = args.outputSummary

    low_quality = "-aa 0.25 -dj 0.0 -ds 0.5 -dr 0 -ss 0.0 -dp 64 -ad 512 -st 0.85 -as 128 -dc 0.25 -dt 0.5 -ab 2 -lw 0.05 -lr 4 -ar 16"
    medium_quality = "-aa 0.2 -dj 0.5 -ds 0.25 -dr 1 -ss 0.7 -dp 256 -ad 2048 -st 0.5 -as 2048 -dc 0.5 -dt 0.25 -ab 3 -lw 0.01 -lr 6 -ar 64"
    high_quality = "-aa 0.1 -dj 1.0 -ds 0.05 -dr 3 -ss 1.0 -dp 512 -ad 4096 -st 0.15 -as 4096 -dc 0.75 -dt 0.15 -ab 6 -lw 0.005 -lr 8 -ar 128"

    # Modify the following to run a Radiance case with custom parameters
    custom_quality = "-aa 0.25 -dj 0.0 -ds 0.5 -dr 3 -ss 0.0 -dp 64 -ad 512 -st 0.85 -as 128 -dc 0.25 -dt 0.5 -ab 3 -lw 0.05 -lr 4 -ar 16"

    quality = high_quality if args.quality == "high" else medium_quality if args.quality == "medium" else custom_quality if args.quality == "custom" else low_quality

    sky_mtx = load_json(sky_matrix_path)
    print("\nSky matrix loaded from {0:}\n".format(sky_matrix_path))

    surfaces = load_json(surfaces_path)
    print("Context geometry loaded from {0:}\n".format(surfaces_path))

    analysis_grid = load_json(analysis_grid_path)
    zone_name = analysis_grid["analysis_grids"][0]["name"]
    print("Analysis grid for {0:} loaded from {1:}\n".format(zone_name, analysis_grid_path))

    annual_config = {"type": "gridbased", "id": "annual", "simulation_type": 0,
                     "rad_parameters": {"gridbased_parameters": quality}}
    df_config = {"type": "gridbased", "id": "daylight_factor", "rad_parameters": {"gridbased_parameters": quality}}

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

    # Obtain the x, y, z coordinates for the analysis points
    x, y, z = [list(elem) for elem in
               list(zip(*[i["location"] for i in df_recipe.results()[0].to_json()["analysis_points"]]))]
    print("Analysis point coordinates obtained")

    # Obtain the Daylight Factor values corresponding with the analysis points
    df = [i["values"][0][0].values()[0][0] for i in df_recipe.results()[0].to_json()["analysis_points"]]
    print("Daylight Factor results obtained")

    # Generate an occupancy schedule for the annual metrics calculation
    occupancy_schedule = Schedule.from_workday_hours(occ_hours=(8, 17), off_hours=(12, 13), weekend=(6, 7),
                                                     default_value=1)
    print("Annual occupancy schedule defined\n")

    # Obtain the annual metrics values corresponding with the analysis points
    da, cda, udi, udi_less, udi_more = annual_recipe.results()[0].annual_metrics(300, (100, 2000), None,
                                                                                 occupancy_schedule)
    print("Daylight autonomy metrics calculated\n")

    # Write the results to a single JSON file
    summary_results = {"name": zone_name, "x": x, "y": y, "z": z, "df": df, "da": da,
                       "cda": cda, "udi_less ": udi_less,
                       "udi": udi, "udi_more": udi_more}

    # Create a location for the results summary to be saved
    summary_loc = os.path.join(summary_results_path,
                               os.path.basename(analysis_grid_path).replace(".json", "_result.json"))

    # Write results to single summary file
    with open("{0:}".format(summary_loc), "w") as f:
        json.dump(summary_results, f)
    print("Results written to {0:}".format(summary_loc))

    # print(json.dumps(RESULTS, indent=4))
