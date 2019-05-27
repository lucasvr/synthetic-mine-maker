#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Output producer.

from collections import OrderedDict
import os

class PostGIS:
    def __init__(self):
        self.schema = "synthetic_mine"

    def write(self, level, the_map, output_dir):
        """
        Create a set of output files with instructions on how to
        populate a PostGIS database with the generated geometries.
        """
        functions = OrderedDict([
            ("mineworking", self.writeMineWorking),
            ("drillholes", self.writeDrillHoles),
            ("multiline_drillholes", self.writeMultiLineDrillHoles),
            ("segments", self.writeSegments),
            ("geological_shapes", self.writeGeologicalShapes),
            ("blockmodel", self.writeBlockModel)
        ])
        for table in functions.keys():
            print("Exporting results: level {}, table {}".format(level, table))
            fname = "{}.level_{:02d}.dump".format(table, level)
            path = os.path.join(output_dir, fname)
            functions[table](the_map, f"{self.schema}.{table}", path)

    def __create(self, path, table):
        f = open(path, "w")
        layout = "(id bigserial, geom geometry(GeometryZ))"
        f.write(f"CREATE SCHEMA IF NOT EXISTS {self.schema};\n")
        f.write(f"CREATE TABLE IF NOT EXISTS {table}{layout};\n")
        f.write(f"INSERT INTO {table}(geom) VALUES\n")
        return f

    def __close(self, f):
        f.write(";\n")
        f.close()

    def writeMineWorking(self, the_map, table, path):
        """
        Write the mine working (level map).
        """
        f = self.__create(path, table)
        f.write("('POLYHEDRALSURFACEZ(\n")
        for i, cell in enumerate(the_map.corridor):
            terminator = "," if i < len(the_map.corridor)-1 else ""
            f.write("{}{}\n".format(cell.coords(), terminator))
        f.write(")')")
        self.__close(f)

    def writeDrillHoles(self, the_map, table, path):
        """
        Write drill holes as a series of LineString objects.
        """
        f = self.__create(path, table)
        for i, drill in enumerate(the_map.drills):
            terminator = "," if i < len(the_map.drills)-1 else ""
            f.write("('{}'){}\n".format(drill.geom(), terminator))
        self.__close(f)

    def writeMultiLineDrillHoles(self, the_map, table, path):
        """
        Write drill holes as a single large MultiLineString.
        This is handy when all drill holes need to be rendered
        together.
        """
        f = self.__create(path, table)
        f.write("('MULTILINESTRINGZ(\n")
        for i, drill in enumerate(the_map.drills):
            terminator = "," if i < len(the_map.drills)-1 else ""
            coords = drill.geom().replace("LINESTRINGZ", "")
            f.write("{}{}\n".format(coords, terminator))
        f.write(")')")
        self.__close(f)

    def writeSegments(self, the_map, table, path):
        """
        Write drill hole segments.
        """
        f = self.__create(path, table)
        for i, drill in enumerate(the_map.drills):
            segments = drill.segments()
            for j, segment in enumerate(segments):
                last = i == len(the_map.drills)-1 and j == len(segments)-1
                terminator = "," if not last else ""
                f.write("('{}'){}\n".format(segment.geom(), terminator))
        self.__close(f)

    def writeGeologicalShapes(self, the_map, table, path):
        """
        Write geological shapes.
        """
        f = self.__create(path, table)
        for i, shape in enumerate(the_map.shapes):
            terminator = "," if i < len(the_map.shapes)-1 else ""
            f.write("('{}'){}\n".format(shape.geom(), terminator))
        self.__close(f)

    def writeBlockModel(self, the_map, table, path):
        """
        Write block model entities.
        """
        f = self.__create(path, table)
        for i, shape in enumerate(the_map.shapes):
            terminator = "," if i < len(the_map.shapes)-1 else ""
            f.write("{}{}\n".format(shape.blockmodelGeom(), terminator))
        self.__close(f)
