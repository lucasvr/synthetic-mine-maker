#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Mine-related objects.

from scipy.spatial import ConvexHull, Delaunay
from collections import OrderedDict
from src.geometry import *
import numpy as np
import random
import math

class DrillHole:
    """
    Drill hole information.
    """
    def __init__(self, p1, normal, col, row, size_generator, segment_size, num_dimensions):
        # Col,Row used for ASCII printing purposes only
        self.col = col
        self.row = row
        self.size_generator = size_generator
        self.line = Line(p1, Point(p1.x, p1.y, p1.z))
        self.normal = normal
        self.segment_size = segment_size
        self.num_dimensions = num_dimensions
        self.length = -1

    def create(self):
        """
        Create the drill hole line object.
        """
        n = self.num_dimensions
        self.line.p2.x += self.normal.x
        self.line.p2.y += self.normal.y
        if n == 3:
            self.line.p2.z += self.normal.z

        # Tilt the line a little bit so it's not boring straight
        x_angle = random.uniform(math.radians(-15), math.radians(15)) if n == 3 else None
        y_angle = random.uniform(math.radians(-15), math.radians(15)) if n == 3 else None
        z_angle = random.uniform(math.radians(-15), math.radians(15))
        self.line.rotate(x_angle=x_angle, y_angle=y_angle, z_angle=z_angle)

        # Keep the length of this drill hole within the range
        # requested by the user
        self.length = self.size_generator.generate(1)[0]
        self.line.setLength(self.length)

    def segments(self):
        """
        Split self.line into several line segments of @self.segment_size
        each (with the exception of the last segment, which may be smaller
        than that.)
        """
        lines = []
        p1, normal = self.line.p1, self.normal
        for depth in np.arange(0, self.length, self.segment_size):
            drill = DrillHole(p1, normal, self.col, self.row, None, 0, self.num_dimensions)
            drill.length = self.segment_size
            if depth + self.segment_size > self.length:
                drill.length = self.length - depth

            p2 = Point(self.line.p2.x, self.line.p2.y, self.line.p2.z)
            drill.line.p2 = p2
            drill.line.setLength(drill.length)
            lines.append(drill)
            p1 = p2
        return lines

    def geom(self):
        """
        Returns a WKT representation of this drillhole.
        """
        return self.line.wkt()

    def __str__(self):
        return  f"{self.line}"

    def repr(self):
        return self.__str__()


class MineWorkingCell:
    """
    Representation of a mineworking cell and its attributes
    """

    EMPTY    = 0
    CORRIDOR = 1
    BLOCK    = 1 # Alias
    DRILL    = 2
    ENDPOINT = 3

    def __init__(self,
        col, row,
        height, width,
        level=0, padding=25,
        num_dimensions=3,
        cell_type=EMPTY):

        self.col = col
        self.row = row
        self.height = height
        self.width = width
        self.level = level
        self.type = cell_type
        self.num_dimensions = num_dimensions
        self.neighbors = {
            'n': None, # North
            's': None, # South
            'w': None, # West
            'e': None, # East
            'u': None, # Up
            'd': None  # Down
        }
        pcenter = self.__centerPoint(padding)
        self.pcenter = pcenter
        self.points = [
            [pcenter.x - width/2, pcenter.y - width/2, pcenter.z][:num_dimensions], # p1
            [pcenter.x - width/2, pcenter.y + width/2, pcenter.z][:num_dimensions], # p2
            [pcenter.x + width/2, pcenter.y - width/2, pcenter.z][:num_dimensions], # p3
            [pcenter.x + width/2, pcenter.y + width/2, pcenter.z][:num_dimensions]] # p4
        self.points_ceiling = [
            self.__ceiling(self.points[0]),
            self.__ceiling(self.points[1]),
            self.__ceiling(self.points[2]),
            self.__ceiling(self.points[3])]

    def asBlock(self, size):
        """
        Return a solid geometry that represents this cell.
        """
        x = self.pcenter.x - size/2
        y = self.pcenter.y - size/2
        z = self.pcenter.z - size/2 if self.num_dimensions == 3 else None
        z_next = z+size if z is not None else None

        points = []
        points.append(Point(x,           y,      z))
        points.append(Point(x+size,      y,      z))
        points.append(Point(x+size,      y, z_next))
        points.append(Point(     x,      y, z_next))
        points.append(Point(     x, y+size,      z))
        points.append(Point(     x, y+size, z_next))
        points.append(Point(x+size, y+size, z_next))
        points.append(Point(x+size, y+size,      z))

        order = [
            [3, 0, 4, 5, 3],
            [1, 2, 6, 7, 1],
            [0, 3, 2, 1, 0],
            [4, 7, 6, 5, 4],
            [0, 1, 7, 4, 0],
            [2, 3, 5, 6, 2]
        ]
        fmt = "POLYHEDRALSURFACEZ(" if z is not None else "POLYHEDRALSURFACE("
        for i, face in enumerate(order):
            terminator = "," if i < len(order)-1 else ""
            fmt += "(("
            for j, index in enumerate(face):
                terminator = "," if j < len(face)-1 else ""
                fmt += "{}{}".format(points[index].coords(), terminator)
            terminator = "," if i < len(order)-1 else ""
            fmt += ")){}".format(terminator)
        return fmt + ")"

    def translate(self, origin_point):
        """
        Translate coordinates by those of @origin_point.
        """
        self.pcenter.translate(origin_point)
        for p in self.points:
            p[0] += origin_point.x
            p[1] += origin_point.y
            if self.num_dimensions == 3:
                p[2] += origin_point.z
        for p in self.points_ceiling:
            p[0] += origin_point.x
            p[1] += origin_point.y
            if self.num_dimensions == 3:
                p[2] += origin_point.z

    def getWall(self, orientation):
        """
        Get the two triangles that form a wall. The @orientation
        defines whether the wall faces north, south, east or west.
        """
        t1, t2 = None, None
        p1, p2, p3, p4 = self.points
        p1_c, p2_c, p3_c, p4_c = self.points_ceiling

        if orientation == 'n':
            t1 = Triangle(Point(*p3), Point(*p1), Point(*p1_c))
            t2 = Triangle(Point(*p1_c), Point(*p3_c), Point(*p3))
        elif orientation == 's':
            t1 = Triangle(Point(*p2), Point(*p4), Point(*p4_c))
            t2 = Triangle(Point(*p4_c), Point(*p2_c), Point(*p2))
        elif orientation == 'w':
            t1 = Triangle(Point(*p1), Point(*p2), Point(*p2_c))
            t2 = Triangle(Point(*p2_c), Point(*p1_c), Point(*p1))
        elif orientation == 'e':
            t1 = Triangle(Point(*p4), Point(*p3), Point(*p3_c))
            t2 = Triangle(Point(*p3_c), Point(*p4_c), Point(*p4))
        elif orientation == 'd': # Floor
            t1 = Triangle(Point(*p1), Point(*p3), Point(*p2))
            t2 = Triangle(Point(*p2), Point(*p3), Point(*p4))
        elif orientation == 'u': # Ceiling
            t1 = Triangle(Point(*p1_c), Point(*p3_c), Point(*p2_c))
            t2 = Triangle(Point(*p2_c), Point(*p3_c), Point(*p4_c))

        return t1, t2

    def getVerticeData(self, vertices_dict):
        """
        Modify @vertices_dict in place to include a new key with the
        point coordinates that form this cell.
        """
        for triangle in self.getTriangles():
            for point in [triangle.p1, triangle.p2, triangle.p3]:
                unique_id = point.uniqueId()
                if not unique_id in vertices_dict:
                    vertices_dict[unique_id] = [point.x, point.y, point.z][:self.num_dimensions]

    def getTriangles(self):
        """
        Returns a list of all triangle objects that form this cell.
        """
        tlist = []
        for orientation in ['n', 's', 'w', 'e', 'u', 'd']:
            if self.neighbors[orientation] is None:
                t1, t2 = self.getWall(orientation)
                tlist += [t1, t2]
        return tlist

    def coords(self):
        """
        List of points that represent this cell's floor, ceiling, and walls.
        Returned as a textual string that can be merged into WKT.
        """
        mesh = []
        for orientation in ['n', 's', 'w', 'e', 'u', 'd']:
            if self.neighbors[orientation] is None:
                t1, t2 = self.getWall(orientation)
                mesh += [t1.coords(), t2.coords()]

        fmt = ""
        for t in mesh:
            fmt += "(({})),".format(t)
        return fmt[:-1]

    def geom(self):
        """
        WKT representation of this geometry
        """
        fmt = "POLYHEDRALSURFACEZ(" if self.num_dimensions == 3 else "POLYHEDRALSURFACE("
        fmt += self.coords()
        fmt += ")"
        return fmt

    def __ceiling(self, p):
        """
        Translate floor to ceiling coordinates (z axis)
        """
        return [p[0], p[1], p[2]+self.height][:self.num_dimensions]

    def setNeighbors(self, neighbors_coords):
        """
        Determine which neighboring cells we connect with.
        """
        if len(neighbors_coords) == 0:
            return
        elif len(neighbors_coords[0]) == 2:
            # There are 4 possible neighbors (east, west, north, and south)
            for (ncol, nrow) in neighbors_coords:
                if ncol > self.col:
                    self.neighbors['e'] = (ncol, nrow)
                elif ncol < self.col:
                    self.neighbors['w'] = (ncol, nrow)
                elif nrow < self.row:
                    self.neighbors['n'] = (ncol, nrow)
                elif nrow > self.row:
                    self.neighbors['s'] = (ncol, nrow)
        else:
            # The same 4 possible neighbors (east, west, north, and south)
            # plus one more one level down and another one one level up.
            for (ncol, nrow, nlevel) in neighbors_coords:
                if ncol > self.col:
                    self.neighbors['e'] = (ncol, nrow, nlevel)
                elif ncol < self.col:
                    self.neighbors['w'] = (ncol, nrow, nlevel)
                elif nrow < self.row:
                    self.neighbors['n'] = (ncol, nrow, nlevel)
                elif nrow > self.row:
                    self.neighbors['s'] = (ncol, nrow, nlevel)
                elif nlevel > self.level:
                    self.neighbors['d'] = (ncol, nrow, nlevel)
                elif nlevel < self.level:
                    self.neighbors['u'] = (ncol, nrow, nlevel)

    def __centerPoint(self, padding=5):
        """
        Create a Point geometry at the center of the cell's coordinates
        in the map.
        """
        px = self.col * self.width
        py = self.row * self.width
        pz = -self.level * self.height * padding if self.num_dimensions == 3 else None
        return Point(px, py, pz)
        
    def randomPointOnTheWall(self):
        """
        Pick a random point on the wall that faces outwards. Returns that
        point and the surface normal.
        """
        p1, p2, p3, p4 = self.points
        p1_c, p2_c, p3_c, p4_c = self.points_ceiling
        orientation_list = ['n', 's', 'w', 'e']
        random.shuffle(orientation_list)

        for orientation in orientation_list:
            if self.neighbors[orientation] is None:
                # We have a wall here
                t1, t2 = self.getWall(orientation)
                t = random.choice([t1, t2])
                return t.getRandomPoint(), t.computeNormal()

        # Surrounding cells are either at the boundary
        # of the grid or have type = CORRIDOR
        return None, None


class GeologicalShape:
    def __init__(self, xsize, ysize, zsize, max_blocks):
        self.map = np.empty((xsize, ysize, zsize), dtype=bool)
        self.xsize = xsize
        self.ysize = ysize
        self.zsize = zsize
        self.max_blocks = max_blocks
        self.block_indexes = []
        self.delaunay = None
        self.cube_size = 5

    def __str__(self):
        grid = ""
        for k in range(self.zsize):
            grid += "---- level {} ----\n".format(k)
            for i in range(self.xsize):
                for j in range(self.ysize):
                    cell = self.map[i, j, k]
                    if cell.type == MineWorkingCell.EMPTY:
                        grid += "."
                    elif cell.type == MineWorkingCell.BLOCK:
                        grid += "#"
                grid += "\n"
            grid += "\n"
        return grid

    def repr(self):
        return self.__str__()

    def possibleNeighbors(self, i, j, k):
        s = self.cube_size
        neighbors = [
            (i, j-s, k),
            (i-s, j, k), (i+s, j, k), (i, j+s, k),
            (i, j, k-s), (i, j, k+s)]
        valid_neighbors = []
        for (ni, nj, nk) in neighbors:
            if ni >= 0 and ni < self.map.shape[0] and \
                nj >= 0 and nj < self.map.shape[1] and \
                nk >= 0 and nk < self.map.shape[2]:
                valid_neighbors.append((ni, nj, nk))
        return valid_neighbors

    def create(self, seed):
        """
        Create the geological model shape and the block models
        """
        # Adjust the seed point so that the shape grows above and
        # below this level's corridor cells
        self.seed = Point(seed.x, seed.y, seed.z + (self.zsize/2.0) * self.cube_size)

        # Create the shape as a collection of regular boxes
        vertices = self.__createGeometry()

        # Compute the convex hull of the shape
        self.hull = ConvexHull(vertices)
        self.delaunay = Delaunay(self.hull.points)

    def __createGeometry(self):
        # Initialize the grid
        for k in range(0, self.map.shape[2], self.cube_size):
            for i in range(0, self.map.shape[0], self.cube_size):
                for j in range(0, self.map.shape[1], self.cube_size):
                    self.map[i,j,k] = False

        random_ysize = random.randrange(self.map.shape[1])
        random_zsize = random.randrange(self.map.shape[2])

        # Define the shape cells
        max_blocks = self.max_blocks
        for i in range(0, self.xsize, self.cube_size):
            y_min = random.randrange(random_ysize + 1)
            y_rand = random.randrange(random_ysize + 1, self.ysize + 1)
            y_max = self.ysize if random_ysize == self.ysize else y_rand

            for j in range(y_min, y_max, self.cube_size):
                z_min = random.randrange(random_zsize + 1)
                z_rand = random.randrange(random_zsize + 1, self.zsize + 1)
                z_max = self.zsize if random_zsize == self.zsize else z_rand

                for k in range(z_min, z_max, self.cube_size):
                    # We want to have a mineworking cell here
                    self.block_indexes.append((i,j,k))
                    self.map[i,j,k] = True
                    max_blocks -= 1
            if max_blocks <= 0:
                break

        # Tell each cell who its neighbors are
        vertices_dict = OrderedDict()
        for i, j, k in self.block_indexes:
            neighbors = []
            for (ni, nj, nk) in self.possibleNeighbors(i, j, k):
                if self.map[ni, nj, nk]:
                    neighbors.append((ni, nj, nk))
            if len(neighbors) > 0:
                cell = MineWorkingCell(
                    i, j,
                    self.cube_size, self.cube_size,
                    level=k,
                    padding=1,
                    cell_type=MineWorkingCell.BLOCK)
                cell.translate(self.seed)
                cell.setNeighbors(neighbors)
                cell.getVerticeData(vertices_dict)

        # Return the list of vertices that compose this shape
        return list(vertices_dict.values())

    def geom(self):
        """
        WKT representation of this geometry.
        """
        fmt = "POLYHEDRALSURFACEZ(\n"
        for index in self.delaunay.simplices:
            fmt += "(("
            for p in self.hull.points[index][0:3]:
                fmt += "{} {} {},".format(p[0], p[1], p[2])
            # Repeat the first point
            p = self.hull.points[index][0]
            fmt += "{} {} {}".format(p[0], p[1], p[2])
            fmt += ")),\n"
        return fmt[:-2] + "\n)"

    def blockmodelGeom(self):
        """
        List of WKT strings representing all blockmodels within this geometry.
        """
        fmt = ""
        for idx, (i, j, k) in enumerate(self.block_indexes):
            cell = MineWorkingCell(
                    i, j,
                    self.cube_size, self.cube_size,
                    level=k,
                    padding=1,
                    cell_type=MineWorkingCell.BLOCK)
            cell.translate(self.seed)
            terminator = "," if idx < len(self.block_indexes)-1 else ""
            fmt += "('"
            fmt += cell.asBlock(self.cube_size)
            fmt += "'){}\n".format(terminator)
        return fmt
