# call "C:\Users\tgerrish\AppData\Local\Continuum\anaconda2\Scripts\activate.bat" && activate base

# TODO - Orient analysis grid_file to longest edge of zone it's being generated for
# TODO - Create ability to visualise surfaces and analysis grids in context
# TODO - Add radiance parameters to the config.json to put into the generated recipes
# TODO - Add method interpreting results for SDA, DA, DF, UDI, UDILess, UDIMore
# TODO - Check the fenestration surface normal is point teh right direction for correct window angle for G value assignment
# TODO - Add method to extract glazing light transmittance from the IDF to pass to the Radiance case generation (rather than using the config file to get this data)

# from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import json
import os
import sys
import itertools

import matplotlib.patches as patches
import numpy as np
from eppy.modeleditor import IDF
from scipy.spatial import Delaunay


sys.path.insert(0, 'ladybug')
sys.path.insert(0, 'honeybee')

from honeybee.hbsurface import HBSurface
from honeybee.radiance.analysisgrid import AnalysisGrid
from honeybee.radiance.material.glass import Glass
from honeybee.radiance.material.plastic import Plastic
from honeybee.radiance.properties import RadianceProperties
from honeybee.radiance.sky.skymatrix import SkyMatrix


# ************************************************** #
# ***   Public methods                           *** #
# ************************************************** #

def load_json(path):
    """
    Load a JSON file into a dictionary object
    :type path: Path to JSON file
    :return: Dictionary representing content of JSON file
    """
    with open(path) as data_file:
        return json.load(data_file)


def os_idd():
    """
    Check the operating system and return it's name
    :return: Standard location of EnergyPlus IDD file
    """
    if "win" in sys.platform.lower() and "dar" not in sys.platform.lower():
        return "C:/EnergyPlusV8-8-0/Energy+.idd"
    elif "dar" in sys.platform.lower():
        return "/Applications/EnergyPlus-8-8-0/Energy+.idd"
    elif "lin" in sys.platform.lower():
        raise NameError("No IDD location specified - check the TODO list")


def unit_vector(start, end):
    """
    Returns the unit vector of a line described by its start and end points
    :type start: [x, y] coordinate array
    :type end: [x, y] coordinate array
    :return: [x, y] vector array
    """
    pt_distance = np.array(end) - np.array(start)
    vector = pt_distance / np.sqrt(np.sum(pt_distance * pt_distance))
    return vector


def unit_vector2(vector):
    """
    Returns the unit vector of a vector
    :type vector: array
    :return: array
    """
    return vector / np.linalg.norm(vector)


def surface_normal(points, flip=False):
    """
    Given 3 points from a surface, return the surface normal
    :type points: array
    :type flip: bool
    :return: array
    """
    U = np.array(points[1]) - np.array(points[0])
    V = np.array(points[2]) - np.array(points[0])
    Nx = U[1] * V[2] - U[2] * V[1]
    Ny = U[2] * V[0] - U[0] * V[2]
    Nz = U[0] * V[1] - U[1] * V[0]
    mag = np.sqrt(Nx ** 2 + Ny ** 2 + Nz ** 2)

    if flip:
        return (np.array([Nx, Ny, Nz]) / mag).tolist()
    else:
        return (-np.array([Nx, Ny, Nz]) / mag).tolist()


def translated_point(uv, uw, origin, point):
    """
    Translates a 3D point into a 2D point
    :type uv: array
    :type uw: array
    :type origin: array
    :type point: array
    :return: array
    """
    x = (point[0] - origin[0]) * uv[0] + (point[1] - origin[1]) * uv[1] + (point[2] - origin[2]) * uv[2]
    y = (point[0] - origin[0]) * uw[0] + (point[1] - origin[1]) * uw[1] + (point[2] - origin[2]) * uw[2]
    return x, y


def untranslated_point(uv, uw, origin, point):
    """
    Translates a 2D point into a 3D point
    :type uv: array
    :type uw: array
    :type origin: array
    :type point: array
    :return: array
    """
    x = origin[0] + uv[0] * point[0] + uw[0] * point[1]
    y = origin[1] + uv[1] * point[0] + uw[1] * point[1]
    z = origin[2] + uv[2] * point[0] + uw[2] * point[1]
    return x, y, z


def triangulate_3d_surfaces(parent_surface_vertices, child_surfaces_vertices):
    """
    Returns a set of vertices describing the delaunay mesh of a parent surface minus the child surfaces
    :type parent_surface_vertices: array
    :type child_surfaces_vertices: array
    :return: array
    """
    uv = unit_vector(parent_surface_vertices[0], parent_surface_vertices[1])
    uw = unit_vector(parent_surface_vertices[0], parent_surface_vertices[3])

    parent_surface_vertices_translated = np.array(
        [translated_point(uv, uw, parent_surface_vertices[0], i) for i in parent_surface_vertices])
    child_surfaces_vertices_translated = np.array(
        [[translated_point(uv, uw, parent_surface_vertices[0], i) for i in ch] for ch in child_surfaces_vertices])

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


def angle_between(vector_1, vector_2):
    """
    Returns the angle in radians between vectors 'vector_1' and 'vector_2'
    :type vector_1: object
    :type vector_2: object
    :return: Angle in radians
    """
    vector_1_u = unit_vector2(vector_1)
    vector_2_u = unit_vector2(vector_2)
    return np.arccos(np.clip(np.dot(vector_1_u, vector_2_u), -1.0, 1.0))


def rotate(origin, point, angle_rad):
    """
    Rotate a point counterclockwise by a given angle around a given origin. The angle should be given in radians.
    :type origin: object
    :type point: object
    :type angle_rad: Angle in radians
    :return: array
    """
    o_x, o_y = origin
    p_x, p_y = point
    q_x = o_x + np.cos(angle_rad) * (p_x - o_x) - np.sin(angle_rad) * (p_y - o_y)
    q_y = o_y + np.sin(angle_rad) * (p_x - o_x) + np.cos(angle_rad) * (p_y - o_y)
    return q_x, q_y


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise TypeError('Boolean value expected. E.g. y/N/0/true,f')


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


# ************************************************** #
# ***   Main execution                           *** #
# ************************************************** #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a Radiance case (using Honeybee) from an IDF file!")
    parser.add_argument(
        "-i",
        "--inputIDF",
        type=str,
        help="Path to the source IDF from which geometry and constructions are obtained",
        default="./resources/idf_processing/output.idf"  # TODO - remove post testing
    )
    parser.add_argument(
        "-w",
        "--weatherFile",
        type=str,
        help="Path to the EPW weather file for the location being simulated",
        default="./resources/idf_processing/GBR_Cardiff_CIBSE_TRY.epw"  # TODO - remove post testing
    )
    parser.add_argument(
        "-c",
        "--configFile",
        type=str,
        help="Path to the config file containing construction reflectances and glazing transmissivities",
        default="./resources/idf_processing/idf_config.json"  # TODO - remove post testing
    )
    parser.add_argument(
        "-o",
        "--outputDir",
        type=str,
        help="Path to the target output directory",
        default="./radiance_case"  # TODO - remove post testing
    )
    parser.add_argument(
        "-gs",
        "--gridSize",
        type=float,
        help="Optional grid_file size (default is 0.5m)",
        default=0.5
    )
    parser.add_argument(
        "-so",
        "--surfaceOffset",
        type=float,
        help="Optional analysis grid_file surface offset (default is 0.765m)",
        default=0.765
    )
    parser.add_argument(
        "-eo",
        "--edgeOffset",
        type=float,
        help="Optional analysis grid_file room boundary offset (default is 0.1m)",
        default=0.1
    )
    parser.add_argument(
        "-fb",
        "--fullBuilding",
        type=str2bool,
        help="Create a 3D case - THIS WILL PROBABLY BREAK!",
        default=False
    )
    parser.add_argument(
        "-cs",
        "--chunkSize",
        type=int,
        help="How many points to be included in each 3d grid matrix chunk!",
        default=1000
    )

    args = parser.parse_args()

    configuration_file_path = args.configFile
    input_idf_path = args.inputIDF
    input_weatherfile_path = args.weatherFile
    output_directory = args.outputDir
    grid_size = args.gridSize
    surface_offset = args.surfaceOffset
    edge_offset = args.edgeOffset
    full_building = args.fullBuilding
    chunk_size = args.chunkSize



    with open(configuration_file_path, "r") as f:
        config = json.load(f)
    print("Config loaded from {0:}".format(os.path.normpath(configuration_file_path)))

    print("Analysis grid_file spacing set to {0:}".format(grid_size))

    print("Analysis grid_file offset from surface set to {0:}".format(surface_offset))

    print("Analysis grid_file boundary offset set to {0:}".format(edge_offset))

    IDF.setiddname(os_idd())
    idf = IDF(input_idf_path)

    print("IDF loaded from {0:}".format(os.path.normpath(input_idf_path)))
    print("EPW loaded from {0:}".format(os.path.normpath(input_weatherfile_path)))

    # Obtain building orientation to ascertain surface direction
    north_angle_deg = idf.idfobjects["BUILDING"][0].North_Axis
    north_angle_rad = np.radians(north_angle_deg)
    north_vector = (np.sin(north_angle_rad), np.cos(north_angle_rad), 0)
    print("North angle has been read as {0:}".format(north_angle_rad))

    # Define materials to be applied to surfaces
    glass_material_exterior = Glass("GlassMaterialInternal", r_transmittance=config["glass_visible_transmittance"], g_transmittance=config["glass_visible_transmittance"], b_transmittance=config["glass_visible_transmittance"], refraction_index=1.52)
    glass_material_interior = Glass("GlassMaterialInternal", r_transmittance=0.9, g_transmittance=0.9, b_transmittance=0.9, refraction_index=1.52)
    glass_material_skylight = Glass("GlassMaterialSkylight", r_transmittance=config["glass_visible_transmittance"], g_transmittance=config["glass_visible_transmittance"], b_transmittance=config["glass_visible_transmittance"], refraction_index=1.52)
    air_wall_material = Glass("AirWallMaterial", r_transmittance=0, g_transmittance=0, b_transmittance=0, refraction_index=1)
    wall_material = Plastic("WallMaterial", r_reflectance=config["wall_reflectivity"], g_reflectance=config["wall_reflectivity"], b_reflectance=config["wall_reflectivity"], specularity=0, roughness=0)
    ceiling_material = Plastic("CeilingMaterial", r_reflectance=config["ceiling_reflectivity"], g_reflectance=config["ceiling_reflectivity"], b_reflectance=config["ceiling_reflectivity"], specularity=0, roughness=0)
    floor_material = Plastic("FloorMaterial", r_reflectance=config["floor_reflectivity"], g_reflectance=config["floor_reflectivity"], b_reflectance=config["floor_reflectivity"], specularity=0, roughness=0)
    print("Materials defined from properties in {0:}".format(os.path.normpath(configuration_file_path)))

    # Define surfaces for radiation oclusion
    fenestration_surfaces = []
    interior_wall_surfaces = []
    for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if i.Construction_Name == "Interior Wall"]):
        fen_coords = []
        for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
            if wall.Name in fen.Name:
                fen_coords.append(fen.coords)
                fenestration_surfaces.append(HBSurface("fenestration_{0:}".format(fen.Name), fen_coords, surface_type=5,
                                                       is_name_set_by_user=True, is_type_set_by_user=True,
                                                       rad_properties=RadianceProperties(
                                                           material=glass_material_interior)))
        try:
            for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
                interior_wall_surfaces.append(
                    HBSurface("wall_{0:}_{1:}_srfP_{2:}".format(wall_n, wall.Name, i_n), i.tolist(), surface_type=0,
                              is_name_set_by_user=True, is_type_set_by_user=True,
                              rad_properties=RadianceProperties(material=wall_material)))
        except:
            interior_wall_surfaces.append(
                HBSurface("wall_{0:}_{1:}".format(wall_n, wall.Name), np.array(wall.coords).tolist(), surface_type=0,
                          is_name_set_by_user=True, is_type_set_by_user=True,
                          rad_properties=RadianceProperties(material=wall_material)))
    print("{0:} interior wall surfaces generated".format(len(interior_wall_surfaces)))

    exterior_wall_surfaces = []
    for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if i.Construction_Name == "Exterior Wall"]):
        fen_coords = []
        for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
            if wall.Name in fen.Name:
                fen_coords.append(fen.coords)
                fenestration_surfaces.append(HBSurface("fenestration_{0:}".format(fen.Name), fen_coords, surface_type=5,
                                                       is_name_set_by_user=True, is_type_set_by_user=True,
                                                       rad_properties=RadianceProperties(
                                                           material=glass_material_exterior)))
        try:
            for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
                exterior_wall_surfaces.append(
                    HBSurface("wall_{0:}_{1:}_srfP_{2:}".format(wall_n, wall.Name, i_n), i.tolist(), surface_type=0,
                              is_name_set_by_user=True, is_type_set_by_user=True,
                              rad_properties=RadianceProperties(material=wall_material)))
        except:
            exterior_wall_surfaces.append(
                HBSurface("wall_{0:}_{1:}".format(wall_n, wall.Name), np.array(wall.coords).tolist(), surface_type=0,
                          is_name_set_by_user=True, is_type_set_by_user=True,
                          rad_properties=RadianceProperties(material=wall_material)))
    print("{0:} exterior wall surfaces generated".format(len(exterior_wall_surfaces)))

    floor_surfaces = []
    for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if (
            (i.Construction_Name == "Interior Floor") or (i.Construction_Name == "Exterior Floor") or (
            i.Construction_Name == "Exposed Floor"))]):
        fen_coords = []
        fenestration_surfaces.append(HBSurface("fenestration_{0:}".format(fen.Name), fen_coords, surface_type=0, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=glass_material_skylight)))
        for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
            if wall.Name in fen.Name:
                fen_coords.append(fen.coords)
        try:
            for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
                floor_surfaces.append(HBSurface("floor_{0:}_{1:}_srfP_{2:}".format(wall_n, wall.Name, i_n), i.tolist(), surface_type=2, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=floor_material)))
        except:
            floor_surfaces.append(HBSurface("floor_{0:}_{1:}".format(wall_n, wall.Name), np.array(wall.coords).tolist(), surface_type=2, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=floor_material)))
    print("{0:} floor surfaces generated".format(len(floor_surfaces)))

    ceiling_surfaces = []
    for wall_n, wall in enumerate([i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if ((i.Construction_Name == "Interior Ceiling") or (i.Construction_Name == "Exterior Ceiling") or (i.Construction_Name == "Roof"))]):
        fen_coords = []
        fenestration_surfaces.append(HBSurface("fenestration_{0:}".format(fen.Name), fen_coords, surface_type=0, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=glass_material_skylight)))
        for fen_n, fen in enumerate(idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]):
            if wall.Name in fen.Name:
                fen_coords.append(fen.coords)
        try:
            for i_n, i in enumerate(triangulate_3d_surfaces(wall.coords, fen_coords)):
                ceiling_surfaces.append(HBSurface("ceiling_{0:}_{1:}_srfP_{2:}".format(wall_n, wall.Name, i_n), i.tolist(), surface_type=3, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=ceiling_material)))
        except:
            ceiling_surfaces.append(HBSurface("ceiling_{0:}_{1:}".format(wall_n, wall.Name), np.array(wall.coords).tolist(), surface_type=3, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=ceiling_material)))
    print("{0:} ceiling surfaces generated".format(len(ceiling_surfaces)))

    context_surfaces = []
    for context_n, context in enumerate([i for i in idf.idfobjects["SHADING:BUILDING:DETAILED"]]):
        srf = HBSurface("context_{0:}_{1:}".format(context_n, context.Name), context.coords, surface_type=6, is_name_set_by_user=True, is_type_set_by_user=True, rad_properties=RadianceProperties(material=wall_material))
        context_surfaces.append(srf)
    print("{0:} shading surfaces generated".format(len(context_surfaces)))

    print("{0:} fenestration surfaces generated".format(len(fenestration_surfaces)))
    hb_objects = np.concatenate([exterior_wall_surfaces, interior_wall_surfaces, floor_surfaces, ceiling_surfaces, context_surfaces, fenestration_surfaces]).tolist()

    # Generate an output directory to store the JSON recipe constituent parts
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        os.makedirs("{0:}/AnalysisGrids".format(output_directory))
    print("Output directory set to {0:}\\AnalysisGrids".format(os.path.normpath(output_directory)))

    # TESTING: UNDER CONSTRUCTION

    if full_building:
        print("Generating a 3D Radiance case")

        # Get objects bounding box extents
        pts = np.concatenate([np.array([item for sublist in [i.coords for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"]] for item in sublist]), np.array([item for sublist in [i.coords for i in idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]] for item in sublist])])
        pt1 = [min(point[i] for point in pts) for i in range(3)]
        pt2 = [max(point[i] for point in pts) for i in range(3)]
        # print("Bounding box extents at [[{0:}], [{1:}]]".format(pt1, pt2))

        x_vals = np.arange(pt1[0], pt2[0], grid_size).tolist()
        y_vals = np.arange(pt1[1], pt2[1], grid_size).tolist()
        z_vals = np.arange(pt1[2], pt2[2], grid_size).tolist()

        points = list(itertools.product(*[x_vals, y_vals, z_vals]))
        # print("{0:} points generated".format(len(points)))

        chunked_points = list(chunks(points, chunk_size))
        # print("{0:} seperate grids generated".format(len(chunked_points)))

        print("These settings will produce a case with {0:} points".format(len(points)))
        print("With a chunk size of {0:}, this means a total number of {1:} tasks (spread over {2:} pools) will be created.".format(chunk_size, len(chunked_points), int(np.ceil(float(len(chunked_points))/100))))

        response = raw_input("Do you want to continue? [y/N]: ")
        if response == "y":
            hb_analysis_grids = []
            for n, c in enumerate(chunked_points):
                hb_analysis_grids.append(AnalysisGrid.from_points_and_vectors(c, name="gridmatrix{0:04d}".format(n)))
                print("Analysis grid_file for gridmatrix{0:04d} generated ({1:} points)".format(n, len(c)))
        elif response != "y":
            raise RuntimeError("You didn't continue. Good for you.")
            sys.exit(1)

    else:
        print("Generating a 2D Radiance case")
    # TODO: UNDER CONSTRUCTION

        # Define analysis grids for each zone for simulation in Radiance
        hb_analysis_grids = []
        for floor_srf in [i for i in idf.idfobjects["BUILDINGSURFACE:DETAILED"] if ("Floor" in i.Construction_Name)]:
            vert_xs, vert_ys, vert_zs = list(zip(*floor_srf.coords))
            patch = patches.Polygon(list(zip(*[vert_xs, vert_ys])))
            min_x, max_x, min_y, max_y, max_z = min(vert_xs), max(vert_xs), min(vert_ys), max(vert_ys), max(vert_zs)
            x_range = max_x - min_x
            y_range = max_y - min_y
            g = np.meshgrid(np.arange(min_x - (x_range / 2), max_x + (x_range / 2), grid_size),
                            np.arange(min_y - (y_range / 2), max_y + (y_range / 2), grid_size))
            coords = list(zip(*(c.flat for c in g)))
            analysis_points = np.vstack([p for p in coords if patch.contains_point(p, radius=edge_offset)])
            grid_points = list(zip(*[np.array(list(zip(*analysis_points)))[0], np.array(list(zip(*analysis_points)))[1],
                                     np.repeat(max_z + surface_offset, len(analysis_points))]))
            hb_analysis_grids.append(AnalysisGrid.from_points_and_vectors(grid_points, name=floor_srf.Zone_Name))
            print("Analysis grid_file for {0:} generated ({1:} points)".format(floor_srf.Zone_Name, len(analysis_points)))

    # Write the analysis grids to a directory for processing
    for hb_analysis_grid in hb_analysis_grids:
        analysis_grid_path = "{0:}/AnalysisGrids/{1:}.json".format(output_directory, hb_analysis_grid.name)
        # print(model_path)
        with open(analysis_grid_path, "w") as f:
            json.dump({"analysis_grids": [hb_analysis_grid.to_json()]}, f)
        print("Analysis grid_file for {0:} written to {1:}".format(hb_analysis_grid.name, os.path.normpath(analysis_grid_path)))


    # Generate sky matrix for annual analysis
    sky_matrix = SkyMatrix.from_epw_file(input_weatherfile_path, sky_density=2, north=north_angle_deg, hoys=range(0, 8760),
                                         mode=0, suffix="")
    print("Sky matrix ({0:}) generated".format(sky_matrix))

    # Write the sky matrix for annual simulation to file
    sky_matrix_path = "{0:}/sky_mtx.json".format(output_directory)
    with open(sky_matrix_path, "w") as f:
        json.dump({"sky_mtx": sky_matrix.to_json()}, f)
    print("Sky matrix written to {0:}".format(os.path.normpath(sky_matrix_path)))

    # Write the context geometry (surfaces) around the analysis grids
    surfaces_path = "{0:}/surfaces.json".format(os.path.normpath(output_directory))
    with open(surfaces_path, "w") as f:
        f.write(
            repr({"surfaces": [i.to_json() for i in hb_objects]}).replace("'", '"').replace("(", '[').replace(")", ']'))
    print("\nSurfaces written to {0:}".format(os.path.normpath(surfaces_path)))
