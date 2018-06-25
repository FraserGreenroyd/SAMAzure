# TODO - Orient analysis grid to longest edge of zone it's being generated for
# TODO - Add radiance surface properties to HBSurfaces based on IDF properties/corresponding materials
# TODO - Create ability to visualise surfaces and analsyis grids in context
# TODO - Add radiance parameters to the config.json
# TODO - Add method interpreting results for SDA, DA, DF, UDI, UDILess, UDIMore

# Load necessary packages
import sys
sys.path.insert(0,'ladybug')
sys.path.insert(0,'honeybee')
from honeybee.hbsurface import HBSurface
from honeybee.hbfensurface import HBFenSurface
from honeybee.radiance.analysisgrid import AnalysisGrid
from honeybee.radiance.properties import RadianceProperties
from honeybee.radiance.material.glass import Glass
from honeybee.radiance.material.plastic import Plastic
import matplotlib.patches as patches
from honeybee.radiance.analysisgrid import AnalysisGrid
from honeybee.radiance.sky.skymatrix import SkyMatrix
from honeybee.radiance.recipe.daylightfactor.gridbased import GridBased as df_GridBased
from honeybee.radiance.recipe.annual.gridbased import GridBased as annual_GridBased

import eppy
from eppy import modeleditor
from eppy.modeleditor import IDF
import json
import numpy as np

def loadJSON(path):
    """
    Description:
        Load a JSON file into a dictionary object
    Arguments:
        path [string]: The location of the JSON file being loaded
    Returns:
        dictionary [dict]: Dictionary containing contents of loaded JSON file 
    """
    import json
    with open(path) as data_file:
        return json.load(data_file)

# Specify the config file to be referenced
config = loadJSON("idf_config.json")

# Run the LoadModifyIDF.py script
#import subprocess
#subprocess.call(["python", "LoadModifyIDF.py", idf_config_file])

idf_file = config["target_idf"]
idd_file = config["idd_file"]
epw_file = config["weather_file"]
IDF.setiddname(idd_file)
idf = IDF(idf_file)

# Set the "vector to north", so that wall orientation can be obtained
north_angle = np.radians(idf.idfobjects["BUILDING"][0].North_Axis)
north_vector = (np.sin(north_angle), np.cos(north_angle), 0)
def unit_vector(vector):
    """ Returns the unit vector of the vector.  """
    return vector / np.linalg.norm(vector)

def angle_between(v1, v2):
    """ Returns the angle in radians between vectors 'v1' and 'v2'::

            >>> angle_between((1, 0, 0), (0, 1, 0))
            1.5707963267948966
            >>> angle_between((1, 0, 0), (1, 0, 0))
            0.0
            >>> angle_between((1, 0, 0), (-1, 0, 0))
            3.141592653589793
    """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))

def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + np.cos(angle) * (px - ox) - np.sin(angle) * (py - oy)
    qy = oy + np.sin(angle) * (px - ox) + np.cos(angle) * (py - oy)
    return qx, qy

# List the zones to be analysed - I'm thinking this will come from GH initially
zones_to_analyse = config["analysis_zones"]

# Define materials to be applied to surfaces
glass_material_N = Glass("GlassMaterialN", r_transmittance=config["glazing_visible_transmittance_N"], g_transmittance=config["glazing_visible_transmittance_N"], b_transmittance=config["glazing_visible_transmittance_N"], refraction_index=1.52)
glass_material_S = Glass("GlassMaterialS", r_transmittance=config["glazing_visible_transmittance_S"], g_transmittance=config["glazing_visible_transmittance_S"], b_transmittance=config["glazing_visible_transmittance_S"], refraction_index=1.52)
glass_material_E = Glass("GlassMaterialE", r_transmittance=config["glazing_visible_transmittance_E"], g_transmittance=config["glazing_visible_transmittance_E"], b_transmittance=config["glazing_visible_transmittance_E"], refraction_index=1.52)
glass_material_W = Glass("GlassMaterialW", r_transmittance=config["glazing_visible_transmittance_W"], g_transmittance=config["glazing_visible_transmittance_W"], b_transmittance=config["glazing_visible_transmittance_W"], refraction_index=1.52)
glass_material_internal = Glass("GlassMaterialInternal", r_transmittance=0.9, g_transmittance=0.9, b_transmittance=0.9, refraction_index=1.52)
glass_material_skylight = Glass("GlassMaterialSkylight", r_transmittance=config["glazing_visible_transmittance_skylight"], g_transmittance=config["glazing_visible_transmittance_skylight"], b_transmittance=config["glazing_visible_transmittance_skylight"], refraction_index=1.52)

air_wall_material = Glass("AirWallMaterial", r_transmittance=0, g_transmittance=0, b_transmittance=0, refraction_index=1)
wall_material = Plastic("WallMaterial", r_reflectance=config["wall_reflectivity"], g_reflectance=config["wall_reflectivity"], b_reflectance=config["wall_reflectivity"], specularity=0, roughness=0)
ceiling_material = Plastic("CeilingMaterial", r_reflectance=config["ceiling_reflectivity"], g_reflectance=config["ceiling_reflectivity"], b_reflectance=config["ceiling_reflectivity"], specularity=0, roughness=0)
floor_material = Plastic("FloorMaterial", r_reflectance=config["floor_reflectivity"], g_reflectance=config["floor_reflectivity"], b_reflectance=config["floor_reflectivity"], specularity=0, roughness=0)

# Assign surfaces within IDF to HBSurfaces for daylight analysis
exterior_wall_surfaces = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if (i.Construction_Name == "Exterior Wall")]):
    srf = HBSurface("wall_{0:}_{1:}".format(wall_n, wall.Name), wall.coords, surface_type=0, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=wall_material))
    angle_to_north = np.degrees(angle_between(north_vector, srf.normal))
    for fenestration_n, fenestration in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if wall.Name in fenestration.Name:
            # Assign glazing properties based on orientation
            if (angle_to_north > 315) and (angle_to_north <= 45):
                orientation_glazing_material = glass_material_N
            elif (angle_to_north > 45) and (angle_to_north <= 135):
                orientation_glazing_material = glass_material_E
            elif (angle_to_north > 135) and (angle_to_north <= 225):
                orientation_glazing_material = glass_material_S
            elif (angle_to_north > 225) and (angle_to_north <= 315):
                orientation_glazing_material = glass_material_W
            fensrf = HBFenSurface("wall_{0:}_{1:}_fenestration_{2:}_{3:}".format(wall_n, wall.Name, fenestration_n, fenestration.Name), fenestration.coords, rad_properties=RadianceProperties(material=orientation_glazing_material))
            srf.add_fenestration_surface(fensrf)
    exterior_wall_surfaces.append(srf)

interior_wall_surfaces = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if (i.Construction_Name == "Interior Wall")]):
    srf = HBSurface("wall_{0:}_{1:}".format(wall_n, wall.Name), wall.coords, surface_type=0, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=wall_material))
    for fenestration_n, fenestration in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if wall.Name in fenestration.Name:
            fensrf = HBFenSurface("wall_{0:}_{1:}_fenestration_{2:}_{3:}".format(wall_n, wall.Name, fenestration_n, fenestration.Name), fenestration.coords, rad_properties=RadianceProperties(material=glass_material_internal))
            srf.add_fenestration_surface(fensrf)
    interior_wall_surfaces.append(srf)

airwall_surfaces = []
for airwall_n, airwall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if i.Construction_Name == "Air Wall"]):
    srf = HBSurface("airwall_{0:}_{1:}".format(airwall_n, airwall.Name), airwall.coords, surface_type=4, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=air_wall_material))
    airwall_surfaces.append(srf)

floor_surfaces = []
for floor_n, floor in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if (i.Construction_Name == "Interior Floor") or (i.Construction_Name == "Exterior Floor") or (i.Construction_Name == "Exposed Floor")]):
    srf = HBSurface("floor_{0:}_{1:}".format(floor_n, floor.Name), floor.coords, surface_type=2, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=floor_material))
    for fenestration_n, fenestration in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if floor.Name in fenestration.Name:
            fensrf = HBFenSurface("floor_{0:}_{1:}_fenestration_{2:}_{3:}".format(floor_n, floor.Name, fenestration_n, fenestration.Name), fenestration.coords, rad_properties=RadianceProperties(material=glass_material_interior))
            srf.add_fenestration_surface(fensrf)
    floor_surfaces.append(srf)
    
ceiling_surfaces = []
for ceiling_n, ceiling in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if (i.Construction_Name == "Interior Ceiling") or (i.Construction_Name == "Exterior Ceiling") or (i.Construction_Name == "Roof")]):
    srf = HBSurface("ceiling_{0:}_{1:}".format(ceiling_n, ceiling.Name), ceiling.coords, surface_type=3, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=ceiling_material))
    for fenestration_n, fenestration in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if ceiling.Name in fenestration.Name:
            fensrf = HBFenSurface("ceiling_{0:}_{1:}_fenestration_{2:}_{3:}".format(ceiling_n, ceiling.Name, fenestration_n, fenestration.Name), fenestration.coords, rad_properties=RadianceProperties(material=glass_material_skylight))
            srf.add_fenestration_surface(fensrf)
    ceiling_surfaces.append(srf)

context_surfaces = []
for context_n, context in enumerate([i for i in idf.idfobjects["SHADING:BUILDING:DETAILED"]]):
    srf = HBSurface("context_{0:}_{1:}".format(context_n, context.Name), context.coords, surface_type=6, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=wall_material))
    context_surfaces.append(srf)

# Define analysis grids for each zone for simulation in Radiance
zone_grids = []
for zone in zones_to_analyse:
    for floor_srf in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        if ("Floor" in floor_srf.Construction_Name) and (zone in floor_srf.Zone_Name):
            vert_xs, vert_ys, vert_zs = list(zip(*floor_srf.coords))
            patch = patches.Polygon(list(zip(*[vert_xs, vert_ys])))
            min_x, max_x, min_y, max_y, max_z = min(vert_xs), max(vert_xs), min(vert_ys), max(vert_ys), max(vert_zs)
            x_range = max_x - min_x
            y_range = max_y - min_y
            g = np.meshgrid(
                np.arange(min_x - (x_range / 2), max_x + (x_range / 2), config["daylight_analysis_grid_spacing"]), 
                np.arange(min_y - (y_range / 2), max_y + (y_range / 2), config["daylight_analysis_grid_spacing"])
            )
            coords = list(zip(*(c.flat for c in g)))
            analysispoints = np.vstack([p for p in coords if patch.contains_point(p, radius=config["daylight_analysis_grid_edge_offset"])])
            grid_points = list(zip(*[np.array(list(zip(*analysispoints)))[0], np.array(list(zip(*analysispoints)))[1], np.repeat(max_z+config["daylight_analysis_grid_surface_offset"], len(analysispoints))]))
            zone_grids.append(AnalysisGrid.from_points_and_vectors(grid_points, name=zone))

# Generate sky matrix for annual analysis
sky_matrix = SkyMatrix.from_epw_file(epw_file, sky_density=2, north=0, hoys=range(0, 8760), mode=0, suffix="")

# Generate a recipe for the DF and ANNUAL simulations (for all the rooms at once)
df_recipe = df_GridBased(analysis_grids=zone_grids, hb_objects=np.concatenate([exterior_wall_surfaces, interior_wall_surfaces, floor_surfaces, ceiling_surfaces, airwall_surfaces, context_surfaces]).tolist())
annual_recipe = annual_GridBased(sky_matrix, analysis_grids=zone_grids, hb_objects=np.concatenate([exterior_wall_surfaces, interior_wall_surfaces, floor_surfaces, ceiling_surfaces, airwall_surfaces, context_surfaces]).tolist()) # <<<<<< add modified raytrace parametrs

# Save the analysis recipe to file for later processing
df_recipe.write(config["output_directory"], project_name="DONOTRUN_ALLROOMS_DF")
annual_recipe.write(config["output_directory"], project_name="DONOTRUN_ALLROOMS_ANNUAL")