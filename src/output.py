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
            ("points", self.writePoints),
            ("geological_shapes", self.writeGeologicalShapes),
            ("blockmodel", self.writeBlockModel)
        ])
        for table in functions.keys():
            print("Exporting results: level {}, table {}".format(level, table))
            fname = "{}.level_{:02d}.sql".format(table, level)
            path = os.path.join(output_dir, fname)
            functions[table](the_map, f"{self.schema}.{table}", path)

    def __create(self, path, table):
        f = open(path, "w")
        layout = "(id bigserial, geom geometry(GeometryZ))"
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
        f = self.__create(path, table)
        f.write("('POLYHEDRALSURFACEZ(\n")
        for i, cell in enumerate(the_map.corridor):
            terminator = "," if i < len(the_map.corridor)-1 else ""
            f.write("{}{}\n".format(cell.coords(), terminator))
        f.write(")')")
        if the_map.elevator is not None:
            f.write(",\n")
            f.write("('POLYHEDRALSURFACEZ(\n")
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
        f = self.__create(path, table)
        f.write("('MULTILINESTRINGZ(\n")
        for i, drill in enumerate(the_map.drills):
            terminator = "," if i < len(the_map.drills)-1 else ""
            coords = drill.geom().replace("LINESTRINGZ", "")
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

    def writePoints(self, the_map, table, path):
        """
        Write drill holes as POINTZ objects.
        """
        f = self.__create(path, table)
        for i, drill in enumerate(the_map.drills):
            terminator = "," if i < len(the_map.drills)-1 else ""
            p1, p2 = drill.line.p1, drill.line.p2
            f.write("('{}'),('{}'){}\n".format(p1.wkt(), p2.wkt(), terminator))
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


class WKT:
    def write(self, level, the_map, output_dir):
        """
        Create a set of output files in plain WKT format.
        """
        functions = OrderedDict([
            ("mineworking", self.writeMineWorking),
            ("drillholes", self.writeDrillHoles),
            ("multiline_drillholes", self.writeMultiLineDrillHoles),
            ("segments", self.writeSegments),
            ("points", self.writePoints),
            ("geological_shapes", self.writeGeologicalShapes),
            ("blockmodel", self.writeBlockModel)
        ])
        for table in functions.keys():
            print("Exporting results: level {}, {}".format(level, table))
            fname = "{}.level_{:02d}.wkt".format(table, level)
            with open(os.path.join(output_dir, fname), "w") as f:
                functions[table](the_map, f)

    def writeMineWorking(self, the_map, f):
        """
        Write the mine working (level map).
        """
        f.write("POLYHEDRALSURFACEZ(")
        for i, cell in enumerate(the_map.corridor):
            terminator = "," if i < len(the_map.corridor)-1 else ""
            f.write("{}{}".format(cell.coords(), terminator))
        f.write(")\n")
        if the_map.elevator is not None:
            f.write("POLYHEDRALSURFACEZ(")
            f.write("{}".format(the_map.elevator.coords()))
            f.write(")\n")

    def writeDrillHoles(self, the_map, f):
        """
        Write drill holes as a series of LineString objects.
        """
        for i, drill in enumerate(the_map.drills):
            f.write("{}\n".format(drill.geom()))

    def writeMultiLineDrillHoles(self, the_map, f):
        """
        Write drill holes as a single large MultiLineString.
        This is handy when all drill holes need to be rendered
        together.
        """
        f.write("MULTILINESTRINGZ(")
        for i, drill in enumerate(the_map.drills):
            terminator = "," if i < len(the_map.drills)-1 else ""
            coords = drill.geom().replace("LINESTRINGZ", "")
            f.write("{}{}".format(coords, terminator))
        f.write(")\n")

    def writeSegments(self, the_map, f):
        """
        Write drill hole segments.
        """
        for i, drill in enumerate(the_map.drills):
            for j, segment in enumerate(drill.segments()):
                f.write("{}\n".format(segment.geom()))

    def writePoints(self, the_map, f):
        """
        Write drill holes as POINTZ objects.
        """
        for i, drill in enumerate(the_map.drills):
            p1, p2 = drill.line.p1, drill.line.p2
            f.write("{}\n{}\n".format(p1.wkt(), p2.wkt()))

    def writeGeologicalShapes(self, the_map, f):
        """
        Write geological shapes.
        """
        for i, shape in enumerate(the_map.shapes):
            f.write("{}\n".format(shape.geom(postgis_output=False)))

    def writeBlockModel(self, the_map, f):
        """
        Write block model entities.
        """
        for i, shape in enumerate(the_map.shapes):
            f.write("{}\n".format(shape.blockmodelGeom(postgis_output=False)))
