"""
Description:
    Load an IDF file and modify according to settings in a config file
    To run enter the command:
    python 00_ModifyIDF_FullConstructions.py <path to IDF for modification> <path to config JSON file>
Arguments:
    path [string]: JSON config file (and referenced zone_conditions_library within that config file)
Returns:
    idf file [file object]: Modified IDF file

Annotations:
    TODO - Fix the glazing solar heat gain assignment from the config file for different orientations
    TODO - Add option for ground temperature inclusion from the Weatherfile if these are available
"""

import argparse
import json
import sys

from eppy.modeleditor import IDF
from scipy import interpolate

##############################################
# Helper text to assist in running this file #
##############################################

parser = argparse.ArgumentParser(
    description='''Modify an IDF file generated using Grasshopper/Honeybee using a config file to specify fabric performance and space thermal profile data.''',
    epilog="""Best of luck!""")
parser.add_argument('source.idf', type=str, default=None, help='')
parser.add_argument('config.json', type=str, default=None, help='')
parser.add_argument('weatherfile.epw', type=str, default=None, help='')
parser.add_argument('output.idf', type=str, default=None, help='')
args = parser.parse_args()


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

idf_filepath = sys.argv[1]
config_filepath = sys.argv[2]
epw_filepath = sys.argv[3]
modified_idf_filepath = sys.argv[4]

with open(config_filepath, "r") as f:
    config = json.load(f)

print("\nConfig loaded from {0:}\n".format(config_filepath))

if "win" in sys.platform.lower() and "dar" not in sys.platform.lower():
    IDF.setiddname("C:/EnergyPlusV8-8-0/Energy+.idd")
elif "dar" in sys.platform.lower():
    IDF.setiddname("/Applications/EnergyPlus-8-8-0/Energy+.idd")
elif "lin" in sys.platform.lower():
    IDF.setiddname("idd_location")  # TODO - This will break - I need to find where linux installs the IDD and amend

#########################################################################
# LOAD THE EPW SPECIFIED IN THE CONFIG FILE AND ASSIGN IDF TO IDFOBJECT #
#########################################################################

idf = IDF(idf_filepath)

print("IDF loaded from {0:}\n".format(idf_filepath))
print("EPW loaded from {0:}\n".format(epw_filepath))

####################################################################################
# LOAD THE JSON SPECIFIED IN THE CONFIG FILE THAT CONTAINS ZONE PROFILES AND GAINS #
####################################################################################

zone_conditions = load_json(config["zone_conditions_library"])[config["zone_template"]]

print("Zone conditions loaded from {1:}\nZone conditions set to {0:}\n".format(config["zone_template"],
                                                                               config["zone_conditions_library"]))

#######################################################################
# MODIFY IDF SITE INFORMATION USING DATA FROM THE REFERENCED EPW FILE #
#######################################################################

with open(epw_filepath, "r") as f:
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
    Output_External_Shading_Calculation_Results="No"
    # TODO - Remove this for final version - this is used for exporting shade calucaltion for passing to TAS
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
# REMOVE DAILY INTERVAL PROFILES FROM THE IDF FOR CUSTOM REPLACEMENTS GENERATED FROM THE zone_conditions FILE #
###############################################################################################################

idf.idfobjects["SCHEDULE:DAY:INTERVAL"] = []

print("SCHEDULE:DAY:INTERVAL modified")

########################################################
# SET DAILY PROFILES FROM THE INTERNAL GAINS TEMPLATES #
########################################################

idf.idfobjects["SCHEDULE:DAY:HOURLY"] = []

# Set a daily Always On profile

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="AlwaysOnDay",
    Schedule_Type_Limits_Name="OnOffLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = 1

# Set a daily Always Off profile

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="AlwaysOffDay",
    Schedule_Type_Limits_Name="OnOffLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = 0

# Set daily cooling profile from JSON

setpoint = zone_conditions["cooling_setpoint"]
setback = zone_conditions["cooling_setback"]

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="CoolingSetpointDayWeekday",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = setpoint if zone_conditions[
                                                      "cooling_setpoint_weekday"
                                                  ]["Hour_{0:}".format(i + 1)] != 0 else setback

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="CoolingSetpointDayWeekend",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = setpoint if zone_conditions[
                                                      "cooling_setpoint_weekend"
                                                  ]["Hour_{0:}".format(i + 1)] != 0 else setback

# Set daily heating profile from JSON

setpoint = zone_conditions["heating_setpoint"]
setback = zone_conditions["heating_setback"]

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="HeatingSetpointDayWeekday",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = setpoint if zone_conditions[
                                                      "heating_setpoint_weekday"
                                                  ]["Hour_{0:}".format(i + 1)] != 0 else setback

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="HeatingSetpointDayWeekend",
    Schedule_Type_Limits_Name="TemperatureSetpointLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = setpoint if zone_conditions[
                                                      "heating_setpoint_weekend"
                                                  ]["Hour_{0:}".format(i + 1)] != 0 else setback

# Set a daily Occupant profile

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="OccupantGainDayWeekday",
    Schedule_Type_Limits_Name="FractionLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions[
        "occupant_profile_weekday"
    ]["Hour_{0:}".format(i + 1)]

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="OccupantGainDayWeekend",
    Schedule_Type_Limits_Name="FractionLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions[
        "occupant_profile_weekend"
    ]["Hour_{0:}".format(i + 1)]

# Set a daily Lighting profile

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="LightingGainDayWeekday",
    Schedule_Type_Limits_Name="FractionLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions[
        "lighting_profile_weekday"
    ]["Hour_{0:}".format(i + 1)]

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="LightingGainDayWeekend",
    Schedule_Type_Limits_Name="FractionLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions[
        "lighting_profile_weekend"
    ]["Hour_{0:}".format(i + 1)]

# Set a daily Equipment profile

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="EquipmentGainDayWeekday",
    Schedule_Type_Limits_Name="FractionLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions[
        "equipment_profile_weekday"
    ]["Hour_{0:}".format(i + 1)]

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="EquipmentGainDayWeekend",
    Schedule_Type_Limits_Name="FractionLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions[
        "equipment_profile_weekend"
    ]["Hour_{0:}".format(i + 1)]

# Set a daily Ventilation profile

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="VentilationGainDayWeekday",
    Schedule_Type_Limits_Name="FractionLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions[
        "ventilation_profile_weekday"
    ]["Hour_{0:}".format(i + 1)]

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="VentilationGainDayWeekend",
    Schedule_Type_Limits_Name="FractionLimits"
)

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions[
        "ventilation_profile_weekend"
    ]["Hour_{0:}".format(i + 1)]

# Set a daily occupant activity level profile

temp = idf.newidfobject(
    "SCHEDULE:DAY:HOURLY",
    Name="OccupantActivityLevelDay",
    Schedule_Type_Limits_Name="ActivityLevelLimits")

for i in range(24):
    temp["Hour_{0:}".format(i + 1)] = zone_conditions["occupant_sensible_gain_watts_per_person"]

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
    Zone_Floor_Area_per_Person=zone_conditions["occupant_gain_m2_per_person"],
    Fraction_Radiant=0.3,
    Sensible_Heat_Fraction=float(
        zone_conditions["occupant_sensible_gain_watts_per_person"]) / float(
        sum([zone_conditions["occupant_sensible_gain_watts_per_person"],
             zone_conditions["occupant_latent_gain_watts_per_person"]])),
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
    Watts_per_Zone_Floor_Area=zone_conditions["lighting_gain_watts_per_m2"],
    Fraction_Radiant=0.5,
    Fraction_Visible=0.5,
    Lighting_Level=zone_conditions["design_illuminance_lux"]
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
    Watts_per_Zone_Floor_Area=zone_conditions["equipment_gain_watts_per_m2"],
    Fraction_Radiant=0.85,
    Fraction_Latent=0.15,
    Fraction_Lost=0
)

print("ELECTRICEQUIPMENT modified")

#####################################
# REMOVE INFILTRATION FOR ALL ZONES #
#####################################

# NOTE - This was done to enable a fixed level of infiltration to be added to the ventilation design flow-rate

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
    Flow_Rate_per_Person=float(zone_conditions["ventilation_litres_per_second_per_person"]) / 1000,
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
        # Maximum_Heating_Supply_Air_Temperature=18,
        # Minimum_Cooling_Supply_Air_Temperature=18,
        Maximum_Heating_Supply_Air_Humidity_Ratio=0.0156,
        Minimum_Cooling_Supply_Air_Humidity_Ratio=0.0077,
        # Maximum_Heating_Supply_Air_Humidity_Ratio=0.0135,
        # Minimum_Cooling_Supply_Air_Humidity_Ratio=0.0135,
        Heating_Limit="",
        Maximum_Heating_Air_Flow_Rate="",
        Maximum_Sensible_Heating_Capacity="",
        Cooling_Limit="NoLimit",
        Maximum_Cooling_Air_Flow_Rate="",
        Maximum_Total_Cooling_Capacity="",
        Heating_Availability_Schedule_Name="",
        Cooling_Availability_Schedule_Name="",
        Dehumidification_Control_Type="None",
        Cooling_Sensible_Heat_Ratio="",
        Dehumidification_Setpoint="",
        Humidification_Control_Type="None",
        Humidification_Setpoint="",
        # Outdoor_Air_Method="DetailedSpecification",
        Outdoor_Air_Method="Sum",
        # Outdoor_Air_Flow_Rate_per_Person="",
        Outdoor_Air_Flow_Rate_per_Person=0.015,
        Outdoor_Air_Flow_Rate_per_Zone_Floor_Area=0.000227,
        Outdoor_Air_Flow_Rate_per_Zone="",
        # Design_Specification_Outdoor_Air_Object_Name="{0:}_OutdoorAir".format(i.Name),
        Design_Specification_Outdoor_Air_Object_Name="",
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

# for i in idf.idfobjects["ZONE"]:
#     idf.newidfobject(
#         "DESIGNSPECIFICATION:OUTDOORAIR",
#         Name="{0:}_OutdoorAir".format(i.Name),
#         Outdoor_Air_Method="Flow/Person",
#         Outdoor_Air_Flow_per_Person=float(zone_conditions["ventilation_litres_per_second_per_person"]) / 1000,
#         Outdoor_Air_Schedule_Name="VentilationYear"
#     )

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
using simplified single-layered constructions, whereas opaque building elements
are multi-layered. A simple method of defining opaque materials is possible;
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

sghc_values = [0.05, 0.09736842105263158, 0.14473684210526316, 0.19210526315789472, 0.23947368421052628,
               0.28684210526315784, 0.33421052631578946, 0.381578947368421, 0.4289473684210526, 0.47631578947368414,
               0.5236842105263158, 0.5710526315789474, 0.618421052631579, 0.6657894736842105, 0.7131578947368421,
               0.7605263157894736, 0.8078947368421052, 0.8552631578947368, 0.9026315789473683, 0.95]

g_values = [0.02057, 0.04006, 0.05954, 0.104, 0.151, 0.199, 0.247, 0.296, 0.345, 0.394, 0.444, 0.494, 0.545, 0.596,
            0.647, 0.699, 0.751, 0.803, 0.856, 0.91]

f = interpolate.interp1d(g_values, sghc_values)

idf.idfobjects["WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM"] = []

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR WINDOW MATERIAL",
    UFactor=config["glass_u_value"],
    Solar_Heat_Gain_Coefficient=f(config["glass_g_value"]),
    Visible_Transmittance=config["glass_visible_transmittance"]
)

idf.newidfobject(
    "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
    Name="EXTERIOR SKYLIGHT MATERIAL",
    UFactor=config["glass_u_value"],
    Solar_Heat_Gain_Coefficient=f(config["glass_g_value"]),
    Visible_Transmittance=config["glass_visible_transmittance"]
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

"""

To generate materials that when combined define a construction of specified
U-Value, the following values have been used for resultant U-Values and
corresponding insulation thicknesses. As each Exterior Wall, Exterior Floor
and Exterior Roof construction are comprised of three materials, their Inside
and Outside layers are the same across each construction (with the exception
of their reflective characteristics) and only the middle Insulation layer is
modified. As such, the same value interpolation can be applied to each
construction type.

"""

# Interpolation for Custom U-Value assignment

u_values = [5.0, 1.7346938775510203, 1.6530612244897958, 1.5714285714285714, 1.489795918367347, 1.4081632653061225,
            1.3265306122448979, 1.2448979591836735, 1.163265306122449, 1.0816326530612246, 1.0, 0.9855217391304348,
            0.9710434782608696, 0.9565652173913044, 0.9420869565217392, 0.927608695652174, 0.9131304347826087,
            0.8986521739130435, 0.8841739130434784, 0.8696956521739131, 0.8552173913043478, 0.8407391304347827,
            0.8262608695652175, 0.8117826086956522, 0.797304347826087, 0.7828260869565218, 0.7683478260869566,
            0.7538695652173913, 0.7393913043478261, 0.7249130434782609, 0.7104347826086957, 0.6959565217391305,
            0.6814782608695652, 0.667, 0.6525217391304349, 0.6380434782608696, 0.6235652173913043, 0.6090869565217392,
            0.594608695652174, 0.5801304347826087, 0.5656521739130435, 0.5511739130434783, 0.5366956521739131,
            0.5222173913043479, 0.5077391304347826, 0.4932608695652174, 0.4787826086956522, 0.464304347826087,
            0.44982608695652176, 0.43534782608695655, 0.42086956521739133, 0.4063913043478261, 0.3919130434782609,
            0.3774347826086957, 0.36295652173913046, 0.34847826086956524, 0.334, 0.3195217391304348, 0.3050434782608696,
            0.29056521739130436, 0.27608695652173915, 0.26160869565217393, 0.2471304347826087, 0.2326521739130435,
            0.21817391304347827, 0.20369565217391306, 0.18921739130434784, 0.17473913043478262, 0.1602608695652174,
            0.14578260869565218, 0.13130434782608696, 0.11682608695652175, 0.10234782608695653, 0.08786956521739131,
            0.07339130434782609, 0.058913043478260874, 0.044434782608695655, 0.029956521739130437, 0.015478260869565219,
            0.001]

insulation_thicknesses = [0.01982, 0.02075, 0.02178, 0.02291, 0.02416, 0.02556, 0.02714, 0.02891, 0.03094, 0.03328,
                          0.03599, 0.03652, 0.03707, 0.03763, 0.03821, 0.0388, 0.03942, 0.04005, 0.04071, 0.04139,
                          0.04209, 0.04281, 0.04356, 0.04434, 0.04514, 0.04598, 0.04685, 0.04774, 0.04868, 0.04965,
                          0.05066, 0.05172, 0.05282, 0.05396, 0.05516, 0.05641, 0.05772, 0.05909, 0.06053, 0.06204,
                          0.06363, 0.0653, 0.06706, 0.06892, 0.07088, 0.07296, 0.07517, 0.07751, 0.08001, 0.08267,
                          0.08551, 0.08855, 0.09182, 0.09534, 0.09915, 0.1033, 0.1077, 0.1126, 0.118, 0.1238, 0.1303,
                          0.1375, 0.1456, 0.1546, 0.1649, 0.1766, 0.1901, 0.2059, 0.2244, 0.2467, 0.2739, 0.3078,
                          0.3512, 0.409, 0.4896, 0.6096, 0.8076, 1.196, 2.304, 31.47]

f = interpolate.interp1d(u_values, insulation_thicknesses)

if config["exterior_wall_u_value"] > 1.5:
    print(
        "WARNING - Your wall U-Value might fall outside interpolatable limits for this script. The actual value will likely be lower than expected")
if config["exterior_floor_u_value"] > 1.5:
    print(
        "WARNING - Your floor U-Value might fall outside interpolatable limits for this script. The actual value will likely be lower than expected")
if config["exterior_roof_u_value"] > 1.5:
    print(
        "WARNING - Your roof U-Value might fall outside interpolatable limits for this script. The actual value will likely be lower than expected")

# Interior wall materials

idf.idfobjects["MATERIAL"] = []

idf.newidfobject(
    "MATERIAL",
    Name="INTERIOR WALL OUTSIDE MATERIAL",
    Roughness="MediumSmooth",
    Thickness=0.1,
    Conductivity=0.1,
    Density=800,
    Specific_Heat=1090,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.4,
    Visible_Absorptance=1 - config["wall_reflectivity"]
)

# idf.newidfobject(
#     "MATERIAL",
#     Name="INTERIOR WALL MIDDLE MATERIAL",
#     Roughness="MediumRough",
#     Thickness=0.019,
#     Conductivity=0.16,
#     Density=50,
#     Specific_Heat=1030,
#     Thermal_Absorptance=0.1,
#     Solar_Absorptance=0.7,
#     Visible_Absorptance=1.0
# )

# Exterior wall materials

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR WALL OUTSIDE MATERIAL",
    Roughness="MediumSmooth",
    Thickness=0.01,
    Conductivity=5.0,
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
    Thickness=f(1.5) if config["exterior_wall_u_value"] > 1.5 else f(0.1) if config[
                                                                                 "exterior_wall_u_value"] < 0.1 else f(
        config["exterior_wall_u_value"]),
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
    Thickness=0.01,
    Conductivity=5.0,
    Density=800,
    Specific_Heat=1090,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.4,
    Visible_Absorptance=1 - config["wall_reflectivity"]
)

# Interior floor/ceiling materials

idf.newidfobject(
    "MATERIAL",
    Name="INTERIOR FLOOR/CEILING CEILING MATERIAL",
    Roughness="MediumSmooth",
    Thickness=0.1,
    Conductivity=0.2,
    Density=368,
    Specific_Heat=590,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.3,
    Visible_Absorptance=1 - config["ceiling_reflectivity"]
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
    Thickness=0.1,
    Conductivity=0.2,
    Density=1280,
    Specific_Heat=840,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.5,
    Visible_Absorptance=1 - config["floor_reflectivity"]
)

# Exterior floor materials

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR FLOOR OUTSIDE MATERIAL",
    Roughness="MediumRough",
    Thickness=0.01,
    Conductivity=5,
    Density=1000,
    Specific_Heat=1210,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=0.7
)

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR FLOOR MIDDLE MATERIAL",
    Roughness="MediumRough",
    Thickness=f(1.5) if config["exterior_floor_u_value"] > 1.5 else f(0.1) if config[
                                                                                  "exterior_floor_u_value"] < 0.1 else f(
        config["exterior_floor_u_value"]),
    Conductivity=0.036,
    Density=700,
    Specific_Heat=1030,
    Thermal_Absorptance=0.1,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1.0
)

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR FLOOR INSIDE MATERIAL",
    Roughness="MediumRough",
    Thickness=0.01,
    Conductivity=5,
    Density=2240,
    Specific_Heat=900,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=1 - config["floor_reflectivity"]
)

# Exterior roof materials

idf.newidfobject(
    "MATERIAL",
    Name="EXTERIOR ROOF OUTSIDE MATERIAL",
    Roughness="MediumRough",
    Thickness=0.01,
    Conductivity=5,
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
    Thickness=f(1.5) if config["exterior_roof_u_value"] > 1.5 else f(0.1) if config[
                                                                                 "exterior_roof_u_value"] < 0.1 else f(
        config["exterior_roof_u_value"]),
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
    Thickness=0.01,
    Conductivity=5,
    Density=250,
    Specific_Heat=1000,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.3,
    Visible_Absorptance=1 - config["ceiling_reflectivity"]
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
    # Layer_2="INTERIOR WALL MIDDLE MATERIAL",
    # Layer_3="INTERIOR WALL OUTSIDE MATERIAL"
    Layer_2="INTERIOR WALL OUTSIDE MATERIAL"
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
    # Layer_2="INTERIOR FLOOR/CEILING MIDDLE MATERIAL",
    # Layer_3="INTERIOR FLOOR/CEILING FLOOR MATERIAL"
    Layer_2="INTERIOR FLOOR/CEILING FLOOR MATERIAL"

)

idf.newidfobject(
    "CONSTRUCTION",
    Name="EXTERIOR FLOOR",
    Outside_Layer="EXTERIOR FLOOR OUTSIDE MATERIAL",
    Layer_2="EXTERIOR FLOOR MIDDLE MATERIAL",
    Layer_3="EXTERIOR FLOOR INSIDE MATERIAL"
)

idf.newidfobject(
    "CONSTRUCTION",
    Name="INTERIOR CEILING",
    Outside_Layer="INTERIOR FLOOR/CEILING FLOOR MATERIAL",
    # Layer_2="INTERIOR FLOOR/CEILING MIDDLE MATERIAL",
    # Layer_3="INTERIOR FLOOR/CEILING CEILING MATERIAL"
    Layer_2="INTERIOR FLOOR/CEILING CEILING MATERIAL"
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

idf.idfobjects["ZONELIST"] = []

temp = idf.newidfobject("ZONELIST", Name="AllZones")

for i, j in enumerate([str(i.Name) for i in idf.idfobjects["ZONE"]]):
    temp["Zone_{0:}_Name".format(i + 1)] = j

print("ZONELIST modified")

#######################################################
# SET Output variables to report following simulation #
#######################################################

# NOTE - Lots of variables are commented out here - these are all the possible outputs, but we only really need the ones that aren't commented
output_variables = [
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
    "Zone Ideal Loads Zone Total Cooling Energy",
    # "Zone Ideal Loads Zone Total Cooling Rate",
    "Zone Ideal Loads Zone Total Heating Energy",
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

for i in output_variables:
    idf.newidfobject(
        "OUTPUT:VARIABLE",
        Key_Value="*",
        Variable_Name=i,
        Reporting_Frequency="Timestep"
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
necessary for debugging, or to output additional files from the simulation.

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

# idf.idfobjects["SHADING:BUILDING:DETAILED"] = []  # Remove shading elements

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
idf.saveas(modified_idf_filepath)

print("\nIDF file modified and saved to {0:}".format(modified_idf_filepath))
