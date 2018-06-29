from scipy.spatial import Delaunay
import numpy as np

# PAR1 = [(5.0, 0.0, 0.0), (5.0, 5.0, 0.0), (5.0, 5.0, 3.0), (5.0, 0.0, 3.0)]
# CHI1 = [
#     [
#         (5.0, 4.786388397216797, 1.9928041696548462),
#         (5.0, 4.786388397216797, 2.821777105331421),
#         (5.0, 0.20462320744991302, 2.821777105331421),
#         (5.0, 0.20462320744991302, 1.9928041696548462)
#     ]
# ]

# PAR2 = [(0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (5.0, 0.0, 3.0), (0.0, 0.0, 3.0)]
# CHI2 = [
#     [
#         (0.8970338106155396, 0.0, 0.800000011920929),
#         (2.2782294750213623, 0.0, 0.800000011920929),
#         (2.2782294750213623, 0.0, 2.4154775142669678),
#         (0.8970338106155396, 0.0, 2.4154775142669678)
#     ],
#     [
#         (3.0728237628936768, 0.0, 0.800000011920929),
#         (4.284397125244141, 0.0, 0.800000011920929),
#         (4.284397125244141, 0.0, 2.4154775142669678),
#         (3.0728237628936768, 0.0, 2.4154775142669678)
#     ]
# ]


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
