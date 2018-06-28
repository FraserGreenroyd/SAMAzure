"""
Description:
    Load an IDF file and modify according to settings in a config file
Arguments:
    path [string]: JSON config file (and referenced zone_conditions_library within that config file)
Returns:
    idf file [file object]: Modified IDF file

Annotations:
    TODO - Add exposed floor and roof materials
    TODO - Fix the glazing solar heat gain assignment from the config file for different orientations
"""

import json
import sys
from eppy.modeleditor import IDF
import platform


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

# Load the setup configuration for this IDF modification
# with open(sys.argv[1], "r") as f:
#     CONFIG = json.load(f)
with open("idf_config.json", "r") as f:
    CONFIG = json.load(f)

# Load IDF ready for pre-processing and modification
IDF_FILE = CONFIG["source_idf"]
if "win" in platform.platform().lower() and "dar" not in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_windows"])
elif "linux" in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_linux"])
elif "dar" in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_os"])

EPW_FILE = CONFIG["weather_file"]
idf = IDF(IDF_FILE)

# Load the JSON file containing internal gains, schedules and setpoints
ZONE_CONDITIONS = load_json(
    CONFIG["zone_conditions_library"]
)[CONFIG["zone_template"]]

# Load the EPW file to get the location variables and store in the IDF object
with open(EPW_FILE, "r") as f:
    A, B, C, D, E, F, G, H, I, J = f.readlines()[0].replace(
        "\n", ""
    ).split(",")
idf.idfobjects["SITE:LOCATION"] = []
idf.newidfobject(
    "SITE:LOCATION",
    Name=B,
    Latitude=float(G),
    Longitude=float(H),
    Time_Zone=float(I),
    Elevation=float(J)
)

# Set version number
idf.idfobjects["VERSION"] = []
idf.newidfobject(
    "VERSION",
    Version_Identifier="8.8.0"
)

# Remove Design Day sizing periods
idf.idfobjects["SIZINGPERIOD:DESIGNDAY"] = []

# Remove surface output (to save on simulation time and results size)
idf.idfobjects["OUTPUT:SURFACES:LIST"] = []

# Remove table style output to save on results file size
idf.idfobjects["OUTPUTCONTROL:TABLE:STYLE"] = []

# Set/remove sizing parameters
idf.idfobjects["SIZING:PARAMETERS"] = []

# Remove the HVAC objects provifing fresh air from outside
idf.idfobjects["DESIGNSPECIFICATION:OUTDOORAIR"] = []

# Set simulation to run only for annual period corresponding with weatherfile
idf.idfobjects["SIMULATIONCONTROL"] = []
idf.newidfobject(
    "SIMULATIONCONTROL",
    Do_Zone_Sizing_Calculation="No",
    Do_System_Sizing_Calculation="No",
    Do_Plant_Sizing_Calculation="No",
    Run_Simulation_for_Sizing_Periods="No",
    Run_Simulation_for_Weather_File_Run_Periods="Yes"
)

# Set simulation run period (including start day of year)
idf.idfobjects["RUNPERIOD"] = []
idf.newidfobject(
    "RUNPERIOD",
    Name="Custom Run",
    Begin_Month=1,
    Begin_Day_of_Month=1,
    End_Month=12,
    End_Day_of_Month=31,
    Day_of_Week_for_Start_Day="Monday",
    Use_Weather_File_Holidays_and_Special_Days="Yes",
    Use_Weather_File_Daylight_Saving_Period="Yes",
    Apply_Weekend_Holiday_Rule="No",
    Use_Weather_File_Rain_Indicators="Yes",
    Use_Weather_File_Snow_Indicators="Yes"
)

# Remove output variable dictionary
idf.idfobjects["OUTPUT:VARIABLEDICTIONARY"] = []

# Set general building parameters (including North angle)
idf.idfobjects["BUILDING"] = []
idf.newidfobject(
    "BUILDING",
    Name="IDF Name",
    North_Axis=0,
    Terrain="City",
    Solar_Distribution="FullExteriorWithReflections",
    Maximum_Number_of_Warmup_Days=25,
    Minimum_Number_of_Warmup_Days=6
)

# Set number of timesteps per hour in simulation
idf.idfobjects["TIMESTEP"] = []
idf.newidfobject(
    "TIMESTEP",
    Number_of_Timesteps_per_Hour=6
)

# Set shadow calculation method
idf.idfobjects["SHADOWCALCULATION"] = []
idf.newidfobject(
    "SHADOWCALCULATION",
    Calculation_Method="AverageOverDaysInFrequency",
    Calculation_Frequency=20,
    Maximum_Figures_in_Shadow_Overlap_Calculations=1000
)

# Set schedule type limits
idf.idfobjects["SCHEDULETYPELIMITS"] = []
idf.newidfobject(
    "SCHEDULETYPELIMITS",
    Name="FractionLimits",
    Lower_Limit_Value=0,
    Upper_Limit_Value=1,
    Numeric_Type="Continuous",
    Unit_Type="Dimensionless")

idf.newidfobject(
    "SCHEDULETYPELIMITS",
    Name="OnOffLimits",
    Lower_Limit_Value=0,
    Upper_Limit_Value=1,
    Numeric_Type="Discrete",
    Unit_Type="Dimensionless"
)

idf.newidfobject(
    "SCHEDULETYPELIMITS",
    Name="TemperatureSetpointLimits",
    Lower_Limit_Value=0,
    Upper_Limit_Value=100,
    Numeric_Type="Continuous",
    Unit_Type="Dimensionless"
)

idf.newidfobject(
    "SCHEDULETYPELIMITS",
    Name="ActivityLevelLimits",
    Lower_Limit_Value=0,
    Upper_Limit_Value=1000,
    Numeric_Type="Continuous",
    Unit_Type="Dimensionless"
)

# Set daily profiles from the internal gains TEMPlates
idf.idfobjects["SCHEDULE:DAY:INTERVAL"] = []
idf.idfobjects["SCHEDULE:DAY:HOURLY"] = []

# Set a daily Always On profile
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="AlwaysOnDay",
    Schedule_Type_Limits_Name="OnOffLimits"
)

for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = 1

# Set a daily Always Off profile
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="AlwaysOffDay",
    Schedule_Type_Limits_Name="OnOffLimits"
)

for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = 0

# Set daily cooling profile from JSON
setpoint = ZONE_CONDITIONS["cooling_setpoint"]
setback = ZONE_CONDITIONS["cooling_setback"]
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="CoolingSetpointDayWeekday",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = setpoint if ZONE_CONDITIONS[
        "cooling_setpoint_weekday"
    ]["Hour_{0:}".format(i + 1)] == 0 else setback
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="CoolingSetpointDayWeekend",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = setpoint if ZONE_CONDITIONS[
        "cooling_setpoint_weekend"
    ]["Hour_{0:}".format(i + 1)] == 0 else setback

# Set daily heating profile from JSON
setpoint = ZONE_CONDITIONS["heating_setpoint"]
setback = ZONE_CONDITIONS["heating_setback"]
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="HeatingSetpointDayWeekday",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = setpoint if ZONE_CONDITIONS[
        "heating_setpoint_weekday"
    ]["Hour_{0:}".format(i + 1)] == 0 else setback
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="HeatingSetpointDayWeekend",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = setpoint if ZONE_CONDITIONS[
        "heating_setpoint_weekend"
    ]["Hour_{0:}".format(i + 1)] == 0 else setback

# Set a daily Occupant profile
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="OccupantGainDayWeekday",
    Schedule_Type_Limits_Name="FractionLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "occupant_profile_weekday"
    ]["Hour_{0:}".format(i + 1)]
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="OccupantGainDayWeekend",
    Schedule_Type_Limits_Name="FractionLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "occupant_profile_weekend"
    ]["Hour_{0:}".format(i + 1)]

# Set a daily Lighting profile
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="LightingGainDayWeekday",
    Schedule_Type_Limits_Name="FractionLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "lighting_profile_weekday"
    ]["Hour_{0:}".format(i + 1)]
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="LightingGainDayWeekend",
    Schedule_Type_Limits_Name="FractionLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "lighting_profile_weekend"
    ]["Hour_{0:}".format(i + 1)]

# Set a daily Equipment profile
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="EquipmentGainDayWeekday",
    Schedule_Type_Limits_Name="FractionLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "equipment_profile_weekday"
    ]["Hour_{0:}".format(i + 1)]
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="EquipmentGainDayWeekend",
    Schedule_Type_Limits_Name="FractionLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "equipment_profile_weekend"
    ]["Hour_{0:}".format(i + 1)]

# Set a daily Ventilation profile
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="VentilationGainDayWeekday",
    Schedule_Type_Limits_Name="FractionLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "ventilation_profile_weekday"
    ]["Hour_{0:}".format(i + 1)]
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="VentilationGainDayWeekend",
    Schedule_Type_Limits_Name="FractionLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "ventilation_profile_weekend"
    ]["Hour_{0:}".format(i + 1)]

# Set a daily occupant activity level profile
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="OccupantActivityLevelDay",
    Schedule_Type_Limits_Name="ActivityLevelLimits")
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS[
        "occupant_sensible_gain_watts_per_person"
    ] + ZONE_CONDITIONS["occupant_latent_gain_watts_per_person"]

# Remove the current Weekly profiles and replace with compact weekly profiles
idf.idfobjects["SCHEDULE:WEEK:DAILY"] = []
idf.idfobjects["SCHEDULE:WEEK:COMPACT"] = []
idf.newidfobject(
    "SCHEDULE:WEEK:COMPACT",
    Name="OccupantGainWeek",
    DayType_List_1="WeekDays",
    ScheduleDay_Name_1="OccupantGainDayWeekday",
    DayType_List_2="AllOtherDays",
    ScheduleDay_Name_2="OccupantGainDayWeekend"
)

idf.newidfobject(
    "SCHEDULE:WEEK:COMPACT",
    Name="LightingGainWeek",
    DayType_List_1="WeekDays",
    ScheduleDay_Name_1="LightingGainDayWeekday",
    DayType_List_2="AllOtherDays",
    ScheduleDay_Name_2="LightingGainDayWeekend"
)

idf.newidfobject(
    "SCHEDULE:WEEK:COMPACT",
    Name="EquipmentGainWeek",
    DayType_List_1="WeekDays",
    ScheduleDay_Name_1="EquipmentGainDayWeekday",
    DayType_List_2="AllOtherDays",
    ScheduleDay_Name_2="EquipmentGainDayWeekend"
)

idf.newidfobject(
    "SCHEDULE:WEEK:COMPACT",
    Name="OccupantActivityLevelWeek",
    DayType_List_1="AllDays",
    ScheduleDay_Name_1="OccupantActivityLevelDay"
)

idf.newidfobject(
    "SCHEDULE:WEEK:COMPACT",
    Name="HeatingSetpointWeek",
    DayType_List_1="WeekDays",
    ScheduleDay_Name_1="HeatingSetpointDayWeekday",
    DayType_List_2="AllOtherDays",
    ScheduleDay_Name_2="HeatingSetpointDayWeekend"
)

idf.newidfobject(
    "SCHEDULE:WEEK:COMPACT",
    Name="CoolingSetpointWeek",
    DayType_List_1="WeekDays",
    ScheduleDay_Name_1="CoolingSetpointDayWeekday",
    DayType_List_2="AllOtherDays",
    ScheduleDay_Name_2="CoolingSetpointDayWeekend"
)

idf.newidfobject(
    "SCHEDULE:WEEK:COMPACT",
    Name="VentilationWeek",
    DayType_List_1="Weekdays",
    ScheduleDay_Name_1="VentilationGainDayWeekday",
    DayType_List_2="AllOtherDays",
    ScheduleDay_Name_2="VentilationGainDayWeekend"
)

idf.newidfobject(
    "SCHEDULE:WEEK:COMPACT",
    Name="AlwaysOnWeek",
    DayType_List_1="AllDays",
    ScheduleDay_Name_1="AlwaysOnDay")

# Set annual profiles
idf.idfobjects["SCHEDULE:YEAR"] = []
idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="OccupantGainYear",
    Schedule_Type_Limits_Name="FractionLimits",
    ScheduleWeek_Name_1="OccupantGainWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="LightingGainYear",
    Schedule_Type_Limits_Name="FractionLimits",
    ScheduleWeek_Name_1="LightingGainWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="EquipmentGainYear",
    Schedule_Type_Limits_Name="FractionLimits",
    ScheduleWeek_Name_1="EquipmentGainWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="OccupantActivityLevelYear",
    Schedule_Type_Limits_Name="ActivityLevelLimits",
    ScheduleWeek_Name_1="OccupantActivityLevelWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="HeatingSetpointYear",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits",
    ScheduleWeek_Name_1="HeatingSetpointWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="CoolingSetpointYear",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits",
    ScheduleWeek_Name_1="CoolingSetpointWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="VentilationYear",
    Schedule_Type_Limits_Name="OnOffLimits",
    ScheduleWeek_Name_1="VentilationWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="InfiltrationYear",
    Schedule_Type_Limits_Name="OnOffLimits",
    ScheduleWeek_Name_1="AlwaysOnWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

idf.newidfobject(
    "SCHEDULE:YEAR",
    Name="Always On",
    Schedule_Type_Limits_Name="OnOffLimits",
    ScheduleWeek_Name_1="AlwaysOnWeek",
    Start_Month_1=1,
    Start_Day_1=1,
    End_Month_1=12,
    End_Day_1=31
)

# Set heating and cooling setpoints from profile loaded in TEMPlate JSON
idf.idfobjects["HVACTEMPLATE:THERMOSTAT"] = []
[idf.newidfobject(
    "HVACTEMPLATE:THERMOSTAT",
    Name=j + "_HVAC",
    Heating_Setpoint_Schedule_Name="HeatingSetpointYear",
    Constant_Heating_Setpoint="",
    Cooling_Setpoint_Schedule_Name="CoolingSetpointYear",
    Constant_Cooling_Setpoint=""
) for j in [i.Name for i in idf.idfobjects["ZONE"]]]

# Set the people gains for all spaces
idf.idfobjects["PEOPLE"] = []
idf.newidfobject(
    "PEOPLE",
    Name="PeopleGain",
    Zone_or_ZoneList_Name="AllZones",
    Number_of_People_Schedule_Name="OccupantGainYear",
    Number_of_People_Calculation_Method="Area/Person",
    Zone_Floor_Area_per_Person=ZONE_CONDITIONS["occupant_gain_m2_per_person"],
    Fraction_Radiant=0.3,
    Sensible_Heat_Fraction=float(ZONE_CONDITIONS[
        "occupant_sensible_gain_watts_per_person"
    ]) / float(sum([ZONE_CONDITIONS[
        "occupant_sensible_gain_watts_per_person"
    ], ZONE_CONDITIONS[
        "occupant_latent_gain_watts_per_person"
    ]])
    ),
    Activity_Level_Schedule_Name="OccupantActivityLevelYear"
)

# Set the lighting gains for all spaces
idf.idfobjects["LIGHTS"] = []
idf.newidfobject(
    "LIGHTS",
    Name="LightingGain",
    Zone_or_ZoneList_Name="AllZones",
    Schedule_Name="LightingGainYear",
    Design_Level_Calculation_Method="Watts/Area",
    Watts_per_Zone_Floor_Area=ZONE_CONDITIONS["lighting_gain_watts_per_m2"],
    Fraction_Radiant=0.5,
    Fraction_Visible=0.5,
    Lighting_Level=ZONE_CONDITIONS["design_illuminance_lux"]
)

# Set the equipment gains for all spaces
idf.idfobjects["ELECTRICEQUIPMENT"] = []
idf.newidfobject(
    "ELECTRICEQUIPMENT",
    Name="EquipmentGain",
    Zone_or_ZoneList_Name="AllZones",
    Schedule_Name="EquipmentGainYear",
    Design_Level_Calculation_Method="Watts/Area",
    Watts_per_Zone_Floor_Area=ZONE_CONDITIONS["equipment_gain_watts_per_m2"],
    Fraction_Radiant=0.15,
    Fraction_Latent=0.85,
    Fraction_Lost=0
)

# Set infiltration rate for all zones
idf.idfobjects["ZONEINFILTRATION:DESIGNFLOWRATE"] = []
idf.newidfobject(
    "ZONEINFILTRATION:DESIGNFLOWRATE",
    Name="InfiltrationGain",
    Zone_or_ZoneList_Name="AllZones",
    Schedule_Name="InfiltrationYear",
    Design_Flow_Rate_Calculation_Method="Flow/Area",
    Flow_per_Zone_Floor_Area=ZONE_CONDITIONS["infiltration_m3_per_second_m2"]
)

# Set ventilation rate for all zones
# idf.idfobjects["ZONEVENTILATION:DESIGNFLOWRATE"] = []
# idf.newidfobject(
#     "ZONEVENTILATION:DESIGNFLOWRATE",
#     Name="VentilationGain",
#     Zone_or_ZoneList_Name="AllZones",
#     Schedule_Name="VentilationYear",
#     Design_Flow_Rate_Calculation_Method="Flow/Person",
#     Flow_Rate_per_Person=ZONE_CONDITIONS[
#         "ventilation_litres_per_second_per_person"
#     ] * 0.001
# )

# Set Ideal Loads Air System air supply based on internal TEMPlate
idf.idfobjects["HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM"] = []
for i in idf.idfobjects["ZONE"]:
    idf.newidfobject(
        "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
        Zone_Name=i.Name,
        Template_Thermostat_Name=j+"_HVAC",
        Maximum_Heating_Supply_Air_Temperature=50,
        Minimum_Cooling_Supply_Air_Temperature=13,
        Maximum_Heating_Supply_Air_Humidity_Ratio=0.0156,
        Minimum_Cooling_Supply_Air_Humidity_Ratio=0.0077,
        Heating_Limit="NoLimit",
        Cooling_Limit="NoLimit",
        Dehumidification_Control_Type="ConstantSensibleHeatRatio",
        Cooling_Sensible_Heat_Ratio=0.7,
        Dehumidification_Setpoint=60,
        Humidification_Control_Type="None",
        Humidification_Setpoint=30,
        Outdoor_Air_Method="Flow/Person",
        Outdoor_Air_Flow_Rate_per_Person=ZONE_CONDITIONS["ventilation_litres_per_second_per_person"]*0.001,
        Outdoor_Air_Economizer_Type="NoEconomizer",
        Heat_Recovery_Type="None",
        Sensible_Heat_Recovery_Effectiveness=0.7,
        Latent_Heat_Recovery_Effectiveness=0.65)

# Remove the existing window materials
idf.idfobjects["WINDOWMATERIAL:GLAZING"] = []
idf.idfobjects["WINDOWMATERIAL:GAS"] = []

# Remove the existing materials
idf.idfobjects["MATERIAL:AIRGAP"] = []
idf.idfobjects["MATERIAL"] = []

# Create single layer window material for glazing transmittance/g-value
idf.idfobjects["WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM"] = []

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR GLAZING MATERIAL_X",
    UFactor=CONFIG["glass_u_value"],
    Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_X"],
    Visible_Transmittance=CONFIG["glass_visible_transmittance_X"]
)

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR GLAZING MATERIAL_N",
    UFactor=CONFIG["glass_u_value"],
    Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_N"],
    Visible_Transmittance=CONFIG["glass_visible_transmittance_N"]
)

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR GLAZING MATERIAL_E",
    UFactor=CONFIG["glass_u_value"],
    Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_E"],
    Visible_Transmittance=CONFIG["glass_visible_transmittance_N"]
)

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR GLAZING MATERIAL_S",
    UFactor=CONFIG["glass_u_value"],
    Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_S"],
    Visible_Transmittance=CONFIG["glass_visible_transmittance_N"]
)

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR GLAZING MATERIAL_W",
    UFactor=CONFIG["glass_u_value"],
    Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_W"],
    Visible_Transmittance=CONFIG["glass_visible_transmittance_N"]
)

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="INTERIOR GLAZING MATERIAL",
    UFactor=0.8,
    Solar_Heat_Gain_Coefficient=0.9,
    Visible_Transmittance=0.9
)

# Create basic single layer materials with no mass for easy U-Value attribution
idf.idfobjects["MATERIAL:NOMASS"] = []
idf.newidfobject(
    "MATERIAL:NOMASS",
    Name="EXTERIOR WALL MATERIAL",
    Roughness="MediumRough",
    Thermal_Resistance=1 / CONFIG["exterior_wall_u_value"],
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1 - CONFIG["wall_reflectivity"]
)

idf.newidfobject(
    "MATERIAL:NOMASS",
    Name="INTERIOR WALL MATERIAL",
    Roughness="MediumSmooth",
    Thermal_Resistance=1 / 1.8,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1 - CONFIG["wall_reflectivity"]
)

idf.newidfobject(
    "MATERIAL:NOMASS",
    Name="INTERIOR FLOOR MATERIAL",
    Roughness="MediumSmooth",
    Thermal_Resistance=1 / 1.087,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1 - CONFIG["floor_reflectivity"]
)

idf.newidfobject(
    "MATERIAL:NOMASS",
    Name="INTERIOR CEILING MATERIAL",
    Roughness="MediumSmooth",
    Thermal_Resistance=1 / 1.087,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1 - CONFIG["ceiling_reflectivity"]
)

idf.newidfobject(
    "MATERIAL:NOMASS",
    Name="EXTERIOR ROOF MATERIAL",
    Roughness="MediumRough",
    Thermal_Resistance=1 / CONFIG["exterior_roof_u_value"],
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1 - CONFIG["ceiling_reflectivity"]
)

idf.newidfobject(
    "MATERIAL:NOMASS",
    Name="AIR WALL MATERIAL",
    Roughness="MediumRough",
    Thermal_Resistance=0.001,
    Thermal_Absorptance=0.001,
    Solar_Absorptance=0.001,
    Visible_Absorptance=0.001
)

idf.newidfobject(
    "MATERIAL",
    Name="THERMAL MASS MATERIAL",
    Roughness="MediumRough",
    Thickness=1,
    Conductivity=2,
    Density=2000,
    Specific_Heat=900,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=0.7
)

# Set the constructions for the whole building
idf.idfobjects["CONSTRUCTION"] = []
idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR WALL",
    Outside_Layer="EXTERIOR WALL MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR WALL",
    Outside_Layer="INTERIOR WALL MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR FLOOR",
    Outside_Layer="INTERIOR FLOOR MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR CEILING",
    Outside_Layer="INTERIOR CEILING MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR ROOF",
    Outside_Layer="EXTERIOR ROOF MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="AIR WALL",
    Outside_Layer="AIR WALL MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR WINDOW",
    Outside_Layer="EXTERIOR GLAZING MATERIAL_X"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR WINDOW",
    Outside_Layer="INTERIOR GLAZING MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="THERMAL MASS",
    Outside_Layer="THERMAL MASS MATERIAL"
)

# Get external surface areas for each zone and assign internal mass
ZONE_WALL_AREA = []
for zone in [str(i.Name) for i in idf.idfobjects["ZONE"]]:
    area = 0
    for surface in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        if (surface.Zone_Name == zone) & (str(surface.Sun_Exposure) == "SunExposed"):
            area += surface.area
    ZONE_WALL_AREA.append(area)

idf.idfobjects["INTERNALMASS"] = []
for i, j in list(zip([str(i.Name) for i in idf.idfobjects["ZONE"]], ZONE_WALL_AREA)):
    if j != 0:
        idf.newidfobject(
            "INTERNALMASS",
            Name=i + "_MASS",
            Construction_Name="THERMAL MASS",
            Zone_Name=i,
            Surface_Area=j
        )
    else:
        pass

# Create a list zones to be referenced for passing the internal gains setpoitns
TEMP = idf.newidfobject("ZONELIST", Name="AllZones")
for i, j in enumerate([str(i.Name) for i in idf.idfobjects["ZONE"]]):
    TEMP["Zone_{0:}_Name".format(i + 1)] = j

# Output variables to report during simulation
OUTPUT_VARIABLES = [
    "Zone Mean Air Temperature",
    "Zone Mean Radiant Temperature",
    "Zone Air Relative Humidity",
    "Zone Operative Temperature",
    "Zone People Total Heating Energy",
    "Zone Lights Electric Energy",
    "Zone Electric Equipment Electric Energy",
    "Zone Windows Total Transmitted Solar Radiation Energy",
    "Zone Air System Sensible Heating Energy",
    "Zone Air System Sensible Cooling Energy",
]

# Set the list of outputs to be generated fromt eh EnergyPLus simulation
idf.idfobjects["OUTPUT:VARIABLE"] = []
[
    idf.newidfobject(
        "OUTPUT:VARIABLE",
        Key_Value="*",
        Variable_Name=i,
        Reporting_Frequency="hourly"
    ) for i in OUTPUT_VARIABLES
]

# Diagnostics/testing
"""
The following section adds a bunch of diagnostics toools that can be used for checking how well the simulation has run
This includes:
    A list of potential output variables possible from the completed/failed simulation
    A list of the constructions in the completed/failed simulation - including U-values and thermal mass
    An SQLite format output result from the completed/failed simulation - this is probably better than using ReadVarsESO, but needs some further work]
    A detailed output diagnostics file indicatign any major issues in the completed/failed simulation
"""
# idf.idfobjects["OUTPUT:VARIABLEDICTIONARY"] = []
# idf.newidfobject("OUTPUT:VARIABLEDICTIONARY", Key_Field="regular")

# idf.idfobjects["OUTPUT:CONSTRUCTIONS"] = []
# idf.newidfobject("OUTPUT:CONSTRUCTIONS", Details_Type_1="Constructions")

# idf.idfobjects["OUTPUT:SQLITE"] = []
# idf.newidfobject("OUTPUT:SQLITE", Option_Type="Simple")

# idf.idfobjects["OUTPUT:DIAGNOSTICS"] = []
# idf.newidfobject("OUTPUT:DIAGNOSTICS", Key_1="DisplayExtraWarnings", Key_2="DisplayUnusedSchedules")

# Save the idf to a new file
idf.saveas(CONFIG["target_idf"])
