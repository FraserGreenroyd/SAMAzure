# SAMAzure

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

<!-- 
    Adding Python to bash path
    export PATH="$PATH:/c/Users/tgerrish/AppData/Local/Continuum/anaconda3/envs/py27" 
-->
