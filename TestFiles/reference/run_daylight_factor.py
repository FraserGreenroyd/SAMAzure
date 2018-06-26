from honeybee.radiance.recipe.daylightfactor.gridbased import GridBased
from honeybee.futil import bat_to_sh
import json
import re
import os

recipe_path = '/usr/honeybee-worker/recipe.json'
folder = "/usr/honeybee-worker/rad_files"
name = "daylightfactor"

with open(recipe_path) as json_data:
    recipe_json = json.load(json_data)

rec = GridBased.from_json(recipe_json)

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
results = [r.to_json() for r in rec.results()]
with open ('/usr/honeybee-worker/grid_results.json',"w") as results_file:
    results_file.write(json.dumps(results))
    results_file.close()

results_list = [point["values"][0][0][6324][0] for point in results[0]["analysis_points"]]

average_df =  float(sum(results_list) / len(results_list))

with open ('/usr/honeybee-worker/key_results.json',"w") as key_results:
    key_results.write(json.dumps({"average daylight factor": average_df}))

print "Post processing completed."
