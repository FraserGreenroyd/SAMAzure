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
    TODO - Fix the glazing solar heat gain assignment from the config file for different orientations
    TODO - Add option for ground temperature inclusion from the Weatherfile if these are available
"""

import json
import sys
from eppy.modeleditor import IDF
import platform
from scipy import interpolate

##########################################
# FREQUENTLY USED FUNCTIONS DEFINED HERE #
##########################################

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

#########################################################################
# LOAD THE IDF TO BE MODIFIED AND THE CONFIG FILE USED TO MODIFY VALUES #
#########################################################################

IDF_FILEPATH = sys.argv[1]
CONFIG_FILEPATH = sys.argv[2]

with open(CONFIG_FILEPATH, "r") as f:
    CONFIG = json.load(f)

print("\nConfig loaded from {0:}\n".format(CONFIG_FILEPATH))

IDF_FILE = sys.argv[1]
if "win" in platform.platform().lower() and "dar" not in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_windows"])
elif "linux" in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_linux"])
elif "dar" in platform.platform().lower():
    IDF.setiddname(CONFIG["idd_file_os"])

#########################################################################
# LOAD THE EPW SPECIFIED IN THE CONFIG FILE AND ASSIGN IDF TO IDFOBJECT #
#########################################################################

EPW_FILE = CONFIG["weather_file"]
idf = IDF(IDF_FILE)

print("IDF loaded from {0:}\n".format(IDF_FILEPATH))
print("EPW loaded from {0:}\n".format(EPW_FILE))

####################################################################################
# LOAD THE JSON SPECIFIED IN THE CONFIG FILE THAT CONTAINS ZONE PROFILES AND GAINS #
####################################################################################

ZONE_CONDITIONS = load_json(CONFIG["zone_conditions_library"])[CONFIG["zone_template"]]

print("Zone conditions loaded from {1:}\nZone conditions set to {0:}\n".format(CONFIG["zone_template"], CONFIG["zone_conditions_library"]))

#######################################################################
# MODIFY IDF SITE INFORMATION USING DATA FROM THE REFERENCED EPW FILE #
#######################################################################

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

#################################
# SET ENERGYPLUS VERSION NUMBER #
#################################

idf.idfobjects["VERSION"] = []

idf.newidfobject(
    "VERSION",
    Version_Identifier="8.8.0"
)

print("VERSION modified")

######################################################
# REMOVE DESIGN DAY SIZING PERIODS FROM THE IDF FILE #
######################################################

idf.idfobjects["SIZINGPERIOD:DESIGNDAY"] = []

print("SIZINGPERIOD:DESIGNDAY modified")

#######################################################################
# SET SIMULATION TO RUN ONLY FOR ANNUAL PERIOD USING WITH WEATHERFILE #
#######################################################################

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

####################################################################
# SET SIMULATION RUN PERIOD AND START DAY (FOR PROFILE ASSIGNMENT) #
####################################################################

idf.idfobjects["RUNPERIOD"] = []

idf.newidfobject(
    "RUNPERIOD",
    Name="PARAMETRIC RUN",
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

#################################################################
# SET GROUND TEMPERATURE VALUES - CURRENTLY FIXED AT 18 DEFAULT #
#################################################################

idf.idfobjects["SITE:GROUNDTEMPERATURE:BUILDINGSURFACE"] = []

idf.newidfobject(
    "SITE:GROUNDTEMPERATURE:BUILDINGSURFACE",
    January_Ground_Temperature=18,
    February_Ground_Temperature=18,
    March_Ground_Temperature=18,
    April_Ground_Temperature=18,
    May_Ground_Temperature=18,
    June_Ground_Temperature=18,
    July_Ground_Temperature=18,
    August_Ground_Temperature=18,
    September_Ground_Temperature=18,
    October_Ground_Temperature=18,
    November_Ground_Temperature=18,
    December_Ground_Temperature=18
)

print("SITE:GROUNDTEMPERATURE:BUILDINGSURFACE modified")

###########################
# SET BUILDING PARAMETERS #
###########################

idf.idfobjects["BUILDING"] = []

idf.newidfobject(
    "BUILDING",
    Name="IHOPETHISWORKS",
    North_Axis=0,
    Terrain="City",
    Solar_Distribution="FullInteriorAndExteriorWithReflections",
    Maximum_Number_of_Warmup_Days=25,
    Minimum_Number_of_Warmup_Days=6
)

print("BUILDING modified")

##################################################
# SET NUMBER OF TIMESTEPS PER HOUR IN SIMULATION #
##################################################

idf.idfobjects["TIMESTEP"] = []

idf.newidfobject(
    "TIMESTEP",
    Number_of_Timesteps_per_Hour=6
)

print("TIMESTEP modified")

#################################
# SET SHADOW CALCULATION METHOD #
#################################

idf.idfobjects["SHADOWCALCULATION"] = []

idf.newidfobject(
    "SHADOWCALCULATION",
    Calculation_Method="AverageOverDaysInFrequency",
    Calculation_Frequency=20,
    Maximum_Figures_in_Shadow_Overlap_Calculations=15000,
    Polygon_Clipping_Algorithm="SutherlandHodgman",
    Sky_Diffuse_Modeling_Algorithm="SimpleSkyDiffuseModeling",
    External_Shading_Calculation_Method="InternalCalculation",
    Output_External_Shading_Calculation_Results="No"  # TODO - Remove this for final version - this is used for exporting shade calucaltion for passing to TAS
)

print("SHADOWCALCULATION modified")

############################
# SET SCHEDULE TYPE LIMITS #
############################

idf.idfobjects["SCHEDULETYPELIMITS"] = []

idf.newidfobject(
    "SCHEDULETYPELIMITS",
    Name="FractionLimits",
    Lower_Limit_Value=0,
    Upper_Limit_Value=1,
    Numeric_Type="Continuous",
    Unit_Type="Dimensionless"
)

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

###############################################################################################################
# REMOVE DAILY INTERVAL PROFILES FROM THE IDF FOR CUSTOM REPLACEMENTS GENERATED FROM THE ZONE_CONDITIONS FILE #
###############################################################################################################

idf.idfobjects["SCHEDULE:DAY:INTERVAL"] = []

print("SCHEDULE:DAY:INTERVAL modified")

########################################################
# SET DAILY PROFILES FROM THE INTERNAL GAINS TEMPLATES #
########################################################

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
    TEMP["Hour_{0:}".format(i + 1)] = ZONE_CONDITIONS["occupant_sensible_gain_watts_per_person"]

print("SCHEDULE:DAY:HOURLY modified")

##################################
# REMOVE THE WEEK DAILY PROFILES #
##################################

idf.idfobjects["SCHEDULE:WEEK:DAILY"] = []

print("SCHEDULE:WEEK:DAILY modified")

###################################
# SET COMPACT WEEK DAILY PROFILES #
###################################

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

#######################
# SET ANNUAL PROFILES #
#######################

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

######################################
# SET THE PEOPLE GAINS FOR ALL ZONES #
######################################

idf.idfobjects["PEOPLE"] = []

idf.newidfobject(
    "PEOPLE",
    Name="PeopleGain",
    Zone_or_ZoneList_Name="AllZones",
    Number_of_People_Schedule_Name="OccupantGainYear",
    Number_of_People_Calculation_Method="Area/Person",
    Zone_Floor_Area_per_Person=ZONE_CONDITIONS["occupant_gain_m2_per_person"],
    Fraction_Radiant=0.3,
    Sensible_Heat_Fraction=float(
        ZONE_CONDITIONS["occupant_sensible_gain_watts_per_person"]) / float(
        sum([ZONE_CONDITIONS["occupant_sensible_gain_watts_per_person"],
            ZONE_CONDITIONS["occupant_latent_gain_watts_per_person"]])),
    Activity_Level_Schedule_Name="OccupantActivityLevelYear"
)

print("PEOPLE modified")

########################################
# SET THE LIGHTING GAINS FOR ALL ZONES #
########################################

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


#########################################
# SET THE EQUIPMENT GAINS FOR ALL ZONES #
#########################################

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

#####################################
# REMOVE INFILTRATION FOR ALL ZONES #
#####################################

# NOTE - This was done to enable a fixed level of infiltrtation to be added to the ventilation design flowrate

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

# print("ZONEINFILTRATION:DESIGNFLOWRATE modified")

print("ZONEINFILTRATION:DESIGNFLOWRATE modified")

##################################################
# SET VENTILATION AND INFILTRATION FOR ALL ZONES #
##################################################

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

##################################################################################
# SET HEATING AND COOLING SETPOINTS FROM PROFILE IN THE INTERNAL GAINS TEMPLATES #
##################################################################################

idf.idfobjects["HVACTEMPLATE:THERMOSTAT"] = []

for i in idf.idfobjects["ZONE"]:
    idf.newidfobject(
        "HVACTEMPLATE:THERMOSTAT",
        Name="{0:}_HVAC".format(i.Name),
        Heating_Setpoint_Schedule_Name="HeatingSetpointYear",
        Constant_Heating_Setpoint="",
        Cooling_Setpoint_Schedule_Name="CoolingSetpointYear",
        Constant_Cooling_Setpoint=""
    )

print("HVACTEMPLATE:THERMOSTAT modified")

######################################################################################
# SET IDEAL LOADS AIR SYSTEM AIR SUPPLY FROM PROFILE IN THE INTERNAL GAINS TEMPLATES #
######################################################################################

idf.idfobjects["HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM"] = []

for i in idf.idfobjects["ZONE"]:
    idf.newidfobject(
        "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
        Zone_Name=i.Name,
        Template_Thermostat_Name="{0:}_HVAC".format(i.Name),
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
        Outdoor_Air_Flow_Rate_per_Zone_Floor_Area=0.000227,
        Outdoor_Air_Flow_Rate_per_Zone="",
        Design_Specification_Outdoor_Air_Object_Name="{0:}_OutdoorAir".format(i.Name),
        Demand_Controlled_Ventilation_Type="",
        Outdoor_Air_Economizer_Type="NoEconomizer",
        Heat_Recovery_Type="None",
        Sensible_Heat_Recovery_Effectiveness="",
        Latent_Heat_Recovery_Effectiveness=""
    )

print("HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM modified")

############################################################
# REMOVE THE HVAC OBJECTS PROVIFING FRESH AIR FROM OUTSIDE #
############################################################

idf.idfobjects["DESIGNSPECIFICATION:OUTDOORAIR"] = []

for i in idf.idfobjects["ZONE"]:
    idf.newidfobject(
        "DESIGNSPECIFICATION:OUTDOORAIR",
        Name="{0:}_OutdoorAir".format(i.Name),
        Outdoor_Air_Method="Flow/Person",
        Outdoor_Air_Flow_per_Person=float(ZONE_CONDITIONS["ventilation_litres_per_second_per_person"]) / 1000,
        Outdoor_Air_Schedule_Name="VentilationYear"
    )

print("DESIGNSPECIFICATION:OUTDOORAIR modified")

####################################
# SET HVAC PLANT SIZING PARAMETERS #
####################################

idf.idfobjects["SIZING:PARAMETERS"] = []

idf.newidfobject(
    "SIZING:PARAMETERS",
    Heating_Sizing_Factor=1.25,
    Cooling_Sizing_Factor=1.15
)
print("SIZING:PARAMETERS modified")

#################################
#################################
## MATERIALS AND CONSTRUCTIONS ##
#################################
#################################

"""

The following section defines materials and constructions. Glazing is specified
using simplified single-layered constructions, wheras opaque building elements
are mul;ti-layered. A simple method of defining opaque materials is possible;
however, replicating thermal mass effects without that mass being present in
the simple massless single-layered method proved difficult.

"""

############################################
# REMOVE EXISTING WINDOW GLAZING MATERIALS #
############################################

idf.idfobjects["WINDOWMATERIAL:GLAZING"] = []

print("WINDOWMATERIAL:GLAZING objects modified")

########################################
# REMOVE EXISTING WINDOW GAS MATERIALS #
########################################

idf.idfobjects["WINDOWMATERIAL:GAS"] = []

print("WINDOWMATERIAL:GAS objects modified")

#################################################
# CREATE WINDOW MATERIAL SIMPLE GLAZING SYSTEMS #
#################################################

# TODO - Add different glazing configurations for different orientations (and elevation to account for skylights)

idf.idfobjects["WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM"] = []

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR WINDOW MATERIAL",
    UFactor=CONFIG["glass_u_value"],
    Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient"],
    Visible_Transmittance=CONFIG["glass_visible_transmittance"]
)

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR SKYLIGHT MATERIAL",
    UFactor=CONFIG["glass_u_value"],
    Solar_Heat_Gain_Coefficient=CONFIG["glass_solar_heat_gain_coefficient"],
    Visible_Transmittance=CONFIG["glass_visible_transmittance"]
)

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="INTERIOR WINDOW MATERIAL",
    UFactor=5.8,
    Solar_Heat_Gain_Coefficient=0.95,
    Visible_Transmittance=0.9
)

print("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM modified")

#################
# SET MATERIALS #
#################

idf.idfobjects["MATERIAL"] = []

# Interior wall materials

idf.newidfobject(
    "MATERIAL",
    Name="INTERIOR WALL OUTSIDE MATERIAL",
    Roughness="MediumSmooth",
    Thickness=0.019,
    Conductivity=0.16,
    Density=800,
    Specific_Heat=1090,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.4,
    Visible_Absorptance=1-CONFIG["wall_reflectivity"]
)

idf.newidfobject(
    "MATERIAL",
    Name="INTERIOR WALL MIDDLE MATERIAL",
    Roughness="MediumRough",
    Thickness=0.019,  # TODO - REPLACE THIS WITH A SENSIBLE VALUE FOR INTERIOR WALL U-VALUE
    Conductivity=0.16,
    Density=50,
    Specific_Heat=1030,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1.0
)

# Exterior wall materials
u_values = [5.0, 5.0, 1.7346938775510203, 1.6530612244897958, 1.631578947368421, 1.5714285714285714, 1.489795918367347, 1.4210526315789473, 1.4081632653061225, 1.3265306122448979, 1.2448979591836735, 1.2105263157894737, 1.163265306122449, 1.0816326530612246, 1.0, 0.965551724137931, 0.9311034482758621, 0.8966551724137931, 0.8622068965517241, 0.8277586206896551, 0.7933103448275862, 0.7588620689655172, 0.7244137931034482, 0.6899655172413793, 0.6555172413793103, 0.6210689655172413, 0.5866206896551724, 0.5521724137931034, 0.5177241379310344, 0.4832758620689655, 0.44882758620689656, 0.41437931034482756, 0.3799310344827586, 0.34548275862068967, 0.31103448275862067, 0.2765862068965517, 0.24213793103448275, 0.20768965517241378, 0.17324137931034483, 0.13879310344827586, 0.10434482758620689, 0.06989655172413793, 0.035448275862068966, 0.001]
insulation_thicknesses = [0.01946, 0.01974, 0.02066, 0.02168, 0.02196, 0.0228, 0.02404, 0.0252, 0.02543, 0.02699, 0.02875, 0.02956, 0.03075, 0.03306, 0.03573, 0.037, 0.03836, 0.03982, 0.0414, 0.0431, 0.04496, 0.04698, 0.04919, 0.05162, 0.0543, 0.05728, 0.0606, 0.06433, 0.06855, 0.07336, 0.0789, 0.08534, 0.09293, 0.102, 0.113, 0.1267, 0.1442, 0.1673, 0.1992, 0.2461, 0.322, 0.4654, 0.839, 4.255]
f = interpolate.interp1d(insulation_thicknesses, u_values)
if CONFIG["exterior_wall_u_value"] < 0.02:
    thickness = f(0.02)
elif CONFIG["exterior_wall_u_value"] > 4.0:
    thickness = f(4.0)
else:
    thickness = f(CONFIG["exterior_wall_u_value"])
print(thickness)

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR WALL OUTSIDE MATERIAL",
    Roughness="MediumSmooth",
    Thickness=0.1,
    Conductivity=1.13,
    Density=1800,
    Specific_Heat=1000,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1.0
)

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR WALL MIDDLE MATERIAL",
    Roughness="MediumRough",
    Thickness=thickness,
    Conductivity=0.036,
    Density=50,
    Specific_Heat=1030,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1.0
)

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR WALL INSIDE MATERIAL",
    Roughness="MediumSmooth",
    Thickness=0.019,
    Conductivity=0.16,
    Density=800,
    Specific_Heat=1090,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.4,
    Visible_Absorptance=1-CONFIG["wall_reflectivity"]
)

# Interior floor/ceiling materials

idf.newidfobject(
    "MATERIAL",
    Name="INTERIOR FLOOR/CEILING CEILING MATERIAL",
    Roughness="MediumSmooth",
    Thickness=0.0191,
    Conductivity=0.06,
    Density=368,
    Specific_Heat=590,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.3,
    Visible_Absorptance=1-CONFIG["ceiling_reflectivity"]
)

# idf.newidfobject(
#     "MATERIAL",
#     Name="INTERIOR FLOOR/CEILING MIDDLE MATERIAL",
#     Roughness="MediumRough",
#     Thickness=0.1,  # TODO - REPLACE THIS WITH SENSIBLE VALUE FOR INTERIOR FLOOR/CEILING U-VALUE
#     Conductivity=0.036,
#     Density=50,
#     Specific_Heat=1030,
#     Thermal_Absorptance=0.1,
#     Solar_Absorptance=0.7,
#     Visible_Absorptance=1.0
# )

idf.newidfobject(
    "MATERIAL",
    Name="INTERIOR FLOOR/CEILING FLOOR MATERIAL",
    Roughness="MediumRough",
    Thickness=0.1016,
    Conductivity=0.53,
    Density=1280,
    Specific_Heat=840,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.5,
    Visible_Absorptance=1-CONFIG["floor_reflectivity"]
)

# Exterior floor materials

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR FLOOR OUTSIDE MATERIAL",
    Roughness="MediumRough",
    Thickness=0.0508,
    Conductivity=0.03,
    Density=43,
    Specific_Heat=1210,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=0.7
)

# idf.newidfobject(
#     "MATERIAL",
#     Name="EXTERIOR FLOOR MIDDLE MATERIAL",
#     Roughness="MediumRough",
#     Thickness=0.2,  # TODO - REPLACE THIS WITH SENSIBLE VALUE FOR EXTERIOR FLOOR U-VALUE
#     Conductivity=0.036,
#     Density=50,
#     Specific_Heat=1030,
#     Thermal_Absorptance=0.1,
#     Solar_Absorptance=0.7,
#     Visible_Absorptance=1.0
# )

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR FLOOR INSIDE MATERIAL",
    Roughness="MediumRough",
    Thickness=0.2032,
    Conductivity=1.95,
    Density=2240,
    Specific_Heat=900,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1-CONFIG["floor_reflectivity"]
)

# Exterior roof materials

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR ROOF OUTSIDE MATERIAL",
    Roughness="MediumRough",
    Thickness=0.1,
    Conductivity=0.5,
    Density=1800,
    Specific_Heat=1000,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.5,
    Visible_Absorptance=0.5
)

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR ROOF MIDDLE MATERIAL",
    Roughness="MediumRough",
    Thickness=0.2,  # TODO - REPLACE THIS WITH MODIFIABLE VALUE FOR CUSTOM ROOF U-VALUE INPUT
    Conductivity=0.036,
    Density=50,
    Specific_Heat=1030,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=0.7
)

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR ROOF INSIDE MATERIAL",
    Roughness="MediumSmooth",
    Thickness=0.001,
    Conductivity=0.5,
    Density=250,
    Specific_Heat=1000,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.3,
    Visible_Absorptance=1-CONFIG["ceiling_reflectivity"]
)

# Air wall materials

idf.newidfobject(
    "MATERIAL",
    Name="AIR WALL MATERIAL",
    Roughness="Smooth",
    Thickness=0.002,
    Conductivity=0.0262,
    Density=1.225,
    Specific_Heat=1000,
    Thermal_Absorptance=0.001,
    Solar_Absorptance=0.001,
    Visible_Absorptance=0.001
)

print("MATERIAL modified")

#########################################
# MODIFY ANY EXISTING AIR GAP MATERIALS #
#########################################

idf.idfobjects["MATERIAL:AIRGAP"] = []

idf.newidfobject(
    "MATERIAL:AIRGAP",
    Name="INTERIOR FLOOR/CEILING MIDDLE MATERIAL",
    Thermal_Resistance=0.15
)

print("MATERIAL:AIRGAP modified")

#####################
# SET CONSTRICTIONS #
#####################

idf.idfobjects["CONSTRUCTION"] = []

print("CONSTRUCTION modified")


idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR WALL",
    Outside_Layer="INTERIOR WALL OUTSIDE MATERIAL",
    Layer_2="INTERIOR WALL MIDDLE MATERIAL",
    Layer_3="INTERIOR WALL OUTSIDE MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR WALL",
    Outside_Layer="EXTERIOR WALL OUTSIDE MATERIAL",
    Layer_2="EXTERIOR WALL MIDDLE MATERIAL",
    Layer_3="EXTERIOR WALL INSIDE MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR FLOOR",
    Outside_Layer="INTERIOR FLOOR/CEILING CEILING MATERIAL",
    Layer_2="INTERIOR FLOOR/CEILING MIDDLE MATERIAL",
    Layer_3="INTERIOR FLOOR/CEILING FLOOR MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR FLOOR",
    Outside_Layer="EXTERIOR FLOOR OUTSIDE MATERIAL",
    # Layer_2="EXTERIOR FLOOR MIDDLE MATERIAL",
    # Layer_3="EXTERIOR FLOOR INSIDE MATERIAL"
    Layer_2="EXTERIOR FLOOR INSIDE MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR CEILING",
    Outside_Layer="INTERIOR FLOOR/CEILING FLOOR MATERIAL",
    Layer_2="INTERIOR FLOOR/CEILING MIDDLE MATERIAL",
    Layer_3="INTERIOR FLOOR/CEILING CEILING MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR ROOF",
    Outside_Layer="EXTERIOR ROOF OUTSIDE MATERIAL",
    Layer_2="EXTERIOR ROOF MIDDLE MATERIAL",
    Layer_3="EXTERIOR ROOF INSIDE MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="AIR WALL",
    Outside_Layer="AIR WALL MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR WINDOW",
    Outside_Layer="EXTERIOR WINDOW MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR WINDOW",
    Outside_Layer="INTERIOR WINDOW MATERIAL"
)

################################################################
# SET A ZONE LIST FOR PASSING TO ZONE CONDITIONS CONFIGURATION #
################################################################

TEMP = idf.newidfobject("ZONELIST", Name="AllZones")

for i, j in enumerate([str(i.Name) for i in idf.idfobjects["ZONE"]]):
    TEMP["Zone_{0:}_Name".format(i + 1)] = j

print("ZONELIST modified")

#######################################################
# SET Output variables to report following simulation #
#######################################################

# NOTE - Lots of variables are commented out here - these are all the possible outputs, but we only really need the ones that aren't commented
OUTPUT_VARIABLES = [
    "Zone Air Relative Humidity",
    "Zone Air Temperature",
    "Zone Electric Equipment Total Heating Energy",
    "Zone Ideal Loads Outdoor Air Sensible Cooling Energy",
    "Zone Ideal Loads Outdoor Air Sensible Heating Energy",
    "Zone Lights Total Heating Energy",
    "Zone Mean Air Dewpoint Temperature",
    "Zone Mean Radiant Temperature",
    "Zone Mechanical Ventilation Current Density Volume Flow Rate",
    "Zone People Occupant Count",
    "Zone People Total Heating Energy",
    "Zone Thermostat Cooling Setpoint Temperature",
    "Zone Thermostat Heating Setpoint Temperature",
    "Zone Total Internal Total Heating Energy",
    "Zone Windows Total Transmitted Solar Radiation Energy",
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
    # "Zone Air System Sensible Cooling Energy",
    # "Zone Air System Sensible Cooling Rate",
    # "Zone Air System Sensible Heating Energy",
    # "Zone Air System Sensible Heating Rate",
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
    # "Zone Ideal Loads Outdoor Air Total Cooling Rate",
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
    # "Zone Lights Total Heating Rate",
    # "Zone Lights Visible Radiation Heating Energy",
    # "Zone Lights Visible Radiation Heating Rate",
    # "Zone Mean Air Humidity Ratio",
    # "Zone Mean Air Temperature",
    # "Zone Mechanical Ventilation Air Changes per Hour",
    # "Zone Mechanical Ventilation Cooling Load Decrease Energy",
    # "Zone Mechanical Ventilation Cooling Load Increase Due to Overheating Energy",
    # "Zone Mechanical Ventilation Cooling Load Increase Energy",
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
    # "Zone People Radiant Heating Energy",
    # "Zone People Radiant Heating Rate",
    # "Zone People Sensible Heating Energy",
    # "Zone People Sensible Heating Rate",
    # "Zone People Total Heating Rate",
    # "Zone Thermostat Air Temperature",
    # "Zone Thermostat Control Type",
    # "Zone Total Internal Convective Heating Energy",
    # "Zone Total Internal Convective Heating Rate",
    # "Zone Total Internal Latent Gain Energy",
    # "Zone Total Internal Latent Gain Rate",
    # "Zone Total Internal Radiant Heating Energy",
    # "Zone Total Internal Radiant Heating Rate",
    # "Zone Total Internal Total Heating Rate",
    # "Zone Total Internal Visible Radiation Heating Energy",
    # "Zone Total Internal Visible Radiation Heating Rate",
    # "Zone Windows Total Heat Gain Energy",
    # "Zone Windows Total Heat Gain Rate",
    # "Zone Windows Total Heat Loss Energy",
    # "Zone Windows Total Heat Loss Rate",
    # "Zone Windows Total Transmitted Solar Radiation Rate",
]


idf.idfobjects["OUTPUT:VARIABLE"] = []

for i in OUTPUT_VARIABLES:
    idf.newidfobject(
        "OUTPUT:VARIABLE",
        Key_Value="*",
        Variable_Name=i,
        Reporting_Frequency="hourly"
    )

print("OUTPUT:VARIABLE modified")

#######################################################################
# REMOVE SURFACE OUTPUT (TO SAVE ON SIMULATION TIME AND RESULTS SIZE) #
#######################################################################

idf.idfobjects["OUTPUT:SURFACES:LIST"] = []

print("OUTPUT:SURFACES:LIST modified")

###################################################################
# REMOVE TABLE STYLE OUTPUT TO SAVE ON TOTAL RESULTS FILES OUTPUT #
###################################################################

idf.idfobjects["OUTPUTCONTROL:TABLE:STYLE"] = []

print("OUTPUTCONTROL:TABLE:STYLE modified")

#####################################
# REMOVE OUTPUT VARIABLE DICTIONARY #
#####################################

idf.idfobjects["OUTPUT:VARIABLEDICTIONARY"] = []

print("OUTPUT:VARIABLEDICTIONARY modified")

#########################
# DIAGNOSTICS & TESTING #
#########################

"""
The following commands further modify the IDF file, to include certain aspects
necessary for debugging, or to output additional files from the simulation.null=

To run these uncomment the lines below
"""

idf.idfobjects["OUTPUT:VARIABLEDICTIONARY"] = []
idf.newidfobject("OUTPUT:VARIABLEDICTIONARY", Key_Field="regular")

idf.idfobjects["OUTPUT:CONSTRUCTIONS"] = []
idf.newidfobject("OUTPUT:CONSTRUCTIONS", Details_Type_1="Constructions")

idf.idfobjects["OUTPUT:SQLITE"] = []
idf.newidfobject("OUTPUT:SQLITE", Option_Type="Simple")

idf.idfobjects["OUTPUT:DIAGNOSTICS"] = []
idf.newidfobject("OUTPUT:DIAGNOSTICS", Key_1="DisplayExtraWarnings", Key_2="DisplayUnusedSchedules")

idf.idfobjects["OUTPUT:SURFACES:LIST"] = []
idf.newidfobject("OUTPUT:SURFACES:LIST", Report_Type="Details")

idf.idfobjects["OUTPUTCONTROL:TABLE:STYLE"] = []
idf.newidfobject("OUTPUTCONTROL:TABLE:STYLE", Column_Separator="Comma")

idf.idfobjects["OUTPUT:TABLE:SUMMARYREPORTS"] = []
idf.newidfobject("OUTPUT:TABLE:SUMMARYREPORTS", Report_1_Name="AllSummary")

idf.idfobjects["SHADING:BUILDING:DETAILED"] = []  # Remove shading elements

idf.idfobjects["SHADOWCALCULATION"] = []
idf.newidfobject(
    "SHADOWCALCULATION",
    Calculation_Method="AverageOverDaysInFrequency",
    Calculation_Frequency=20,
    Maximum_Figures_in_Shadow_Overlap_Calculations=15000,
    Polygon_Clipping_Algorithm="SutherlandHodgman",
    Sky_Diffuse_Modeling_Algorithm="SimpleSkyDiffuseModeling",
    External_Shading_Calculation_Method="InternalCalculation",
    Output_External_Shading_Calculation_Results="Yes"
)

##############################
# SAVE THE IDF AS A NEW FILE #
##############################

idf.saveas(IDF_FILEPATH.replace(".idf", "_modified.idf"))

print("\nIDF file modified and saved to {0:}".format(IDF_FILEPATH.replace(".idf", "_modified.idf")))
