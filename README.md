# SAMAzure

This repository contains methods for generating EnergyPlus and Radiance simulations from source IDF files, and sending the resulting EnergyPlus and Radiance cases to Azure for simulation.

## Syntax for running EnergyPlus files from command line

## Syntax for running individual processes

### Reconfiguring IDF files

### Converting an IDF to a Radiance case

### Running a Radiance simulation from the generated case

<!--

1.  Create Rhino model as surfaces. Generate individual zones from surfaces (including air-walls and glazing objects) using Honeybee and save to IDF somewhere.
2.  Using the FIRSTPYTHONSCRIPT, a weatherfile and config JSON, generate a ready-to-simulate IDF file. The command to run this is:
    -  ```python FIRSTPYTHONSCRIPT.py INPUT.idf WEATHERFILE.epw CONFIG.json OUTPUT.idf```
3.  Generate a set of files ready for simulation in Radiance from the IDF using the SECONDPYTHONSCRIPT. The command to run this is:
    -  ```python SECONDPYTHONSCRIPT.py INPUT.idf WEATHERFILE.epw CONFIG.json```
4.  


## Running EnergyPlus from command line
Syntax for running Energyplus on IDF and EPW file is:
```
<Path to energyplus executable> -a -x -r -w <Path to EPW file> <Path to IDF file>
```

For example, the commands to run on Windows and MacOS are:
```
"C:\EnergyPlusV8-8-0\energyplus.exe" -a -x -r -w "GBR_Cardiff_CIBSE_TRY.epw" "test_modified.idf"
```
or 
```
"/Applications/EnergyPlus-8-8-0/energyplus-8.8.0" -a -x -r -w "GBR_Cardiff_CIBSE_TRY.epw" "test_basic_modified.idf"
```

    Adding Python to bash path
    export PATH="$PATH:/c/Users/tgerrish/AppData/Local/Continuum/anaconda3/envs/py27" 
-->
