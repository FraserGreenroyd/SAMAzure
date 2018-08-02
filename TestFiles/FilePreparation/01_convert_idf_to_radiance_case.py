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
    TODO - Create ability to visualise surfaces and analysis grids in context
    TODO - Add radiance parameters to the config.json to put into the generated recipes
    TODO - Add method interpreting results for SDA, DA, DF, UDI, UDILess, UDIMore
    TODO - Check the fenestration surface normal is point teh right direction for correct window angle for G value assignment
    TODO - Add method to extract glazing light transmittance from the IDF to pass to the Radiance case generation (rather than using the config file to get this data)
"""

# Load necessary packages
import os
from eppy.modeleditor import IDF
import json
import numpy as np
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

idf_filepath = sys.argv[1]
config_filepath = sys.argv[2]
epw_file = sys.argv[3]
output_directory = sys.argv[4]  # "Radfiles"

# Load the setup configuration for this IDF modification
with open(config_filepath, "r") as f:
    config = json.load(f)
print("\nConfig loaded from {0:}\n".format(config_filepath))

# Load IDF ready for pre-processing and modification
if "win" in sys.platform.lower() and "dar" not in sys.platform.lower():
    IDF.setiddname("C:/EnergyPlusV8-8-0/Energy+.idd")
elif "dar" in sys.platform.lower():
    IDF.setiddname("/Applications/EnergyPlus-8-8-0/Energy+.idd")
elif "lin" in sys.platform.lower():
    IDF.setiddname("idd_location")  # TODO - This will break - I need to find where linux installs the IDD and amend

# epw_file = config["weather_file"]
idf = IDF(idf_filepath)

print("IDF loaded from {0:}\n".format(idf_filepath))
print("EPW loaded from {0:}\n".format(epw_file))

# Set the "vector to north", so that wall orientation can be obtained
north_angle_deg = idf.idfobjects["BUILDING"][0].North_Axis
north_angle_rad = np.radians(north_angle_deg)
north_vector = (np.sin(north_angle_rad), np.cos(north_angle_rad), 0)
print("North angle has been read as {0:}\n".format(north_angle_rad))

# Define materials to be applied to surfaces
glass_material_exterior = Glass(
    "GlassMaterialInternal",
    r_transmittance=config["glass_visible_transmittance"],
    g_transmittance=config["glass_visible_transmittance"],
    b_transmittance=config["glass_visible_transmittance"],
    refraction_index=1.52
)

# glass_material_N = Glass(
#     "GlassMaterialN",
#     r_transmittance=config["glass_visible_transmittance"],
#     g_transmittance=config["glass_visible_transmittance"],
#     b_transmittance=config["glass_visible_transmittance"],
#     refraction_index=1.52
#     )
#
# glass_material_S = Glass(
#     "GlassMaterialS",
#     r_transmittance=config["glass_visible_transmittance"],
#     g_transmittance=config["glass_visible_transmittance"],
#     b_transmittance=config["glass_visible_transmittance"],
#     refraction_index=1.52
# )
#
# glass_material_E = Glass(
#     "GlassMaterialE",
#     r_transmittance=config["glass_visible_transmittance"],
#     g_transmittance=config["glass_visible_transmittance"],
#     b_transmittance=config["glass_visible_transmittance"],
#     refraction_index=1.52
# )
#
# glass_material_W = Glass(
#     "GlassMaterialW",
#     r_transmittance=config["glass_visible_transmittance"],
#     g_transmittance=config["glass_visible_transmittance"],
#     b_transmittance=config["glass_visible_transmittance"],
#     refraction_index=1.52
# )

glass_material_interior = Glass(
    "GlassMaterialInternal",
    r_transmittance=0.9, g_transmittance=0.9, b_transmittance=0.9, refraction_index=1.52
)

glass_material_skylight = Glass(
    "GlassMaterialSkylight",
    r_transmittance=config["glass_visible_transmittance"],
    g_transmittance=config["glass_visible_transmittance"],
    b_transmittance=config["glass_visible_transmittance"],
    refraction_index=1.52
)

air_wall_material = Glass(
    "AirWallMaterial",
    r_transmittance=0, g_transmittance=0, b_transmittance=0, refraction_index=1
)

wall_material = Plastic(
    "WallMaterial",
    r_reflectance=config["wall_reflectivity"],
    g_reflectance=config["wall_reflectivity"],
    b_reflectance=config["wall_reflectivity"],
    specularity=0, roughness=0
)

ceiling_material = Plastic(
    "CeilingMaterial",
    r_reflectance=config["ceiling_reflectivity"],
    g_reflectance=config["ceiling_reflectivity"],
    b_reflectance=config["ceiling_reflectivity"],
    specularity=0, roughness=0
)

floor_material = Plastic(
    "FloorMaterial",
    r_reflectance=config["floor_reflectivity"],
    g_reflectance=config["floor_reflectivity"],
    b_reflectance=config["floor_reflectivity"],
    specularity=0, roughness=0
)

print("Materials defined from properties in {0:}\n".format(config_filepath))

fenestration_surfaces = []
interior_wall_surfaces = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if i.Construction_Name == "Interior Wall"]):
    fen_coords = []
    for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if wall.Name in fen.Name:
            fen_coords.append(fen.coords)
            fenestration_surfaces.append(
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
            interior_wall_surfaces.append(
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
        interior_wall_surfaces.append(
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
print("{0:} interior wall surfaces generated".format(len(interior_wall_surfaces)))

exterior_wall_surfaces = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if i.Construction_Name == "Exterior Wall"]):
    # angle_to_north = np.degrees(angle_between(north_vector, surface_normal(wall.coords[:3], flip=False)))
    # if (angle_to_north > 315) or (angle_to_north <= 45):
    #     glass_material = glass_material_N
    # elif (angle_to_north > 45) and (angle_to_north <= 135):
    #     glass_material = glass_material_E
    # elif (angle_to_north > 135) and (angle_to_north <= 225):
    #     glass_material = glass_material_S
    # elif (angle_to_north > 225) and (angle_to_north <= 315):
    #     glass_material = glass_material_W
    fen_coords = []
    for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
        if wall.Name in fen.Name:
            fen_coords.append(fen.coords)
            fenestration_surfaces.append(
                HBSurface(
                    "fenestration_{0:}".format(fen.Name),
                    fen_coords,
                    surface_type=5,
                    is_name_set_by_user=True,
                    is_type_set_by_user=True,
                    rad_properties=RadianceProperties(
                        material=glass_material_exterior
                    )
                )
            )
    try:
        for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
            #faces.append(i.tolist())
            exterior_wall_surfaces.append(
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
        exterior_wall_surfaces.append(
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
print("{0:} exterior wall surfaces generated".format(len(exterior_wall_surfaces)))

floor_surfaces = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if ((i.Construction_Name == "Interior Floor") or (i.Construction_Name == "Exterior Floor") or (i.Construction_Name == "Exposed Floor"))]):
    fen_coords = []
    fenestration_surfaces.append(
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
            floor_surfaces.append(
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
        floor_surfaces.append(
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

print("{0:} floor surfaces generated".format(len(floor_surfaces)))

ceiling_surfaces = []
for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if ((i.Construction_Name == "Interior Ceiling") or (i.Construction_Name == "Exterior Ceiling") or (i.Construction_Name == "Roof"))]):
    fen_coords = []
    fenestration_surfaces.append(
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
            ceiling_surfaces.append(
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
        ceiling_surfaces.append(
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

print("{0:} ceiling surfaces generated".format(len(ceiling_surfaces)))

context_surfaces = []
for context_n, context in enumerate([i for i in idf.idfobjects["SHADING:BUILDING:DETAILED"]]):
    srf = HBSurface("context_{0:}_{1:}".format(context_n, context.Name), context.coords, surface_type=6, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=wall_material))
    context_surfaces.append(srf)

print("{0:} shading surfaces generated".format(len(context_surfaces)))
print("{0:} fenestration surfaces generated\n".format(len(fenestration_surfaces)))
hb_objects = np.concatenate([exterior_wall_surfaces, interior_wall_surfaces, floor_surfaces, ceiling_surfaces, context_surfaces, fenestration_surfaces]).tolist()  # , AIRWALL_SURFACES

# Define analysis grids for each zone for simulation in Radiance
print("Generating analysis grids: ")
hb_analysis_grids = []
for floor_srf in [i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if ("Floor" in i.Construction_Name)]:
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
    analysis_points = np.vstack([p for p in coords if patch.contains_point(p, radius=config["daylight_analysis_grid_edge_offset"])])
    grid_points = list(zip(*[np.array(list(zip(*analysis_points)))[0], np.array(list(zip(*analysis_points)))[1], np.repeat(max_z + config["daylight_analysis_grid_surface_offset"], len(analysis_points))]))
    hb_analysis_grids.append(AnalysisGrid.from_points_and_vectors(grid_points, name=floor_srf.Zone_Name))
    print("Analysis grid for {0:} generated ({1:} points)".format(floor_srf.Zone_Name, len(analysis_points)))

# Generate sky matrix for annual analysis
sky_matrix = SkyMatrix.from_epw_file(epw_file, sky_density=2, north=north_angle_deg, hoys=range(0, 8760), mode=0, suffix="")
print("Sky matrix ({0:}) generated\n".format(sky_matrix))

# Generate an output directory to store the JSON recipe constituent parts
if not os.path.exists(output_directory):
    os.makedirs(output_directory)
    os.makedirs("{0:}/AnalysisGrids".format(output_directory))

# Write the sky matrix for annual simulation to file
sky_matrix_path = "{0:}/sky_mtx.json".format(output_directory)
with open(sky_matrix_path, "w") as f:
    json.dump({"sky_mtx": sky_matrix.to_json()}, f)
print("Sky matrix written to {0:}\n".format(sky_matrix_path))

# Write the analysis grids to a directory for processing
for hb_analysis_grid in hb_analysis_grids:
    analysis_grid_path = "{0:}/AnalysisGrids/{1:}.json".format(output_directory, hb_analysis_grid.name)
    with open(analysis_grid_path, "w") as f:
        json.dump({"analysis_grids": [hb_analysis_grid.to_json()]}, f)
    print("Analysis grid for {0:} written to {1:}".format(hb_analysis_grid.name, analysis_grid_path))

# Write the context geometry (surfaces) around the analysis grids
surfaces_path = "{0:}/surfaces.json".format(output_directory)
with open(surfaces_path, "w") as f:
    f.write(repr({"surfaces": [i.to_json() for i in hb_objects]}).replace("'", '"').replace("(", '[').replace(")", ']'))
print("\nSurfaces written to {0:}\n".format(surfaces_path))
