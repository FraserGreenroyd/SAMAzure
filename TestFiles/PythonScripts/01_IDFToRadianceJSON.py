"""
Description:
    Load an IDF file and generate the input/s for a Radiance simulation via Honeybee
    To run enter the command:
    python 01_IDFToRadianceJSON.py <path to IDF to run> <path to config JSON file>
Arguments:
    path [string]: JSON config file (and referenced IDF within that config file)
Returns:
    Radiance simulation recipe/s [file objects]: Radiance simulation input/s

Annotations:
    TODO - Orient analysis grid to longest edge of zone it's being generated for
    TODO - Create ability to visualise surfaces and analsyis grids in context
    TODO - Add radiance parameters to the config.json to put into the generated recipes
    TODO - Add method interpreting results for SDA, DA, DF, UDI, UDILess, UDIMore
    TODO - Check the fenestration surface normal is point teh right direction for correct window angle for G value assignment
"""

# Load necessary packages
import os
from eppy.modeleditor import IDF
import json
import numpy as np
import platform
import matplotlib.patches as patches
from scipy.spatial import Delaunay
import sys
sys.path.insert(0, 'ladybug')
sys.path.insert(0, 'honeybee')

from honeybee.hbsurface import HBSurface
# from honeybee.hbfensurface import HBFenSurface
from honeybee.radiance.analysisgrid import AnalysisGrid
from honeybee.radiance.material.glass import Glass
from honeybee.radiance.material.plastic import Plastic
from honeybee.radiance.properties import RadianceProperties
# from honeybee.radiance.recipe.daylightfactor.gridbased import GridBased as GridBasedDF
# from honeybee.radiance.recipe.annual.gridbased import GridBased as GridBasedAnnual
from honeybee.radiance.sky.skymatrix import SkyMatrix


def unit_vector(start, end):
    """
    Description:
        Get the orthogonal unit vector between two points
    Arguments:
        start [array]: X, Y, Z coordinate of start point
        end [array]: X, Y, Z coordinate of end point
    Returns:
        unit_vector [array]: X, Y, Z unit vector
    """
    pt_distance = np.array(end) - np.array(start)
    vector = pt_distance / np.sqrt(np.sum(pt_distance * pt_distance))
    return vector


def surface_normal(points, flip=False):
    """
    Description:
        Given 3 points from a surface, return the surface normal
    Arguments:
        points [array]: List of 3 XYZ points
        flip [bool]: Reverse the unit vector
    Returns:
        x, y, z [array]: Unit vector
    """
    U = np.array(points[1]) - np.array(points[0])
    V = np.array(points[2]) - np.array(points[0])
    Nx = U[1]*V[2] - U[2]*V[1]
    Ny = U[2]*V[0] - U[0]*V[2]
    Nz = U[0]*V[1] - U[1]*V[0]
    mag = np.sqrt(Nx**2 + Ny**2 + Nz**2)

    if flip:
        return (np.array([Nx, Ny, Nz]) / mag).tolist()
    else:
        return (-np.array([Nx, Ny, Nz]) / mag).tolist()


def translated_point(uv, uw, origin, point):
    """
    Description:
        Translates a 3D point into a 2D point
    Arguments:
        uv [array]: Unit vector for x direction of 2D plane
        uw [array]: Unit vector for y direction of 2D plane
        origin [array]: Base point of 2D plane
        point [array]: X, Y, Z point to be translated
    Returns:
        x, y [array]: Point translated onto 2D coordinate plane
    """
    x = (point[0] - origin[0]) * uv[0] + (point[1] - origin[1]) * uv[1] + (point[2] - origin[2]) * uv[2]
    y = (point[0] - origin[0]) * uw[0] + (point[1] - origin[1]) * uw[1] + (point[2] - origin[2]) * uw[2]
    return x, y


def untranslated_point(uv, uw, origin, point):
    """
    Description:
        Translates a 3D point into a 2D point
    Arguments:
        uv [array]: Unit vector for x direction of 2D plane
        uw [array]: Unit vector for y direction of 2D plane
        origin [array]: Base point of 2D plane
        point [array]: X, Y, Z point to be translated
    Returns:
        x, y, z [array]: Point translated from 2D to 3D coordinate plane
    """
    x = origin[0] + uv[0] * point[0] + uw[0] * point[1]
    y = origin[1] + uv[1] * point[0] + uw[1] * point[1]
    z = origin[2] + uv[2] * point[0] + uw[2] * point[1]
    return x, y, z


def triangulate_3d_surfaces(parent_surface_vertices, child_surfaces_vertices):
    """
    Description:
        Given a planar surface defined by vertices, and coplanar child surfaces
        returns a set of surfaces descriing the parent surface, without the
        child surfaces.
    Arguments:
        parent_surface_vertices [array]: List of parent surface vertices
        child_surfaces_vertices [array]: Nested list of child surface vertices
    Returns:
        triangulated_surface_vertices [array]: Nested list of triangulated surface
        vertices
    """
    uv = unit_vector(parent_surface_vertices[0], parent_surface_vertices[1])
    uw = unit_vector(parent_surface_vertices[0], parent_surface_vertices[3])

    parent_surface_vertices_translated = np.array([translated_point(uv, uw, parent_surface_vertices[0], i) for i in parent_surface_vertices])
    child_surfaces_vertices_translated = np.array([[translated_point(uv, uw, parent_surface_vertices[0], i) for i in ch] for ch in child_surfaces_vertices])

    parent_points = parent_surface_vertices_translated
    child_points = [item for sublist in child_surfaces_vertices_translated for item in sublist]

    points = np.concatenate([parent_points, child_points])
    tri = Delaunay(points).simplices.copy()

    mask = []
    for face_pts in points[tri]:
        n = []
        for child_pts in child_surfaces_vertices_translated:
            n.append(len(np.array([x for x in set(tuple(x) for x in face_pts) & set(tuple(x) for x in child_pts)])))
        if 3 in n:
            mask.append(False)
        else:
            mask.append(True)

    triangulated_surface_vertices = []
    for i in points[tri][mask]:
        mm = []
        for j in i:
            mm.append(untranslated_point(uv, uw, parent_surface_vertices[0], j))
        triangulated_surface_vertices.append(mm)

    return np.array(triangulated_surface_vertices)


def unit_vector2(vector):
    """
    Description:
        Returns the unit vector of a vector
    Arguments:
        vector [1D-array]: Vector defined as [n.n, n.n, n.n]
    Returns:
        vector [1D-array]: Dictionary containing contents of loaded JSON file
    """
    return vector / np.linalg.norm(vector)


def angle_between(vector_1, vector_2):
    """
    Returns the angle in radians between vectors 'vector_1' and 'vector_2'
            >>> angle_between((1, 0, 0), (0, 1, 0))
            1.5707963267948966
            >>> angle_between((1, 0, 0), (1, 0, 0))
            0.0
            >>> angle_between((1, 0, 0), (-1, 0, 0))
            3.141592653589793
    """
    vector_1_u = unit_vector2(vector_1)
    vector_2_u = unit_vector2(vector_2)
    return np.arccos(np.clip(np.dot(vector_1_u, vector_2_u), -1.0, 1.0))


def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    o_x, o_y = origin
    p_x, p_y = point

    q_x = o_x + np.cos(angle) * (p_x - o_x) - np.sin(angle) * (p_y - o_y)
    q_y = o_y + np.sin(angle) * (p_x - o_x) + np.cos(angle) * (p_y - o_y)
    return q_x, q_y


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

# Set the "vector to north", so that wall orientation can be obtained
north_angle_deg = idf.idfobjects["BUILDING"][0].North_Axis
north_angle = np.radians(north_angle_deg)
north_vector = (np.sin(north_angle), np.cos(north_angle), 0)
print("North angle has been read as {0:}\n".format(north_angle))

# Define materials to be applied to surfaces
glass_material_N = Glass(
    "GlassMaterialN",
    r_transmittance=CONFIG["glass_visible_transmittance_N"],
    g_transmittance=CONFIG["glass_visible_transmittance_N"],
    b_transmittance=CONFIG["glass_visible_transmittance_N"],
    refraction_index=1.52
    )

glass_material_S = Glass(
    "GlassMaterialS",
    r_transmittance=CONFIG["glass_visible_transmittance_S"],
    g_transmittance=CONFIG["glass_visible_transmittance_S"],
    b_transmittance=CONFIG["glass_visible_transmittance_S"],
    refraction_index=1.52
)

glass_material_E = Glass(
    "GlassMaterialE",
    r_transmittance=CONFIG["glass_visible_transmittance_E"],
    g_transmittance=CONFIG["glass_visible_transmittance_E"],
    b_transmittance=CONFIG["glass_visible_transmittance_E"],
    refraction_index=1.52
)

glass_material_W = Glass(
    "GlassMaterialW",
    r_transmittance=CONFIG["glass_visible_transmittance_W"],
    g_transmittance=CONFIG["glass_visible_transmittance_W"],
    b_transmittance=CONFIG["glass_visible_transmittance_W"],
    refraction_index=1.52
)

glass_material_interior = Glass(
    "GlassMaterialInternal",
    r_transmittance=0.9, g_transmittance=0.9, b_transmittance=0.9, refraction_index=1.52
)

glass_material_skylight = Glass(
    "GlassMaterialSkylight",
    r_transmittance=CONFIG["glass_visible_transmittance_skylight"],
    g_transmittance=CONFIG["glass_visible_transmittance_skylight"],
    b_transmittance=CONFIG["glass_visible_transmittance_skylight"],
    refraction_index=1.52
)

air_wall_material = Glass(
    "AirWallMaterial",
    r_transmittance=0, g_transmittance=0, b_transmittance=0, refraction_index=1
)

wall_material = Plastic(
    "WallMaterial",
    r_reflectance=CONFIG["wall_reflectivity"],
    g_reflectance=CONFIG["wall_reflectivity"],
    b_reflectance=CONFIG["wall_reflectivity"],
    specularity=0, roughness=0
)

ceiling_material = Plastic(
    "CeilingMaterial",
    r_reflectance=CONFIG["ceiling_reflectivity"],
    g_reflectance=CONFIG["ceiling_reflectivity"],
    b_reflectance=CONFIG["ceiling_reflectivity"],
    specularity=0, roughness=0
)

floor_material = Plastic(
    "FloorMaterial",
    r_reflectance=CONFIG["floor_reflectivity"],
    g_reflectance=CONFIG["floor_reflectivity"],
    b_reflectance=CONFIG["floor_reflectivity"],
    specularity=0, roughness=0
)

print("Materials defined from properties in {0:}\n".format(CONFIG_FILEPATH))

FENESTRATION_SURFACES = []
INTERIOR_WALL_SURFACES = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if i.Construction_Name == "Interior Wall"]):
    fen_coords = []
    for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if wall.Name in fen.Name:
            fen_coords.append(fen.coords)
            FENESTRATION_SURFACES.append(
                HBSurface(
                    "fenestration_{0:}".format(fen.Name),
                    fen_coords,
                    surface_type=5,
                    is_name_set_by_user=True,
                    is_type_set_by_user=True,
                    rad_properties=RadianceProperties(
                        material=glass_material_interior
                    )
                )
            )
    try:
        for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
            #faces.append(i.tolist())
            INTERIOR_WALL_SURFACES.append(
                HBSurface(
                    "wall_{0:}_{1:}_srfP_{2:}".format(wall_n, wall.Name, i_n),
                    i.tolist(),
                    surface_type=0,
                    is_name_set_by_user=True,
                    is_type_set_by_user=True,
                    rad_properties=RadianceProperties(
                        material=wall_material
                    )
                )
            )
    except:
        INTERIOR_WALL_SURFACES.append(
            HBSurface(
                "wall_{0:}_{1:}".format(wall_n, wall.Name),
                np.array(wall.coords).tolist(),
                surface_type=0,
                is_name_set_by_user=True,
                is_type_set_by_user=True,
                rad_properties=RadianceProperties(
                    material=wall_material
                )
            )
        )
print("{0:} interior wall surfaces generated".format(len(INTERIOR_WALL_SURFACES)))

EXTERIOR_WALL_SURFACES = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if i.Construction_Name == "Exterior Wall"]):
    angle_to_north = np.degrees(angle_between(north_vector, surface_normal(wall.coords[:3], flip=False)))
    if (angle_to_north > 315) or (angle_to_north <= 45):
        orientation_glass_material = glass_material_N
    elif (angle_to_north > 45) and (angle_to_north <= 135):
        orientation_glass_material = glass_material_E
    elif (angle_to_north > 135) and (angle_to_north <= 225):
        orientation_glass_material = glass_material_S
    elif (angle_to_north > 225) and (angle_to_north <= 315):
        orientation_glass_material = glass_material_W
    fen_coords = []
    for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if wall.Name in fen.Name:
            fen_coords.append(fen.coords)
            FENESTRATION_SURFACES.append(
                HBSurface(
                    "fenestration_{0:}".format(fen.Name),
                    fen_coords,
                    surface_type=5,
                    is_name_set_by_user=True,
                    is_type_set_by_user=True,
                    rad_properties=RadianceProperties(
                        material=orientation_glass_material
                    )
                )
            )
    try:
        for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
            #faces.append(i.tolist())
            EXTERIOR_WALL_SURFACES.append(
                HBSurface(
                    "wall_{0:}_{1:}_srfP_{2:}".format(wall_n, wall.Name, i_n),
                    i.tolist(),
                    surface_type=0,
                    is_name_set_by_user=True,
                    is_type_set_by_user=True,
                    rad_properties=RadianceProperties(
                        material=wall_material
                    )
                )
            )
    except:
        EXTERIOR_WALL_SURFACES.append(
            HBSurface(
                "wall_{0:}_{1:}".format(wall_n, wall.Name),
                np.array(wall.coords).tolist(),
                surface_type=0,
                is_name_set_by_user=True,
                is_type_set_by_user=True,
                rad_properties=RadianceProperties(
                    material=wall_material
                )
            )
        )
print("{0:} exterior wall surfaces generated".format(len(EXTERIOR_WALL_SURFACES)))

FLOOR_SURFACES = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if ((i.Construction_Name == "Interior Floor") or (i.Construction_Name == "Exterior Floor") or (i.Construction_Name == "Exposed Floor"))]):
    fen_coords = []
    FENESTRATION_SURFACES.append(
        HBSurface(
                "fenestration_{0:}".format(fen.Name),
                fen_coords,
                surface_type=0,
                is_name_set_by_user=True,
                is_type_set_by_user=True,
                rad_properties=RadianceProperties(
                    material=glass_material_skylight
                )
            )
        )
    for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if wall.Name in fen.Name:
            fen_coords.append(fen.coords)
    try:
        for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
            #faces.append(i.tolist())
            FLOOR_SURFACES.append(
                HBSurface(
                    "floor_{0:}_{1:}_srfP_{2:}".format(wall_n, wall.Name, i_n),
                    i.tolist(),
                    surface_type=2,
                    is_name_set_by_user=True,
                    is_type_set_by_user=True,
                    rad_properties=RadianceProperties(
                        material=floor_material
                    )
                )
            )
    except:
        FLOOR_SURFACES.append(
            HBSurface(
                "floor_{0:}_{1:}".format(wall_n, wall.Name),
                np.array(wall.coords).tolist(),
                surface_type=2,
                is_name_set_by_user=True,
                is_type_set_by_user=True,
                rad_properties=RadianceProperties(
                    material=floor_material
                )
            )
        )

print("{0:} floor surfaces generated".format(len(FLOOR_SURFACES)))

CEILING_SURFACES = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if ((i.Construction_Name == "Interior Ceiling") or (i.Construction_Name == "Exterior Ceiling") or (i.Construction_Name == "Roof"))]):
    fen_coords = []
    FENESTRATION_SURFACES.append(
        HBSurface(
            "fenestration_{0:}".format(fen.Name),
            fen_coords,
            surface_type=0,
            is_name_set_by_user=True,
            is_type_set_by_user=True,
            rad_properties=RadianceProperties(
                material=glass_material_skylight
            )
        )
    )
    for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if wall.Name in fen.Name:
            fen_coords.append(fen.coords)
    try:
        for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
            #faces.append(i.tolist())
            CEILING_SURFACES.append(
                HBSurface(
                    "ceiling_{0:}_{1:}_srfP_{2:}".format(wall_n, wall.Name, i_n),
                    i.tolist(),
                    surface_type=3,
                    is_name_set_by_user=True,
                    is_type_set_by_user=True,
                    rad_properties=RadianceProperties(
                        material=ceiling_material
                    )
                )
            )
    except:
        CEILING_SURFACES.append(
            HBSurface(
                "ceiling_{0:}_{1:}".format(wall_n, wall.Name),
                np.array(wall.coords).tolist(),
                surface_type=3,
                is_name_set_by_user=True,
                is_type_set_by_user=True,
                rad_properties=RadianceProperties(
                    material=ceiling_material
                )
            )
        )

print("{0:} ceiling surfaces generated".format(len(CEILING_SURFACES)))

CONTEXT_SURFACES = []
for context_n, context in enumerate([i for i in idf.idfobjects["SHADING:BUILDING:DETAILED"]]):
    srf = HBSurface("context_{0:}_{1:}".format(context_n, context.Name), context.coords, surface_type=6, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=wall_material))
    CONTEXT_SURFACES.append(srf)

print("{0:} shading surfaces generated".format(len(CONTEXT_SURFACES)))
print("{0:} fenestration surfaces generated\n".format(len(FENESTRATION_SURFACES)))
HB_OBJECTS = np.concatenate([EXTERIOR_WALL_SURFACES, INTERIOR_WALL_SURFACES, FLOOR_SURFACES, CEILING_SURFACES, CONTEXT_SURFACES, FENESTRATION_SURFACES]).tolist()  # , AIRWALL_SURFACES

# Define analysis grids for each zone for simulation in Radiance
print("Generating analysis grids: ")
HB_ANALYSIS_GRIDS = []
for floor_srf in [i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if ("Floor" in i.Construction_Name)]:
    vert_xs, vert_ys, vert_zs = list(zip(*floor_srf.coords))
    patch = patches.Polygon(list(zip(*[vert_xs, vert_ys])))
    min_x, max_x, min_y, max_y, max_z = min(vert_xs), max(vert_xs), min(vert_ys), max(vert_ys), max(vert_zs)
    x_range = max_x - min_x
    y_range = max_y - min_y
    g = np.meshgrid(
        np.arange(min_x - (x_range / 2), max_x + (x_range / 2), CONFIG["daylight_analysis_grid_spacing"]),
        np.arange(min_y - (y_range / 2), max_y + (y_range / 2), CONFIG["daylight_analysis_grid_spacing"])
    )
    COORDS = list(zip(*(c.flat for c in g)))
    ANALYSIS_POINTS = np.vstack([p for p in COORDS if patch.contains_point(p, radius=CONFIG["daylight_analysis_grid_edge_offset"])])
    GRID_POINTS = list(zip(*[np.array(list(zip(*ANALYSIS_POINTS)))[0], np.array(list(zip(*ANALYSIS_POINTS)))[1], np.repeat(max_z+CONFIG["daylight_analysis_grid_surface_offset"], len(ANALYSIS_POINTS))]))
    HB_ANALYSIS_GRIDS.append(AnalysisGrid.from_points_and_vectors(GRID_POINTS, name=floor_srf.Zone_Name))
    print("Analysis grid for {0:} generated ({1:} points)".format(floor_srf.Zone_Name, len(ANALYSIS_POINTS)))

# Generate sky matrix for annual analysis
SKY_MATRIX = SkyMatrix.from_epw_file(EPW_FILE, sky_density=2, north=north_angle_deg, hoys=range(0, 8760), mode=0, suffix="")
print("Sky matrix ({0:}) generated\n".format(SKY_MATRIX))

# Generate an output directory to store the JSON recipe constituent parts
OUTPUT_DIR = "HoneybeeRecipeJSONs"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    os.makedirs("{0:}/AnalysisGrids".format(OUTPUT_DIR))

# Write the sky matrix for annual simulation to file
SKY_MTX_PATH = "{0:}/sky_mtx.json".format("HoneybeeRecipeJSONs")
with open(SKY_MTX_PATH, "w") as f:
    json.dump({"sky_mtx": SKY_MATRIX.to_json()}, f)
print("Sky matrix written to {0:}\n".format(SKY_MTX_PATH))

for HB_ANALYSIS_GRID in HB_ANALYSIS_GRIDS:
    ANALYSIS_GRID_PATH = "{0:}/AnalysisGrids/{1:}.json".format(OUTPUT_DIR, HB_ANALYSIS_GRID.name)
    with open(ANALYSIS_GRID_PATH, "w") as f:
        json.dump({"analysis_grids": [HB_ANALYSIS_GRID.to_json()]}, f)
    print("Analysis grid for {0:} written to {1:}".format(HB_ANALYSIS_GRID.name, ANALYSIS_GRID_PATH))

# Write the context geometry (surfaces) around the analysis grids
SURFACES_PATH = "{0:}/surfaces.json".format(OUTPUT_DIR)
with open(SURFACES_PATH, "w") as f:
    f.write(repr({"surfaces": [i.to_json() for i in HB_OBJECTS]}).replace("'", '"').replace("(", '[').replace(")", ']'))
print("\nSurfaces written to {0:}\n".format(SURFACES_PATH))

# # print(HB_ANALYSIS_GRIDS[0].to_json())

# # Create the analysis recipes for each IDF zone
# # print("Generating analysis grids ...")
# # for HB_ANALYSIS_GRID in HB_ANALYSIS_GRIDS:

# #     # Create a directory in which to save the DF recipe/s
# #     DF_RECIPE_DIR = "{0:}/{1:}/daylight_factor".format(CONFIG["output_directory"], HB_ANALYSIS_GRID.name)
# #     if not os.path.exists(DF_RECIPE_DIR):
# #         os.makedirs(DF_RECIPE_DIR)

# #     # Generate a DF recipe as JSON and save [WITHOUT CONTEXT GEOMETRY]
# #     with open("{0:}/df_recipe.json".format(DF_RECIPE_DIR), "w") as f:
# #         json.dump(GridBasedDF(analysis_grids=[HB_ANALYSIS_GRID], hb_objects=[]).to_json(), f)
# #     print("{0:} daylight factor analysis grid written to {1:}/df_recipe.json\n".format(HB_ANALYSIS_GRID.name, DF_RECIPE_DIR))

# #     # Create a directory in which to save the Annual recipe/s
# #     ANNUAL_RECIPE_DIR = "{0:}/{1:}/annual".format(CONFIG["output_directory"], HB_ANALYSIS_GRID.name)
# #     if not os.path.exists(ANNUAL_RECIPE_DIR):
# #         os.makedirs(ANNUAL_RECIPE_DIR)

# #     # Generate an ANNUAL recipe as JSON and save [WITHOUT CONTEXT GEOMETRY]
# #     with open("{0:}/annual_recipe.json".format(ANNUAL_RECIPE_DIR), "w") as f:
# #         # Remove sky matrix from the Annual recipe and assign to variable
# #         json.dump(GridBasedAnnual(SKY_MATRIX, analysis_grids=[HB_ANALYSIS_GRID], hb_objects=[]).to_json(), f)
# #     print("{0:} annual analysis grid written to {1:}/annual_recipe.json\n".format(HB_ANALYSIS_GRID.name, ANNUAL_RECIPE_DIR))

# # # Write the context geometry to a seperate file
# # with open(CONFIG["output_directory"]+"/geometry.json", "w") as f:
# #     f.write(repr({"surfaces": [i.to_json() for i in HB_OBJECTS]}).replace("'", '"').replace("(", '[').replace(")", ']'))
# # print("Geometry written to {0:}\n".format(CONFIG["output_directory"]+"/geometry.json"))

# # # Write the sky matrix to a seperate file
# # with open(CONFIG["output_directory"]+"/sky_matrix.json", "w") as f:
# #     json.dump(sky_matrix_json, f)
# # print("Annual sky matrix written to {0:}\n".format(CONFIG["output_directory"]+"/sky_matrix.json"))
