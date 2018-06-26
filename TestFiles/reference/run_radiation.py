from honeybee.radiance.recipe.radiation.gridbased import GridBased
from honeybee.futil import bat_to_sh
import json
import re
import os

recipe_path = '/usr/honeybee-worker/recipe.json'
folder = "/usr/honeybee-worker/rad_files"
name = "radiation"

with open(recipe_path) as json_data:
    payload = json.load(json_data)#['payload']

rec = GridBased.from_json(payload)

# Generate bat file
bat = rec.write(folder, name)
# Convert bat to sh
sh = bat_to_sh(bat)

# Clean up shell script for -dr 3.0
with open(sh, "r") as shell_file:
    lines = shell_file.readlines()
    newlines = list()
    for line in lines:
        if "-dr" in line:
            line = re.sub("-dr (.*?) -", "-dr 3 -", line)
        newlines.append(line)
    shell_file.close()

with open(sh, "w") as new_shell:
    new_shell.writelines(newlines)
    new_shell.close()

print "start to run the subprocess"
if os.name == 'nt':
    success = rec.run(bat)
else:
    success = rec.run(sh)

print "Simulation completed."
print "Running post processing..."

grid = rec.results()[0]
grid.load_values_from_files()
json_grid = grid.to_json()
with open ('/usr/honeybee-worker/grid_results.json',"w") as results_file:
    results_file.write(json.dumps(json_grid))
    results_file.close()

key_results = {}

for key in json_grid["analysis_points"][0]["values"][0][0].keys():
    pit_grid = [point["values"][0][0][key][0] for point in json_grid["analysis_points"]]
    average_rad = float(sum(pit_grid)/len(pit_grid))
    key_results[str(key)] = average_rad

with open ('/usr/honeybee-worker/key_results.json',"w") as key_results_file:
    key_results_file.write(json.dumps({"average radiation": key_results}))

print "Post processing completed."
