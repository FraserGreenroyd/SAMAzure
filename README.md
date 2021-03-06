# Run process

-  Create Rhino model as surfaces. Generate individual zones from surfaces (including air-walls and glazing objects) using Honeybee and save to IDF somewhere.
-  Using ReconfigureIDF, a weatherfile and config JSON, generate a ready-to-simulate IDF file. The command to run this is `python ReconfigureIDF.py -i <input IDF file> -w <weather file> -t <internal gains template> -c <config file> -o <output IDF file>`. The usage of this command can be found by running `python ReconfigureIDF.py -h`.
-  Generate a set of files ready for simulation in Radiance from the IDF using IDFToHoneybeeRadiance. The command to run this is `python IDFToHoneybeeRadiance.py -i <input IDF file> -w <weather file> -c <config file> -o <output directory> -gs <analysis grid size>`. The usage of this command can be found by running `python IDFToHoneybeeRadiance.py -h`.
-  Run the Radiance case from the source files generated by the previous step (IDFToHoneybeeRadiance) using RunHoneybeeRadiance. The command to run this is `python run_HBradiance.py -p <analysis points file> -sm <sky matrix file> -s <surfaces file> -o <results output directory> -q <quality of simulation>`. The usage of this command can be found by running `python run_HBradiance.py -h`.

<!---
cd "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles"

CONFIGURE IDF
python ReconfigureIDF.py -i "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\4_zone_test.idf" -w "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\GBR_Cardiff_CIBSE_TRY.epw" -c "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\idf_config.json" -o "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\4_zone_test_mod.idf" -t "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\internal_gains_library.json"

RUN ENERGYPLUS
"C:\EnergyPlusV8-8-0\energyplus.exe" -a -r -x -w "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\GBR_Cardiff_CIBSE_TRY.epw" -d "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\epresults" "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\4_zone_test_mod.idf"

CONVERT IDF TO RADIANCE
python IDFToHoneybeeRadiance.py -i "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\4_zone_test_mod.idf" -w "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\GBR_Cardiff_CIBSE_TRY.epw" -c "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\idf_config.json" -o "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\radfiles" -gs 1.0

RUND RADIANCE
python RunHoneybeeRadiance.py -p "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\radfiles\AnalysisGrids\zone1.json" -sm "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\radfiles\sky_mtx.json" -s "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\radfiles\surfaces.json" -o "C:\Users\tgerrish\Documents\GitHub\SAMAzure\TestFiles\radfiles" -q low
-->
