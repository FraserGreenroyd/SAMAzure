# Run process

1.  Create Rhino model as surfaces. Generate individual zones from surfaces (including air-walls and glazing objects) using Honeybee and save to IDF somewhere.
2.  Using the FIRSTPYTHONSCRIPT, a weatherfile and config JSON, generate a ready-to-simulate IDF file. The command to run this is:
    -  ```python FIRSTPYTHONSCRIPT.py INPUT.idf WEATHERFILE.epw CONFIG.json OUTPUT.idf```
3.  Generate a set of files ready for simulation in Radiance from the IDF using the SECONDPYTHONSCRIPT. The command to run this is:
    -  ```python SECONDPYTHONSCRIPT.py INPUT.idf WEATHERFILE.epw CONFIG.json```
4.  