"""
Description:
    Load an IDF file and modify according to settings in a config file
    To run enter the command:
    python 00_ModifyIDF.py <path to IDF for modification> <path to config JSON file>
Arguments:
    path [string]: JSON config file (and referenced zone_conditions_library within that config file)
Returns:
    idf file [file object]: Modified IDF file

Annotations:
    TODO - Add exposed floor and roof materials
    TODO - Fix the glazing solar heat gain assignment from the config file for different orientations
    TODO - Add air supply as infiltration to the zones - using the zone area and people per area to define the air supply rate
    OR
    TODO - Add ventilation as ZONEVENTILATION:DESIGNFLOWRATE
    TODO - Remove the HVAC supply air in EnergyPlus
"""

import json
import sys
from eppy.modeleditor import IDF
import platform
from scipy import interpolate


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


IDF_FILEPATH = sys.argv[1]
CONFIG_FILEPATH = sys.argv[2]

# Load the setup configuration for this IDF modification
with open(CONFIG_FILEPATH, "r") as f:
    CONFIG = json.load(f)
print("\nConfig loaded from {0:}\n".format(CONFIG_FILEPATH))

# Load IDF ready for pre-processing and modification
IDF_FILE = sys.argv[1]
if "win" in platform.platform().lower() and "dar" not in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_windows"])
elif "linux" in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_linux"])
elif "dar" in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_os"])

EPW_FILE = CONFIG["weather_file"]
idf = IDF(IDF_FILE)

print("IDF loaded from {0:}\n".format(IDF_FILEPATH))
print("EPW loaded from {0:}\n".format(EPW_FILE))

# Load the JSON file containing internal gains, schedules and setpoints
ZONE_CONDITIONS = load_json(CONFIG["zone_conditions_library"])[CONFIG["zone_template"]]
print("Zone conditions set to {0:} and loaded from {1:}\n".format(CONFIG["zone_template"], CONFIG["zone_conditions_library"]))

# Load the EPW file to get the location variables and store in the IDF object
with open(EPW_FILE, "r") as f:
    A, B, C, D, E, F, G, H, I, J = f.readlines()[0].replace("\n", "").split(",")

idf.idfobjects["SITE:LOCATION"] = []
idf.newidfobject(
    "SITE:LOCATION",
    Name=B,
    Latitude=float(G),
    Longitude=float(H),
    Time_Zone=float(I),
    Elevation=float(J)
)
print("SITE:LOCATION modified")

# Set version number
idf.idfobjects["VERSION"] = []
idf.newidfobject(
    "VERSION",
    Version_Identifier="8.8.0"
)
print("VERSION modified")

# Remove Design Day sizing periods
idf.idfobjects["SIZINGPERIOD:DESIGNDAY"] = []
print("SIZINGPERIOD:DESIGNDAY removed")

# Remove surface output (to save on simulation time and results size)
idf.idfobjects["OUTPUT:SURFACES:LIST"] = []
print("OUTPUT:SURFACES:LIST removed")

# Remove table style output to save on results file size
idf.idfobjects["OUTPUTCONTROL:TABLE:STYLE"] = []
print("OUTPUTCONTROL:TABLE:STYLE removed")

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
print("SIMULATIONCONTROL modified")

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
print("RUNPERIOD modified")

# Remove output variable dictionary
idf.idfobjects["OUTPUT:VARIABLEDICTIONARY"] = []
print("OUTPUT:VARIABLEDICTIONARY removed")

# Set general building parameters (including North angle)
idf.idfobjects["BUILDING"] = []
idf.newidfobject(
    "BUILDING",
    Name="IDF Name",
    North_Axis=0,
    Terrain="City",
    Solar_Distribution="FullInteriorAndExteriorWithReflections",
    Maximum_Number_of_Warmup_Days=25,
    Minimum_Number_of_Warmup_Days=6
)
print("BUILDING modified")

# Set number of timesteps per hour in simulation
idf.idfobjects["TIMESTEP"] = []
idf.newidfobject(
    "TIMESTEP",
    Number_of_Timesteps_per_Hour=6
)
print("TIMESTEP modified")

# Set shadow calculation method
idf.idfobjects["SHADOWCALCULATION"] = []
idf.newidfobject(
    "SHADOWCALCULATION",
    Calculation_Method="AverageOverDaysInFrequency",
    Calculation_Frequency=20,
    Maximum_Figures_in_Shadow_Overlap_Calculations=15000,
    Polygon_Clipping_Algorithm="SutherlandHodgman",
    Sky_Diffuse_Modeling_Algorithm="SimpleSkyDiffuseModeling",
    External_Shading_Calculation_Method="InternalCalculation",
    Output_External_Shading_Calculation_Results="No"  # NOTE - Remove this for final version - this is used for testing export to TAS
)
print("SHADOWCALCULATION modified")

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
print("SCHEDULETYPELIMITS modified")

# Set daily profiles from the internal gains TEMPlates
idf.idfobjects["SCHEDULE:DAY:INTERVAL"] = []
print("SCHEDULE:DAY:INTERVAL removed")

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
    ]["Hour_{0:}".format(i + 1)] != 0 else setback
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="CoolingSetpointDayWeekend",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = setpoint if ZONE_CONDITIONS[
        "cooling_setpoint_weekend"
    ]["Hour_{0:}".format(i + 1)] != 0 else setback

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
    ]["Hour_{0:}".format(i + 1)] != 0 else setback
TEMP = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="HeatingSetpointDayWeekend",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)
for i in range(24):
    TEMP["Hour_{0:}".format(i + 1)] = setpoint if ZONE_CONDITIONS[
        "heating_setpoint_weekend"
    ]["Hour_{0:}".format(i + 1)] != 0 else setback

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
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS["occupant_sensible_gain_watts_per_person"]  # + ZONE_CONDITIONS["occupant_latent_gain_watts_per_person"]
print("SCHEDULE:DAY:HOURLY modified")

# Remove the current Weekly profiles and replace with compact weekly profiles
idf.idfobjects["SCHEDULE:WEEK:DAILY"] = []
print("SCHEDULE:WEEK:DAILY removed")

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
print("SCHEDULE:WEEK:COMPACT modified")

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
print("SCHEDULE:YEAR modified")

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
print("PEOPLE modified")

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
print("LIGHTS modified")

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
print("ELECTRICEQUIPMENT modified")

# Set infiltration rate for all zones
idf.idfobjects["ZONEINFILTRATION:DESIGNFLOWRATE"] = []
# idf.newidfobject(
#     "ZONEINFILTRATION:DESIGNFLOWRATE",
#     Name="InfiltrationGain",
#     Zone_or_ZoneList_Name="AllZones",
#     Schedule_Name="InfiltrationYear",
#     Design_Flow_Rate_Calculation_Method="Flow/Area",
#     Flow_per_Zone_Floor_Area=0.000227,
#     Constant_Term_Coefficient=1,
#     Temperature_Term_Coefficient=0,
#     Velocity_Term_Coefficient=0,
#     Velocity_Squared_Term_Coefficient=0
# )
idf.idfobjects["ZONEVENTILATION:DESIGNFLOWRATE"] = []
idf.newidfobject(
    "ZONEVENTILATION:DESIGNFLOWRATE",
    Name="Infiltration",
    Zone_or_ZoneList_Name="AllZones",
    Schedule_Name="InfiltrationYear",
    Design_Flow_Rate_Calculation_Method="Flow/Area",
    Flow_Rate_per_Zone_Floor_Area=0.000227,
    Ventilation_Type="Natural"
)
print("ZONEINFILTRATION:DESIGNFLOWRATE modified")

# Set ventilation rate for all zones
# idf.idfobjects["ZONEVENTILATION:DESIGNFLOWRATE"] = []
idf.newidfobject(
    "ZONEVENTILATION:DESIGNFLOWRATE",
    Name="Ventilation",
    Zone_or_ZoneList_Name="AllZones",
    Schedule_Name="VentilationYear",
    Design_Flow_Rate_Calculation_Method="Flow/Person",
    Flow_Rate_per_Person=ZONE_CONDITIONS["ventilation_litres_per_second_per_person"],
    Ventilation_Type="Natural"
)
print("ZONEVENTILATION:DESIGNFLOWRATE modified")

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
print("HVACTEMPLATE:THERMOSTAT modified")

# Set Ideal Loads Air System air supply based on internal TEMPlate
idf.idfobjects["HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM"] = []
for i in idf.idfobjects["ZONE"]:
    idf.newidfobject(
        "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
        Zone_Name=i.Name,
        Template_Thermostat_Name=j+"_HVAC",
        System_Availability_Schedule_Name="",
        Maximum_Heating_Supply_Air_Temperature=50,
        Minimum_Cooling_Supply_Air_Temperature=13,
        Maximum_Heating_Supply_Air_Humidity_Ratio=0.0156,
        Minimum_Cooling_Supply_Air_Humidity_Ratio=0.0077,
        Heating_Limit="",
        Maximum_Heating_Air_Flow_Rate="",
        Maximum_Sensible_Heating_Capacity="",
        Cooling_Limit="NoLimit",
        Maximum_Cooling_Air_Flow_Rate=0,
        Maximum_Total_Cooling_Capacity="",
        Heating_Availability_Schedule_Name="",
        Cooling_Availability_Schedule_Name="",
        Dehumidification_Control_Type="None",
        Cooling_Sensible_Heat_Ratio="",
        Dehumidification_Setpoint="",
        Humidification_Control_Type="None",
        Humidification_Setpoint="",
        Outdoor_Air_Method="DetailedSpecification",
        Outdoor_Air_Flow_Rate_per_Person="",
        Outdoor_Air_Flow_Rate_per_Zone_Floor_Area="",
        Outdoor_Air_Flow_Rate_per_Zone="",
        Design_Specification_Outdoor_Air_Object_Name="ZoneOutdoorAir",
        Demand_Controlled_Ventilation_Type="",
        Outdoor_Air_Economizer_Type="NoEconomizer",
        Heat_Recovery_Type="None",
        Sensible_Heat_Recovery_Effectiveness="",
        Latent_Heat_Recovery_Effectiveness="")
print("HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM modified")

# Remove the HVAC objects provifing fresh air from outside
idf.idfobjects["DESIGNSPECIFICATION:OUTDOORAIR"] = []
idf.newidfobject(
    "DESIGNSPECIFICATION:OUTDOORAIR",
    Name="ZoneOutdoorAir",
    Outdoor_Air_Method="Flow/Person",
    Outdoor_Air_Flow_per_Person=float(ZONE_CONDITIONS["ventilation_litres_per_second_per_person"]) / 1000,
    Outdoor_Air_Schedule_Name="VentilationYear"
)
print("DESIGNSPECIFICATION:OUTDOORAIR modified")

# Set/remove sizing parameters
idf.idfobjects["SIZING:PARAMETERS"] = []
idf.newidfobject(
    "SIZING:PARAMETERS",
    Heating_Sizing_Factor=1.25,
    Cooling_Sizing_Factor=1.15
)
print("SIZING:PARAMETERS modified")

"""
The following section defines materials and constructions. The methods below
either allow for multi-layered constructions or single layered constructions
with no thermal mass. In the single layered, simplified construction method,
an additional compoennt of thermal mass is added to the zone to replicate
the effects this would have on space temperatures.

For the multiple layer constructions, the layers and propwerties of those
layers were provided by Michal Dengusiak from his SAM workflow, enabling the
modification of constructuion U-Value and g-Value
"""

# Remove glazing materials
idf.idfobjects["WINDOWMATERIAL:GLAZING"] = []

# Add new glazing materials
idf.newidfobject(
    "WINDOWMATERIAL:GLAZING",
    Name="CLEAR FLOAT 6MM",
    Optical_Data_Type="SpectralAverage",
    Thickness=0.0059,
    Solar_Transmittance_at_Normal_Incidence=0.783,  # TODO - REPLACE THIS WITH MODIFIABLE VALUE FOR CUSTOM G VALUE INPUT
    Front_Side_Solar_Reflectance_at_Normal_Incidence=0.071,
    Back_Side_Solar_Reflectance_at_Normal_Incidence=0.071,
    Visible_Transmittance_at_Normal_Incidence=0.78,  # TODO - REPLACE THIS WITH MODIFIABLE VALUE FOR CUSTOM TVIS INPUT
    Front_Side_Visible_Reflectance_at_Normal_Incidence=0.071,
    Back_Side_Visible_Reflectance_at_Normal_Incidence=0.071,
    Infrared_Transmittance_at_Normal_Incidence=0,
    Front_Side_Infrared_Hemispherical_Emissivity=0.84,
    Back_Side_Infrared_Hemispherical_Emissivity=0.84,
    Conductivity=1.06,  # TODO - REPLACE THIS WITH MODIFIABLE VALUE FOR CUSTOM GLAZING U VALUE INPUT
    Dirt_Correction_Factor_for_Solar_and_Visible_Transmittance=1,
    Solar_Diffusing="No"
)
print("WINDOWMATERIAL:GLAZING modified")

# Remove glazing gas materials
idf.idfobjects["WINDOWMATERIAL:GAS"] = []

# Add new glazing gas materials
idf.newidfobject(
    "WINDOWMATERIAL:GAS",
    Name="AIR 12MM",
    Gas_Type="Air",
    Thickness=0.012
)
print("WINDOWMATERIAL:GAS modified")

# Remove materials
idf.idfobjects["MATERIAL"] = []

# Add new materials
idf.newidfobject(
    "MATERIAL",
    Name="INTERIOR WALL",
    Name="C00_Gypsum Board_800.923kg/m3_0.161W/mK",
    Roughness="MediumSmooth",
    Thickness=0.019,
    Conductivity=0.161,
    Density=800.923,
    Specific_Heat=1090,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.4,
    Visible_Absorptance=0.4
)
idf.newidfobject(
    "MATERIAL",
    Name="INTERIOR WALL",
    Name="I00_Mineral Wool_50kg/m3_0.036W/mK",
    Roughness="MediumRough",
    Thickness=0.019,
    Conductivity=0.16,
    Density=50,
    Specific_Heat=1030,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1.0
)

# Remove constructions
idf.idfobjects["CONSTRUCTION"] = []

# Generate new constructions
idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR WINDOW",
    Outside_Layer="CLEAR FLOAT 6MM",
    Layer_2="AIR 12MM",
    Layer_3="CLEAR FLOAT 6MM",
)
idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR WALL",
    Outside_Layer="C00_Gypsum Board_800.923kg/m3_0.161W/mK",
    Layer_2="I00_Mineral Wool_50kg/m3_0.036W/mK",
    Layer_3="C00_Gypsum Board_800.923kg/m3_0.161W/mK",
)
print("CONSTRUCTION modified")





# # The following describes a relationship between the input external wall U value and resultant exrternal wall UValue. It is used for converting teh users input target UI value into a corresponding value equivalnt to the overall wall u value that is intended, via the wall insulation thickness
# userinput_wallU = [0.001, 0.02138776, 0.04177551, 0.06216327, 0.08255102, 0.10293878, 0.12332653, 0.14371429, 0.16410204, 0.1844898, 0.20487755, 0.22526531, 0.24565306, 0.26604082, 0.28642857, 0.30681633, 0.32720408, 0.34759184, 0.36797959, 0.38836735, 0.4087551, 0.42914286, 0.44953061, 0.46991837, 0.49030612, 0.51069388, 0.53108163, 0.55146939, 0.57185714, 0.5922449, 0.61263265, 0.63302041, 0.65340816, 0.67379592, 0.69418367, 0.71457143, 0.73495918, 0.75534694, 0.77573469, 0.79612245, 0.8165102, 0.83689796, 0.85728571, 0.87767347, 0.89806122, 0.91844898, 0.93883673, 0.95922449, 0.97961224, 1]
# resultant_wallU = [1.923, 0.834, 0.532, 0.391, 0.309, 0.255, 0.218, 0.189, 0.168, 0.151, 0.137, 0.125, 0.115, 0.107, 0.1, 0.093, 0.088, 0.083, 0.078, 0.074, 0.071, 0.068, 0.065, 0.062, 0.059, 0.057, 0.055, 0.053, 0.051, 0.049, 0.048, 0.046, 0.045, 0.044, 0.042, 0.041, 0.04, 0.039, 0.038, 0.037, 0.036, 0.035, 0.034, 0.034, 0.033, 0.032, 0.031, 0.031, 0.03, 0.03]
# f_walluval = interpolate.interp1d(resultant_wallU, userinput_wallU)

# if CONFIG["exterior_wall_u_value"] > 1.923:
#     extWallUValue = f_walluval(1.923)
# elif CONFIG["exterior_wall_u_value"] < 0.03:
#     extWallUValue = f_walluval(0.03)
# else:
#     extWallUValue = f_walluval(CONFIG["exterior_wall_u_value"])

# # Modify existing materials
# idf.idfobjects["MATERIAL"] = []
# idf.newidfobject(
#     "MATERIAL",
#     Name="G01A 19MM GYPSUM BOARD",
#     Roughness="MediumSmooth",
#     Thickness=0.019,
#     Conductivity=0.16,
#     Density=800,
#     Specific_Heat=1090,
#     Thermal_Absorptance=0.9,
#     Solar_Absorptance=0.4,
#     Visible_Absorptance=0.4
# )
# idf.newidfobject(
#     "MATERIAL",
#     Name="M11 100MM LIGHTWEIGHT CONCRETE",
#     Roughness="MediumRough",
#     Thickness=0.1016,
#     Conductivity=0.53,
#     Density=1280,
#     Specific_Heat=840,
#     Thermal_Absorptance=0.9,
#     Solar_Absorptance=0.5,
#     Visible_Absorptance=0.5
# )
# idf.newidfobject(
#     "MATERIAL",
#     Name="F16 ACOUSTIC TILE",
#     Roughness="MediumSmooth",
#     Thickness=0.0191,
#     Conductivity=0.06,
#     Density=368,
#     Specific_Heat=590,
#     Thermal_Absorptance=0.9,
#     Solar_Absorptance=0.3,
#     Visible_Absorptance=0.3
# )
# idf.newidfobject(
#     "MATERIAL",
#     Name="AIR WALL MATERIAL",
#     Roughness="MediumSmooth",
#     Thickness=0.002,
#     Conductivity=0.6,
#     Density=800,
#     Specific_Heat=1000,
#     Thermal_Absorptance=0.95,
#     Solar_Absorptance=0.7,
#     Visible_Absorptance=0.7
# )
# idf.newidfobject(
#     "MATERIAL",
#     Name="M01 100MM BRICK",
#     Roughness="MediumRough",
#     Thickness=0.1016,
#     Conductivity=0.89,
#     Density=1920,
#     Specific_Heat=790,
#     Thermal_Absorptance=0.9,
#     Solar_Absorptance=0.7,
#     Visible_Absorptance=0.7
# )
# idf.newidfobject(
#     "MATERIAL",
#     Name="M15 200MM HEAVYWEIGHT CONCRETE",
#     Roughness="MediumRough",
#     Thickness=0.2032,
#     Conductivity=1.95,
#     Density=2240,
#     Specific_Heat=900,
#     Thermal_Absorptance=0.9,
#     Solar_Absorptance=0.7,
#     Visible_Absorptance=0.7
# )
# idf.newidfobject(
#     "MATERIAL",
#     Name="I02 50MM INSULATION BOARD",
#     Roughness="MediumRough",
#     Thickness=extWallUValue,  # 0.0508,
#     Conductivity=0.03,
#     Density=43,
#     Specific_Heat=1210,
#     Thermal_Absorptance=0.9,
#     Solar_Absorptance=0.7,
#     Visible_Absorptance=0.7
# )
# print("MATERIAL modified")

# # Modify existing air gap materials
# idf.idfobjects["MATERIAL:AIRGAP"] = []
# idf.newidfobject(
#     "MATERIAL:AIRGAP",
#     Name="F04 WALL AIR SPACE RESISTANCE",
#     Thermal_Resistance=0.15
# )

# # The following describes a relationship between the input Roof U value and overall floor/ceiling U value. It is used for converting teh users input Roof U value into a corresponding value equivalnt to the overall roof u value that is intended
# userinput_roofU = [1.542, 1.519, 1.496, 1.473, 1.452, 1.431, 1.411, 1.391, 1.372, 1.353, 1.335, 1.317, 1.3, 1.283, 1.266, 1.25, 1.235, 1.22, 1.205, 1.19, 1.176, 1.162, 1.149, 1.136, 1.123, 1.11, 1.098, 1.086, 1.074, 1.063, 1.051, 1.04, 1.03, 1.019, 1.009, 0.998, 0.988, 0.979, 0.969, 0.96, 0.951, 0.942, 0.933, 0.924, 0.915, 0.907, 0.899, 0.891, 0.883, 0.875, 0.867, 0.86, 0.852, 0.845, 0.838, 0.831, 0.824, 0.817, 0.811, 0.804, 0.798, 0.791, 0.785, 0.779, 0.773, 0.767, 0.761, 0.755, 0.749, 0.744, 0.738, 0.733, 0.727, 0.722, 0.717, 0.712, 0.707, 0.702, 0.697, 0.692, 0.687, 0.682, 0.678, 0.673, 0.668, 0.664, 0.66, 0.655, 0.651, 0.647, 0.642, 0.638, 0.634, 0.63, 0.626, 0.622, 0.618, 0.615, 0.611, 0.607, 0.569, 0.535, 0.505, 0.478, 0.454, 0.432, 0.412, 0.394, 0.378, 0.363, 0.35, 0.337, 0.326, 0.315, 0.305, 0.295, 0.287, 0.278, 0.27, 0.263, 0.256, 0.249, 0.243, 0.237, 0.231, 0.225, 0.22, 0.215, 0.194, 0.177, 0.163, 0.15, 0.14, 0.131, 0.123, 0.116, 0.109, 0.104, 0.099]
# resultant_roofU = [0.001, 0.011091, 0.021182, 0.031273, 0.041364, 0.051455, 0.061545, 0.071636, 0.081727, 0.091818, 0.101909, 0.112, 0.122091, 0.132182, 0.142273, 0.152364, 0.162455, 0.172545, 0.182636, 0.192727, 0.202818, 0.212909, 0.223, 0.233091, 0.243182, 0.253273, 0.263364, 0.273455, 0.283545, 0.293636, 0.303727, 0.313818, 0.323909, 0.334, 0.344091, 0.354182, 0.364273, 0.374364, 0.384455, 0.394545, 0.404636, 0.414727, 0.424818, 0.434909, 0.445, 0.455091, 0.465182, 0.475273, 0.485364, 0.495455, 0.505545, 0.515636, 0.525727, 0.535818, 0.545909, 0.556, 0.566091, 0.576182, 0.586273, 0.596364, 0.606455, 0.616545, 0.626636, 0.636727, 0.646818, 0.656909, 0.667, 0.677091, 0.687182, 0.697273, 0.707364, 0.717455, 0.727545, 0.737636, 0.747727, 0.757818, 0.767909, 0.778, 0.788091, 0.798182, 0.808273, 0.818364, 0.828455, 0.838545, 0.848636, 0.858727, 0.868818, 0.878909, 0.889, 0.899091, 0.909182, 0.919273, 0.929364, 0.939455, 0.949545, 0.959636, 0.969727, 0.979818, 0.989909, 1, 1.111111, 1.222222, 1.333333, 1.444444, 1.555556, 1.666667, 1.777778, 1.888889, 2, 2.105263, 2.210526, 2.315789, 2.421053, 2.526316, 2.631579, 2.736842, 2.842105, 2.947368, 3.052632, 3.157895, 3.263158, 3.368421, 3.473684, 3.578947, 3.684211, 3.789474, 3.894737, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5]
# f_roofUvalue = interpolate.interp1d(userinput_roofU, resultant_roofU)
# if CONFIG["exterior_roof_u_value"] > max(userinput_roofU):
#     ceilResistance = f_roofUvalue(max(userinput_roofU))
# elif CONFIG["exterior_roof_u_value"] < min(userinput_roofU):
#     ceilResistance = f_roofUvalue(min(userinput_roofU))
# else:
#     ceilResistance = f_roofUvalue(CONFIG["exterior_roof_u_value"])

# idf.newidfobject(
#     "MATERIAL:AIRGAP",
#     Name="F05 CEILING AIR SPACE RESISTANCE",
#     Thermal_Resistance=ceilResistance
# )
# print("MATERIAL:AIRGAP modified")





# # The following describes a relationship between the input Solar Heat Transmittance and overal window SHGC. It is used for converting teh users input SHGC into a corresponding value equivalnt to the overall window g-Value that is intended
# userinput_g_value = [0.01, 0.05684211, 0.10368421, 0.15052632, 0.19736842, 0.24421053, 0.29105263, 0.33789474, 0.38473684, 0.43157895, 0.47842105, 0.52526316, 0.57210526, 0.61894737, 0.66578947, 0.71263158, 0.75947368, 0.80631579, 0.85315789, 0.9]
# resultant_g_value = [0.2, 0.221, 0.243, 0.267, 0.292, 0.318, 0.346, 0.375, 0.406, 0.438, 0.471, 0.506, 0.542, 0.579, 0.615, 0.656, 0.697, 0.74 ,0.785, 0.832]
# f_gvalue = interpolate.interp1d(resultant_g_value, userinput_g_value)
# if CONFIG["glass_solar_heat_gain_coefficient"] > max(userinput_g_value):
#     glassGValue = f_gvalue(max(userinput_g_value))
# elif CONFIG["glass_solar_heat_gain_coefficient"] < min(userinput_g_value):
#     glassGValue = f_gvalue(min(userinput_g_value))
# else:
#     glassGValue = f_gvalue(CONFIG["glass_solar_heat_gain_coefficient"])

# # The following describes a relationship between the input Glazing U Value and glass conductivity. It is used for converting the users input Glazing U Value into a corresponding value in the glass conductivity field equivalnt to the overall window U-Value that is intended
# userinput_conduct = [0.001, 0.00621053, 0.01142105, 0.01663158, 0.02184211, 0.02705263, 0.03226316, 0.03747368, 0.04268421, 0.04789474, 0.05310526, 0.05831579, 0.06352632, 0.06873684, 0.07394737, 0.07915789, 0.08436842, 0.08957895, 0.09478947, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
# resultant_ufactor = [0.157, 0.748, 1.118, 1.373, 1.559, 1.702, 1.814, 1.905, 1.98, 2.043, 2.096, 2.143, 2.183, 2.218, 2.25, 2.278, 2.303, 2.326, 2.347, 2.365, 2.552, 2.621, 2.657, 2.68, 2.695, 2.705, 2.714, 2.72, 2.725]
# f_ufactor = interpolate.interp1d(resultant_ufactor, userinput_conduct)
# if CONFIG["glass_u_value"] > max(resultant_ufactor):
#     glassConductivity = f_ufactor(max(resultant_ufactor))
# elif CONFIG["glass_u_value"] < min(resultant_ufactor):
#     glassConductivity = f_ufactor(min(resultant_ufactor))
# else:
#     glassConductivity = f_ufactor(CONFIG["glass_u_value"])

# # Modify the existing window materials
# idf.idfobjects["WINDOWMATERIAL:GLAZING"] = []
# idf.newidfobject(
#     "WINDOWMATERIAL:GLAZING",
#     Name="CLEAR 3MM",
#     Optical_Data_Type="SpectralAverage",
#     Thickness=0.003,
#     Solar_Transmittance_at_Normal_Incidence=glassGValue,  # glassGValue,  # This was determined by running the IDF with a ranger of inputs and determining the relationship between input g-value and overall g-value for the computed glazing
#     Front_Side_Solar_Reflectance_at_Normal_Incidence=0.075,
#     Back_Side_Solar_Reflectance_at_Normal_Incidence=0,
#     Visible_Transmittance_at_Normal_Incidence=CONFIG["glass_visible_transmittance"],
#     Front_Side_Visible_Reflectance_at_Normal_Incidence=0.081,
#     Back_Side_Visible_Reflectance_at_Normal_Incidence=0,
#     Infrared_Transmittance_at_Normal_Incidence=0,
#     Front_Side_Infrared_Hemispherical_Emissivity=0.84,
#     Back_Side_Infrared_Hemispherical_Emissivity=0.84,
#     Conductivity=glassConductivity,
#     Dirt_Correction_Factor_for_Solar_and_Visible_Transmittance=1,
#     Solar_Diffusing="No"
# )
# print("WINDOWMATERIAL:GLAZING modified")

# # Modify the existing Window Material Gas materials
# idf.idfobjects["WINDOWMATERIAL:GAS"] = []
# idf.newidfobject(
#     "WINDOWMATERIAL:GAS",
#     Name="AIR 13MM",
#     Gas_Type="Air",
#     Thickness=0.0127
# )
# print("WINDOWMATERIAL:GAS modified")

# # Modify Construction objects
# idf.idfobjects["CONSTRUCTION"] = []
# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="INTERIOR WALL",
#     Outside_Layer="G01A 19MM GYPSUM BOARD",
#     Layer_2="F04 WALL AIR SPACE RESISTANCE",
#     Layer_3="G01A 19MM GYPSUM BOARD",
# )
# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="INTERIOR WINDOW",
#     Outside_Layer="CLEAR 3MM"
# )
# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="EXTERIOR ROOF",
#     Outside_Layer="M11 100MM LIGHTWEIGHT CONCRETE",
#     Layer_2="F05 CEILING AIR SPACE RESISTANCE",
#     Layer_3="F16 ACOUSTIC TILE",
# )
# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="INTERIOR FLOOR",
#     Outside_Layer="F16 ACOUSTIC TILE",
#     Layer_2="F05 CEILING AIR SPACE RESISTANCE",
#     Layer_3="M11 100MM LIGHTWEIGHT CONCRETE",
# )
# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="AIR WALL",
#     Outside_Layer="AIR WALL MATERIAL"
# )
# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="EXTERIOR WALL",
#     Outside_Layer="M01 100MM BRICK",
#     Layer_2="M15 200MM HEAVYWEIGHT CONCRETE",
#     Layer_3="I02 50MM INSULATION BOARD",
#     # Layer_4="F04 WALL AIR SPACE RESISTANCE",  # Removed to modify insulation thickness nly for exterior wall U-value modification from IDF config file
#     Layer_4="G01A 19MM GYPSUM BOARD",
# )
# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="EXTERIOR WINDOW",
#     Outside_Layer="CLEAR 3MM",
#     Layer_2="AIR 13MM",
#     Layer_3="CLEAR 3MM",
# )
# print("CONSTRUCTION modified")

# # Create single layer window material for glazing transmittance/g-value
# idf.idfobjects["WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM"] = []

# idf.newidfobject(
#     "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
#     Name="EXTERIOR GLAZING MATERIAL_X",
#     UFactor=CONFIG["glass_u_value"],
#     Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_X"],
#     Visible_Transmittance=CONFIG["glass_visible_transmittance_X"]
# )

# idf.newidfobject(
#     "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
#     Name="EXTERIOR GLAZING MATERIAL_N",
#     UFactor=CONFIG["glass_u_value"],
#     Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_N"],
#     Visible_Transmittance=CONFIG["glass_visible_transmittance_N"]
# )

# idf.newidfobject(
#     "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
#     Name="EXTERIOR GLAZING MATERIAL_E",
#     UFactor=CONFIG["glass_u_value"],
#     Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_E"],
#     Visible_Transmittance=CONFIG["glass_visible_transmittance_N"]
# )

# idf.newidfobject(
#     "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
#     Name="EXTERIOR GLAZING MATERIAL_S",
#     UFactor=CONFIG["glass_u_value"],
#     Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_S"],
#     Visible_Transmittance=CONFIG["glass_visible_transmittance_N"]
# )

# idf.newidfobject(
#     "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
#     Name="EXTERIOR GLAZING MATERIAL_W",
#     UFactor=CONFIG["glass_u_value"],
#     Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient_W"],
#     Visible_Transmittance=CONFIG["glass_visible_transmittance_N"]
# )

# idf.newidfobject(
#     "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
#     Name="INTERIOR GLAZING MATERIAL",
#     UFactor=0.8,
#     Solar_Heat_Gain_Coefficient=0.9,
#     Visible_Transmittance=0.9
# )
# print("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM modified")

# # Create basic single layer materials with no mass for easy U-Value attribution
# idf.idfobjects["MATERIAL:NOMASS"] = []
# idf.newidfobject(
#     "MATERIAL:NOMASS",
#     Name="EXTERIOR WALL MATERIAL",
#     Roughness="MediumRough",
#     Thermal_Resistance=1 / CONFIG["exterior_wall_u_value"],
#     Thermal_Absorptance=0.5,
#     Solar_Absorptance=0.5,
#     Visible_Absorptance=1 - CONFIG["wall_reflectivity"]
# )

# idf.newidfobject(
#     "MATERIAL:NOMASS",
#     Name="INTERIOR WALL MATERIAL",
#     Roughness="MediumSmooth",
#     Thermal_Resistance=1.8,
#     Thermal_Absorptance=0.5,
#     Solar_Absorptance=0.5,
#     Visible_Absorptance=1 - CONFIG["wall_reflectivity"]
# )

# idf.newidfobject(
#     "MATERIAL:NOMASS",
#     Name="INTERIOR FLOOR MATERIAL",
#     Roughness="MediumSmooth",
#     Thermal_Resistance=1,
#     Thermal_Absorptance=0.5,
#     Solar_Absorptance=0.5,
#     Visible_Absorptance=1 - CONFIG["floor_reflectivity"]
# )

# idf.newidfobject(
#     "MATERIAL:NOMASS",
#     Name="INTERIOR CEILING MATERIAL",
#     Roughness="MediumSmooth",
#     Thermal_Resistance=1,
#     Thermal_Absorptance=0.5,
#     Solar_Absorptance=0.5,
#     Visible_Absorptance=1 - CONFIG["ceiling_reflectivity"]
# )

# idf.newidfobject(
#     "MATERIAL:NOMASS",
#     Name="EXTERIOR ROOF MATERIAL",
#     Roughness="MediumRough",
#     Thermal_Resistance=1 / CONFIG["exterior_roof_u_value"],
#     Thermal_Absorptance=0.5,
#     Solar_Absorptance=0.5,
#     Visible_Absorptance=1 - CONFIG["ceiling_reflectivity"]
# )

# idf.newidfobject(
#     "MATERIAL:NOMASS",
#     Name="AIR WALL MATERIAL",
#     Roughness="MediumRough",
#     Thermal_Resistance=0.001,
#     Thermal_Absorptance=0.001,
#     Solar_Absorptance=0.001,
#     Visible_Absorptance=0.001
# )
# print("MATERIAL:NOMASS modified")

# idf.newidfobject(
#     "MATERIAL",
#     Name="THERMAL MASS MATERIAL",
#     Roughness="MediumRough",
#     Thickness=0.3,
#     Conductivity=2,
#     Density=1500,
#     Specific_Heat=900,
#     Thermal_Absorptance=0.5,
#     Solar_Absorptance=0.7,
#     Visible_Absorptance=0.7
# )
# print("MATERIAL modified")

# # Set the constructions for the whole building
# idf.idfobjects["CONSTRUCTION"] = []
# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="EXTERIOR WALL",
#     Outside_Layer="EXTERIOR WALL MATERIAL"
# )

# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="INTERIOR WALL",
#     Outside_Layer="INTERIOR WALL MATERIAL"
# )

# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="INTERIOR FLOOR",
#     Outside_Layer="INTERIOR FLOOR MATERIAL"
# )

# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="INTERIOR CEILING",
#     Outside_Layer="INTERIOR CEILING MATERIAL"
# )

# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="EXTERIOR ROOF",
#     Outside_Layer="EXTERIOR ROOF MATERIAL"
# )

# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="AIR WALL",
#     Outside_Layer="AIR WALL MATERIAL"
# )

# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="EXTERIOR WINDOW",
#     Outside_Layer="EXTERIOR GLAZING MATERIAL_X"
# )

# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="INTERIOR WINDOW",
#     Outside_Layer="INTERIOR GLAZING MATERIAL"
# )

# idf.newidfobject(
#     "CONSTRUCTION",
#     Name="THERMAL MASS",
#     Outside_Layer="THERMAL MASS MATERIAL"
# )
# print("CONSTRUCTION modified")

# # Get external surface areas for each zone and assign internal mass
# ZONE_WALL_AREA = []
# for zone in [str(i.Name) for i in idf.idfobjects["ZONE"]]:
#     area = 0
#     for surface in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
#         if (surface.Zone_Name == zone) & (str(surface.Sun_Exposure) == "SunExposed"):
#             area += surface.area
#     ZONE_WALL_AREA.append(area)

# idf.idfobjects["INTERNALMASS"] = []
# for i, j in list(zip([str(i.Name) for i in idf.idfobjects["ZONE"]], ZONE_WALL_AREA)):
#     if j != 0:
#         idf.newidfobject(
#             "INTERNALMASS",
#             Name=i + "_MASS",
#             Construction_Name="THERMAL MASS",
#             Zone_Name=i,
#             Surface_Area=j*0.8
#         )
#     else:
#         pass
# print("INTERNALMASS modified")

# Create a list zones to be referenced for passing the internal gains setpoints
TEMP = idf.newidfobject("ZONELIST", Name="AllZones")
for i, j in enumerate([str(i.Name) for i in idf.idfobjects["ZONE"]]):
    TEMP["Zone_{0:}_Name".format(i + 1)] = j
print("ZONELIST modified")

# Output variables to report during simulation
# NOTE - Lots of variables commented out here - these are all the possible outputs, but we only really need the ones that aren't commented
OUTPUT_VARIABLES = [
    # "Electric Equipment Convective Heating Energy",
    # "Electric Equipment Convective Heating Rate",
    # "Electric Equipment Electric Energy",
    # "Electric Equipment Electric Power",
    # "Electric Equipment Latent Gain Energy",
    # "Electric Equipment Latent Gain Rate",
    # "Electric Equipment Lost Heat Energy",
    # "Electric Equipment Lost Heat Rate",
    # "Electric Equipment Radiant Heating Energy",
    # "Electric Equipment Radiant Heating Rate",
    # "Electric Equipment Total Heating Energy",
    # "Electric Equipment Total Heating Rate",
    # "Lights Convective Heating Energy",
    # "Lights Convective Heating Rate",
    # "Lights Electric Energy",
    # "Lights Electric Power",
    # "Lights Radiant Heating Energy",
    # "Lights Radiant Heating Rate",
    # "Lights Return Air Heating Energy",
    # "Lights Return Air Heating Rate",
    # "Lights Total Heating Energy",
    # "Lights Total Heating Rate",
    # "Lights Visible Radiation Heating Energy",
    # "Lights Visible Radiation Heating Rate",
    # "People Air Relative Humidity",
    # "People Air Temperature",
    # "People Convective Heating Energy",
    # "People Convective Heating Rate",
    # "People Latent Gain Energy",
    # "People Latent Gain Rate",
    # "People Occupant Count",
    # "People Radiant Heating Energy",
    # "People Radiant Heating Rate",
    # "People Sensible Heating Energy",
    # "People Sensible Heating Rate",
    # "People Total Heating Energy",
    # "People Total Heating Rate",
    # "Zone Air Heat Balance Air Energy Storage Rate",
    # "Zone Air Heat Balance Internal Convective Heat Gain Rate",
    # "Zone Air Heat Balance Interzone Air Transfer Rate",
    # "Zone Air Heat Balance Outdoor Air Transfer Rate",
    # "Zone Air Heat Balance Surface Convection Rate",
    # "Zone Air Heat Balance System Air Transfer Rate",
    # "Zone Air Heat Balance System Convective Heat Gain Rate",
    # "Zone Air Humidity Ratio",
    "Zone Air Relative Humidity",
    # "Zone Air System Sensible Cooling Energy",
    # "Zone Air System Sensible Cooling Rate",
    # "Zone Air System Sensible Heating Energy",
    # "Zone Air System Sensible Heating Rate",
    "Zone Air Temperature",
    # "Zone Electric Equipment Convective Heating Energy",
    # "Zone Electric Equipment Convective Heating Rate",
    # "Zone Electric Equipment Electric Energy",
    # "Zone Electric Equipment Electric Power",
    # "Zone Electric Equipment Latent Gain Energy",
    # "Zone Electric Equipment Latent Gain Rate",
    # "Zone Electric Equipment Lost Heat Energy",
    # "Zone Electric Equipment Lost Heat Rate",
    # "Zone Electric Equipment Radiant Heating Energy",
    # "Zone Electric Equipment Radiant Heating Rate",
    "Zone Electric Equipment Total Heating Energy",
    # "Zone Electric Equipment Total Heating Rate",
    # "Zone Exterior Windows Total Transmitted Beam Solar Radiation Energy",
    # "Zone Exterior Windows Total Transmitted Beam Solar Radiation Rate",
    # "Zone Exterior Windows Total Transmitted Diffuse Solar Radiation Energy",
    # "Zone Exterior Windows Total Transmitted Diffuse Solar Radiation Rate",
    # "Zone Ideal Loads Economizer Active Time [hr]",
    # "Zone Ideal Loads Heat Recovery Active Time [hr]",
    # "Zone Ideal Loads Heat Recovery Latent Cooling Energy",
    # "Zone Ideal Loads Heat Recovery Latent Cooling Rate",
    # "Zone Ideal Loads Heat Recovery Latent Heating Energy",
    # "Zone Ideal Loads Heat Recovery Latent Heating Rate",
    # "Zone Ideal Loads Heat Recovery Sensible Cooling Energy",
    # "Zone Ideal Loads Heat Recovery Sensible Cooling Rate",
    # "Zone Ideal Loads Heat Recovery Sensible Heating Energy",
    # "Zone Ideal Loads Heat Recovery Sensible Heating Rate",
    # "Zone Ideal Loads Heat Recovery Total Cooling Energy",
    # "Zone Ideal Loads Heat Recovery Total Cooling Rate",
    # "Zone Ideal Loads Heat Recovery Total Heating Energy",
    # "Zone Ideal Loads Heat Recovery Total Heating Rate",
    # "Zone Ideal Loads Hybrid Ventilation Available Status",
    # "Zone Ideal Loads Outdoor Air Latent Cooling Energy",
    # "Zone Ideal Loads Outdoor Air Latent Cooling Rate",
    # "Zone Ideal Loads Outdoor Air Latent Heating Energy",
    # "Zone Ideal Loads Outdoor Air Latent Heating Rate",
    # "Zone Ideal Loads Outdoor Air Mass Flow Rate",
    # "Zone Ideal Loads Outdoor Air Sensible Cooling Energy",
    # "Zone Ideal Loads Outdoor Air Sensible Cooling Rate",
    # "Zone Ideal Loads Outdoor Air Sensible Heating Energy",
    # "Zone Ideal Loads Outdoor Air Sensible Heating Rate",
    # "Zone Ideal Loads Outdoor Air Standard Density Volume Flow Rate",
    "Zone Ideal Loads Outdoor Air Sensible Cooling Energy",
    # "Zone Ideal Loads Outdoor Air Total Cooling Rate",
    "Zone Ideal Loads Outdoor Air Sensible Heating Energy",
    # "Zone Ideal Loads Outdoor Air Total Heating Rate",
    # "Zone Ideal Loads Supply Air Latent Cooling Energy",
    # "Zone Ideal Loads Supply Air Latent Cooling Rate",
    # "Zone Ideal Loads Supply Air Latent Heating Energy",
    # "Zone Ideal Loads Supply Air Latent Heating Rate",
    # "Zone Ideal Loads Supply Air Mass Flow Rate",
    # "Zone Ideal Loads Supply Air Sensible Cooling Energy",
    # "Zone Ideal Loads Supply Air Sensible Cooling Rate",
    # "Zone Ideal Loads Supply Air Sensible Heating Energy",
    # "Zone Ideal Loads Supply Air Sensible Heating Rate",
    # "Zone Ideal Loads Supply Air Standard Density Volume Flow Rate",
    # "Zone Ideal Loads Supply Air Total Cooling Energy",
    # "Zone Ideal Loads Supply Air Total Cooling Rate",
    # "Zone Ideal Loads Supply Air Total Heating Energy",
    # "Zone Ideal Loads Supply Air Total Heating Rate",
    # "Zone Ideal Loads Zone Latent Cooling Energy",
    # "Zone Ideal Loads Zone Latent Cooling Rate",
    # "Zone Ideal Loads Zone Latent Heating Energy",
    # "Zone Ideal Loads Zone Latent Heating Rate",
    # "Zone Ideal Loads Zone Sensible Cooling Energy",
    # "Zone Ideal Loads Zone Sensible Cooling Rate",
    # "Zone Ideal Loads Zone Sensible Heating Energy",
    # "Zone Ideal Loads Zone Sensible Heating Rate",
    # "Zone Ideal Loads Zone Total Cooling Energy",
    # "Zone Ideal Loads Zone Total Cooling Rate",
    # "Zone Ideal Loads Zone Total Heating Energy",
    # "Zone Ideal Loads Zone Total Heating Rate",
    # "Zone Infiltration Air Change Rate",
    # "Zone Infiltration Current Density Volume Flow Rate",
    # "Zone Infiltration Current Density Volume",
    # "Zone Infiltration Latent Heat Gain Energy",
    # "Zone Infiltration Latent Heat Loss Energy",
    # "Zone Infiltration Mass Flow Rate",
    # "Zone Infiltration Mass",
    # "Zone Infiltration Sensible Heat Gain Energy",
    # "Zone Infiltration Sensible Heat Loss Energy",
    # "Zone Infiltration Standard Density Volume Flow Rate",
    # "Zone Infiltration Standard Density Volume",
    # "Zone Infiltration Total Heat Gain Energy",
    # "Zone Infiltration Total Heat Loss Energy",
    # "Zone Interior Windows Total Transmitted Beam Solar Radiation Energy",
    # "Zone Interior Windows Total Transmitted Beam Solar Radiation Rate",
    # "Zone Interior Windows Total Transmitted Diffuse Solar Radiation Energy",
    # "Zone Interior Windows Total Transmitted Diffuse Solar Radiation Rate",
    # "Zone Lights Convective Heating Energy",
    # "Zone Lights Convective Heating Rate",
    # "Zone Lights Electric Energy",
    # "Zone Lights Electric Power",
    # "Zone Lights Radiant Heating Energy",
    # "Zone Lights Radiant Heating Rate",
    # "Zone Lights Return Air Heating Energy",
    # "Zone Lights Return Air Heating Rate",
    "Zone Lights Total Heating Energy",
    # "Zone Lights Total Heating Rate",
    # "Zone Lights Visible Radiation Heating Energy",
    # "Zone Lights Visible Radiation Heating Rate",
    "Zone Mean Air Dewpoint Temperature",
    # "Zone Mean Air Humidity Ratio",
    "Zone Mean Air Temperature",
    "Zone Mean Radiant Temperature",
    # "Zone Mechanical Ventilation Air Changes per Hour",
    # "Zone Mechanical Ventilation Cooling Load Decrease Energy",
    # "Zone Mechanical Ventilation Cooling Load Increase Due to Overheating Energy",
    # "Zone Mechanical Ventilation Cooling Load Increase Energy",
    "Zone Mechanical Ventilation Current Density Volume Flow Rate",
    # "Zone Mechanical Ventilation Current Density Volume",
    # "Zone Mechanical Ventilation Heating Load Decrease Energy",
    # "Zone Mechanical Ventilation Heating Load Increase Due to Overcooling Energy",
    # "Zone Mechanical Ventilation Heating Load Increase Energy",
    # "Zone Mechanical Ventilation Mass Flow Rate",
    # "Zone Mechanical Ventilation Mass",
    # "Zone Mechanical Ventilation No Load Heat Addition Energy",
    # "Zone Mechanical Ventilation No Load Heat Removal Energy",
    # "Zone Mechanical Ventilation Standard Density Volume Flow Rate",
    # "Zone Mechanical Ventilation Standard Density Volume",
    # "Zone Mixing Current Density Volume Flow Rate",
    # "Zone Mixing Latent Heat Gain Energy",
    # "Zone Mixing Latent Heat Loss Energy",
    # "Zone Mixing Mass Flow Rate",
    # "Zone Mixing Mass",
    # "Zone Mixing Sensible Heat Gain Energy",
    # "Zone Mixing Sensible Heat Loss Energy",
    # "Zone Mixing Standard Density Volume Flow Rate",
    # "Zone Mixing Total Heat Gain Energy",
    # "Zone Mixing Total Heat Loss Energy",
    # "Zone Mixing Volume",
    # "Zone Operative Temperature",
    # "Zone Outdoor Air Drybulb Temperature",
    # "Zone Outdoor Air Wetbulb Temperature",
    # "Zone Outdoor Air Wind Direction",
    # "Zone Outdoor Air Wind Speed",
    # "Zone People Convective Heating Energy",
    # "Zone People Convective Heating Rate",
    # "Zone People Latent Gain Energy",
    # "Zone People Latent Gain Rate",
    "Zone People Occupant Count",
    # "Zone People Radiant Heating Energy",
    # "Zone People Radiant Heating Rate",
    # "Zone People Sensible Heating Energy",
    # "Zone People Sensible Heating Rate",
    "Zone People Total Heating Energy",
    # "Zone People Total Heating Rate",
    # "Zone Thermostat Air Temperature",
    # "Zone Thermostat Control Type",
    "Zone Thermostat Cooling Setpoint Temperature",
    "Zone Thermostat Heating Setpoint Temperature",
    # "Zone Total Internal Convective Heating Energy",
    # "Zone Total Internal Convective Heating Rate",
    # "Zone Total Internal Latent Gain Energy",
    # "Zone Total Internal Latent Gain Rate",
    # "Zone Total Internal Radiant Heating Energy",
    # "Zone Total Internal Radiant Heating Rate",
    "Zone Total Internal Total Heating Energy",
    # "Zone Total Internal Total Heating Rate",
    # "Zone Total Internal Visible Radiation Heating Energy",
    # "Zone Total Internal Visible Radiation Heating Rate",
    # "Zone Windows Total Heat Gain Energy",
    # "Zone Windows Total Heat Gain Rate",
    # "Zone Windows Total Heat Loss Energy",
    # "Zone Windows Total Heat Loss Rate",
    "Zone Windows Total Transmitted Solar Radiation Energy",
    # "Zone Windows Total Transmitted Solar Radiation Rate",
]

# Set the list of outputs to be generated from the EnergyPLus simulation  # NOTE - Uncomment these for actual outputs in table - not bere for testig purposes currently
idf.idfobjects["OUTPUT:VARIABLE"] = []
[
    idf.newidfobject(
        "OUTPUT:VARIABLE",
        Key_Value="*",
        Variable_Name=i,
        Reporting_Frequency="hourly"
    ) for i in OUTPUT_VARIABLES
]
print("OUTPUT:VARIABLE modified")

# # Diagnostics/testing
# """
# The following section adds a bunch of diagnostics toools that can be used for checking how well the simulation has run
# This includes:
#     A list of potential output variables possible from the completed/failed simulation
#     A list of the constructions in the completed/failed simulation - including U-values and thermal mass
#     An SQLite format output result from the completed/failed simulation - this is probably better than using ReadVarsESO, but needs some further work]
#     A detailed output diagnostics file indicatign any major issues in the completed/failed simulation
# """
# idf.idfobjects["OUTPUT:VARIABLEDICTIONARY"] = []
# idf.newidfobject("OUTPUT:VARIABLEDICTIONARY", Key_Field="regular")
# print("OUTPUT:VARIABLEDICTIONARY modified")

# idf.idfobjects["OUTPUT:CONSTRUCTIONS"] = []
# idf.newidfobject("OUTPUT:CONSTRUCTIONS", Details_Type_1="Constructions")

# idf.idfobjects["OUTPUT:SQLITE"] = []
# idf.newidfobject("OUTPUT:SQLITE", Option_Type="Simple")

# idf.idfobjects["OUTPUT:DIAGNOSTICS"] = []
# idf.newidfobject("OUTPUT:DIAGNOSTICS", Key_1="DisplayExtraWarnings", Key_2="DisplayUnusedSchedules")



############################################################################################################################################################################################
# Outputs for Michal - TAS test
# idf.newidfobject("OUTPUT:SURFACES:LIST", Report_Type="Details")
idf.newidfobject("OUTPUTCONTROL:TABLE:STYLE", Column_Separator="Comma")
idf.newidfobject("OUTPUT:TABLE:SUMMARYREPORTS", Report_1_Name="AllSummary")
# idf.idfobjects["SHADING:BUILDING:DETAILED"] = []  # Remove shading elements
# idf.idfobjects["SHADOWCALCULATION"] = []
# idf.newidfobject(
#     "SHADOWCALCULATION",
#     Calculation_Method="AverageOverDaysInFrequency",
#     Calculation_Frequency=20,
#     Maximum_Figures_in_Shadow_Overlap_Calculations=15000,
#     Polygon_Clipping_Algorithm="SutherlandHodgman",
#     Sky_Diffuse_Modeling_Algorithm="SimpleSkyDiffuseModeling",
#     External_Shading_Calculation_Method="InternalCalculation",
#     Output_External_Shading_Calculation_Results="Yes"  # NOTE - Remove this for final version - this is used for testing export to TAS
)
# idf.idfobjects["SIMULATIONCONTROL"] = []
# idf.newidfobject(
#     "SIMULATIONCONTROL",
#     Do_Zone_Sizing_Calculation="No",
#     Do_System_Sizing_Calculation="No",
#     Do_Plant_Sizing_Calculation="No",
#     Run_Simulation_for_Sizing_Periods="No",
#     Run_Simulation_for_Weather_File_Run_Periods="Yes"
# )
############################################################################################################################################################################################




# Save the idf to a new file
idf.saveas(IDF_FILEPATH.replace(".idf", "_modified.idf"))
print("\nIDF file modified and saved to {0:}".format(IDF_FILEPATH.replace(".idf", "_modified.idf")))
