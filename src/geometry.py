#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Geometry types and their WKT generators.

import random
from math import sqrt, sin, cos

class Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        if self.z is not None:
            return f"x={self.x} y={self.y} z={self.z}"
        return f"x={self.x} y={self.y}"

    def __repr__(self):
        return self.__str__()

    def __truediv__(self, other):
        x = self.x / other
        y = self.y / other
        z = self.z / other if self.z is not None else None
        return Point(x, y, z)

    def __floordiv__(self, other):
        return self.__truediv__(other)

    def __mul__(self, other):
        x = self.x * other
        y = self.y * other
        z = self.z * other if self.z is not None else None
        return Point(x, y, z)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        z = self.z + other.z if self.z is not None else None
        return Point(x, y, z)

    def __sub__(self, other):
        x = self.x - other.x
        y = self.y - other.y
        z = self.z - other.z if self.z is not None else None
        return Point(x, y, z)

    def uniqueId(self):
        p1, p2, p3 = 73856093, 19349663, 83492791
        if self.z is not None:
            return int(p1*self.x) ^ int(p2*self.y) ^ int(p3*self.z)
        return int(p1*self.x) ^ int(p2*self.y)

    def translate(self, origin):
        self.x += origin.x
        self.y += origin.y
        if self.z is not None:
            self.z += origin.z

    def coords(self):
        if self.z is not None:
            return "{} {} {}".format(self.x, self.y, self.z)
        return "{} {}".format(self.x, self.y)

    def wkt(self):
        if self.z is not None:
            return "POINTZ ({})".format(self.coords())
        return "POINT ({})".format(self.coords())


class Line:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    def setLength(self, new_length):
        x, y, z = self.__translatedCoords()
        cur_length = sqrt(x**2 + y**2 + z**2)
        if cur_length == 0.0:
            cur_length = 1.0
        self.p2.x = self.p1.x + (x / cur_length) * new_length
        self.p2.y = self.p1.y + (y / cur_length) * new_length
        if self.p1.z is not None:
            self.p2.z = self.p1.z + (z / cur_length) * new_length

    def rotate(self, x_angle=None, y_angle=None, z_angle=None):
        """
        Rotate the line around the requested angle(s)
        """
        if x_angle:
            x, y, z = self.__translatedCoords()
            self.p2.y = self.p1.x + (y*cos(x_angle) - z*sin(x_angle))
            self.p2.z = self.p1.z + (y*sin(x_angle) + z*cos(x_angle))
        if y_angle:
            x, y, z = self.__translatedCoords()
            self.p2.x = self.p1.x + (x*cos(y_angle) - z*sin(y_angle))
            self.p2.z = self.p1.z + (-x*sin(y_angle) + z*cos(y_angle))
        if z_angle:
            x, y, z = self.__translatedCoords()
            self.p2.x = self.p1.x + (x*cos(z_angle) - y*sin(z_angle))
            self.p2.y = self.p1.y + (x*sin(z_angle) - y*cos(z_angle))

    def __translatedCoords(self):
        if self.p1.z is not None:
            return (
                self.p2.x - self.p1.x,
                self.p2.y - self.p1.y,
                self.p2.z - self.p1.z
            )
        else:
            return (
                self.p2.x - self.p1.x,
                self.p2.y - self.p1.y,
                0
            )
    def coords(self):
        return "{}, {}".format(self.p1.coords(), self.p2.coords())

    def wkt(self):
        if self.p1.z is not None:
            return "LINESTRINGZ ({})".format(self.coords())
        return "LINESTRING ({})".format(self.coords())


class Triangle:
    def __init__(self, p1, p2, p3):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.normal = None

    def subdivide(self, preserve_shape=True):
        """
        Subdivide the triangle into smaller parts. We pick a random
        point on the triangle surface as pivot and create 6 smaller
        triangles that share that same pivot point. If @preserve_shape
        is true, then the height of the pivot is not changed. Otherwise,
        a random value is added to its height so that the final
        geometry looks more fancy.
        """
        pivot = self.getRandomPoint()
        if not preserve_shape:
            # Determine a new height for the pivot
            normal = self.computeNormal()
            pivot2 = Point(
                pivot.x + normal.x,
                pivot.y + normal.y,
                pivot.z + normal.z if pivot.z is not None else None)
            line = Line(pivot, pivot2)
            line.setLength(random.uniform(0.0, 0.25))
            pivot = line.p2

        p1, p2, p3 = self.p1, self.p2, self.p3
        t1 = Triangle(p1, p1+(p2-p1)/2, pivot)
        t2 = Triangle(p1+(p2-p1)/2, p2, pivot)
        t3 = Triangle(p2, p2+(p3-p2)/2, pivot)
        t4 = Triangle(p2+(p3-p2)/2, p3, pivot)
        t5 = Triangle(p3, p1+(p3-p1)/2, pivot)
        t6 = Triangle(p1+(p3-p1)/2, p1, pivot)
        return [t1, t2, t3, t4, t5, t6]

    def computeNormal(self):
        """
        Return the normal to the triangle surface.
        """
        if self.normal is None:
            v = self.p2 - self.p1
            w = self.p3 - self.p1
            # Compute the cross product
            nx = (v.y * w.z) - (w.y * v.z)
            ny = (v.z * w.x) - (w.z * v.x)
            nz = (v.x * w.y) - (w.x * v.y)
            self.normal = Point(nx, ny, nz)
        return self.normal

    def getRandomPoint(self):
        """
        Get a pseudo-random point that lies in this triangle
        """
        a = random.uniform(0, 1)
        b = random.uniform(0, 1)
        px = (1.0 - sqrt(a)) * self.p1.x + \
            (sqrt(a) * (1.0 - b)) * self.p2.x + \
            (sqrt(a) * b) * self.p3.x
        py = (1.0 - sqrt(a)) * self.p1.y + \
            (sqrt(a) * (1.0 - b)) * self.p2.y + \
            (sqrt(a) * b) * self.p3.y
        pz = (1.0 - sqrt(a)) * self.p1.z + \
            (sqrt(a) * (1.0 - b)) * self.p2.z + \
            (sqrt(a) * b) * self.p3.z
        return Point(px, py, pz)

    def coords(self):
        return "{}, {}, {}, {}".format(
            self.p1.coords(),
            self.p2.coords(),
            self.p3.coords(),
            self.p1.coords())

    def wkt(self):
        return "POLYGONZ ({})".format(self.coords())


class Tetrahedron:
    def __init__(self, pcenter, xsize, ysize, zsize):
        self.points = [Point(pcenter.x, pcenter.y, pcenter.z) for x in range(4)]

        xsize = xsize/2.0
        ysize = ysize/2.0
        zsize = zsize/2.0

        # 2nd point (x+D, y-D, z)
        self.points[1].x += xsize
        self.points[1].y -= ysize

        # 3rd point (x-D, y-D, z)
        self.points[2].x -= xsize
        self.points[2].y -= ysize

        # 4th point (x+d, y-D, z+D)
        self.points[3].y -= ysize
        self.points[3].z += zsize

        # Orientation
        self.order = [
            [0, 2, 1, 0],
            [0, 1, 3, 0],
            [0, 3, 2, 0],
            [1, 2, 3, 1]
        ]

    def coords(self, indexes):
        fmt = ""
        for i in indexes:
            fmt += "{},".format(self.points[i].coords())
        return fmt[:-1]

    def wkt(self):
        fmt = "POLYHEDRALSURFACEZ("
        for face in self.order:
            fmt += "(({})),".format(self.coords(face))
        return fmt[:-1] + ")"


class Hexahedron:
    def __init__(self, pcenter, xsize, ysize, zsize):
        self.points = [Point(pcenter.x, pcenter.y, pcenter.z) for x in range(8)]

        self.points[1].x += xsize

        self.points[2].x += xsize
        self.points[2].z += zsize

        self.points[3].z += zsize

        self.points[4].y += ysize

        self.points[5].y += ysize
        self.points[5].z += zsize

        self.points[6].x += xsize
        self.points[6].y += ysize
        self.points[6].z += zsize

        self.points[7].x += xsize
        self.points[7].y += ysize

        # Orientation
        self.order = [
            [0, 1, 7, 4, 0],
            [1, 2, 6, 7, 1],
            [2, 3, 5, 6, 2],
            [3, 0, 4, 5, 3],
            [4, 7, 6, 5, 4],
            [0, 3, 2, 1, 0]
        ]

    def coords(self, indexes):
        fmt = ""
        for i in indexes:
            fmt += "{},".format(self.points[i].coords())
        return fmt[:-1]

    def wkt(self):
        fmt = "POLYHEDRALSURFACEZ("
        for face in self.order:
            fmt += "(({})),".format(self.coords(face))
        return fmt[:-1] + ")"
