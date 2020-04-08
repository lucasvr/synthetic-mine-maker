#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Output producer.

from collections import OrderedDict
import os

class PostGIS:
    def __init__(self):
        self.schema = "synthetic_mine"
        self.num_dimensions = 3

    def write(self, level, the_map, num_dimensions, output_dir):
        """
        Create a set of output files with instructions on how to
        populate a PostGIS database with the generated geometries.
        """
        self.num_dimensions = num_dimensions
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
            fname = "{}.level_{:02d}.sql".format(table, level)
            path = os.path.join(output_dir, fname)
            functions[table](the_map, f"{self.schema}.{table}", path)

    def __create(self, path, table):
        datatype = "GeometryZ" if self.num_dimensions == 3 else "Geometry"
        f = open(path, "w")
        layout = f"(id bigserial, geom geometry({datatype}))"
        f.write(f"CREATE SCHEMA IF NOT EXISTS {self.schema};\n")
        f.write(f"CREATE TABLE IF NOT EXISTS {table}{layout};\n")
        f.write(f"INSERT INTO {table}(geom) VALUES\n")
        return f

    def __close(self, table, f):
        id_idx = "{}_id_idx".format(table.split(".")[1])
        geom_idx = "{}_geom_idx".format(table.split(".")[1])
        f.write(";\n")
        f.write(f"CREATE INDEX IF NOT EXISTS {id_idx} ON {table}(id);\n")
        f.write(f"CREATE INDEX IF NOT EXISTS {geom_idx} ON {table} USING GIST(geom);\n")
        f.close()

    def writeMineWorking(self, the_map, table, path):
        """
        Write the mine working (level map).
        """
        datatype = "POLYHEDRALSURFACEZ" if self.num_dimensions == 3 else "POLYHEDRALSURFACE"
        f = self.__create(path, table)
        f.write(f"('{datatype}(\n")
        for i, cell in enumerate(the_map.corridor):
            terminator = "," if i < len(the_map.corridor)-1 else ""
            f.write("{}{}\n".format(cell.coords(), terminator))
        f.write(")')")
        if the_map.elevator is not None:
            f.write(",\n")
            f.write(f"('{datatype}(\n")
            f.write("{}\n".format(the_map.elevator.coords()))
            f.write(")')")
        self.__close(table, f)

    def writeDrillHoles(self, the_map, table, path):
        """
        Write drill holes as a series of LineString objects.
        """
        f = self.__create(path, table)
        for i, drill in enumerate(the_map.drills):
            terminator = "," if i < len(the_map.drills)-1 else ""
            f.write("('{}'){}\n".format(drill.geom(), terminator))
        self.__close(table, f)

    def writeMultiLineDrillHoles(self, the_map, table, path):
        """
        Write drill holes as a single large MultiLineString.
        This is handy when all drill holes need to be rendered
        together.
        """
        datatype = "MULTILINESTRINGZ" if self.num_dimensions == 3 else "MULTILINESTRING"
        pattern = "LINESTRINGZ" if self.num_dimensions == 3 else "LINESTRING"
        f = self.__create(path, table)
        f.write(f"('{datatype}(\n")
        for i, drill in enumerate(the_map.drills):
            terminator = "," if i < len(the_map.drills)-1 else ""
            coords = drill.geom().replace(f"{pattern}", "")
            f.write("{}{}\n".format(coords, terminator))
        f.write(")')")
        self.__close(table, f)

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
        self.__close(table, f)

    def writeGeologicalShapes(self, the_map, table, path):
        """
        Write geological shapes.
        """
        f = self.__create(path, table)
        for i, shape in enumerate(the_map.shapes):
            terminator = "," if i < len(the_map.shapes)-1 else ""
            f.write("('{}'){}\n".format(shape.geom(), terminator))
        self.__close(table, f)

    def writeBlockModel(self, the_map, table, path):
        """
        Write block model entities.
        """
        f = self.__create(path, table)
        for i, shape in enumerate(the_map.shapes):
            terminator = "," if i < len(the_map.shapes)-1 else ""
            f.write("{}{}\n".format(shape.blockmodelGeom(), terminator))
        self.__close(table, f)
