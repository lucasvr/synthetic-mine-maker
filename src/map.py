#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Floor creator. Orchestrates the creation of drillholes, blockmodels
# and geological shapes.

from collections import defaultdict
from src.geometry import *
from src.objects import *
import concurrent.futures
import numpy as np
import random
import math
import sys

class Graph:
    """
    Graph class. Used to detect cycles during the creation of the map.
    """
    def __init__(self, num_vertices):
        self.num_vertices = num_vertices
        self.graph = defaultdict(list)

    def connect(self, from_vertex, to_vertex):
        """
        Create an undirected connection between two vertices.
        """
        self.graph[from_vertex].append(to_vertex)
        self.graph[to_vertex].append(from_vertex)

    def disconnect(self, from_vertex, to_vertex):
        """
        Disconnect an existing connection between two vertices.
        """
        self.graph[from_vertex].remove(to_vertex)
        self.graph[to_vertex].remove(from_vertex)

    def hasCycle(self, vertex, visited, parent):
        """
        Check if the graph has any cycles.
        """
        visited[vertex] = True
        for i in self.graph[vertex]:
            if not visited[i]:
                if self.hasCycle(i, visited, vertex):
                    return True
            elif parent != i:
                return True
        return False

    def mayConnect(self, from_node, to_node):
        """
        Check if adding a new connection to the graph will result in a
        cycle or not.
        """
        if from_node in self.graph and to_node in self.graph[from_node]:
            # Connection already exists
            return False
        ret = True
        self.connect(from_node, to_node)
        visited = [False] * self.num_vertices
        for i in range(self.num_vertices):
            if not visited[i]:
                if self.hasCycle(i, visited, -1):
                    ret = False
                    break
        self.disconnect(from_node, to_node)
        return ret


class MapGen:
    def __init__(self, size_generator, shape_size_generators, 
                 cols=100,
                 rows=45, min_seeds=10, max_seeds=20,
                 elevator_coords=(0, 0),
                 num_drills=100,
                 cell_height=3, cell_width=4,
                 drill_ival_length=10,
                 num_shapes=3,
                 num_dimensions=3):
        self.cols = cols
        self.rows = rows
        self.drill_interval_length = drill_ival_length
        self.map = np.empty((cols, rows), dtype=object)
        self.num_rooms = random.randint(min_seeds, max_seeds)
        self.elevator_coords = elevator_coords
        self.num_drills = num_drills
        self.num_shapes = num_shapes
        self.cell_height = cell_height
        self.cell_width = cell_width
        self.size_generator = size_generator
        self.shape_size_generators = shape_size_generators
        self.num_dimensions = num_dimensions
        # The following are variables we want to share with the caller
        self.corridor = []
        self.drills = []
        self.shapes = []
        self.elevator = None

    def __str__(self):
        drill_locations = {}
        for drill in set(self.drills):
            col, row = drill.col, drill.row
            drill_locations[(col, row)] = len([
                x for x in self.drills
                if x.col == col and x.row == row])

        grid = ""
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self.map[col,row]
                if (col,row) in drill_locations:
                    grid += str(drill_locations[(col,row)])
                elif cell == None or cell.type == MineWorkingCell.EMPTY:
                    grid += "."
                elif cell.type == MineWorkingCell.CORRIDOR:
                    grid += "#"
                elif cell.type == MineWorkingCell.DRILL:
                    grid += "!"
                elif cell.type == MineWorkingCell.ENDPOINT:
                    grid += "x"
            grid += "\n"
        return grid

    def repr(self):
        return self.__str__()

    def create(self, level, num_levels):
        """
        This function does the bulk of the synthetic dataset generation
        processing. It begins by creating the endpoints (or "rooms" in
        a dungeon idiom) and by connecting them with corridors. Next,
        it creates drill holes starting at some random walls of these
        corridors. Lastly, geological shapes and block models are
        generated.
        @level determines how deep underground this level is found.
        """
        print("Processing level {}".format(level))
        self.__createCorridors(level)
        if level > 0 and level == num_levels-1:
            self.__createElevator(num_levels)
        self.__createDrillholes()

        # Pick the endpoint of some random drillholes as seeds for the
        # starting point of the geological shapes.
        seeds = [d.line.p2 for d in random.sample(self.drills, self.num_shapes)]

        # Launch parallel instances of the geological shape creator. Note
        # that because shapes can be very large, it is possible to exceed
        # the amount of space reserved for IPC shared memory. Our workaround
        # is to use a thread pool (at the expense of having to be ruled by
        # Python's Global Interpreter Lock).
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for shape in executor.map(self.__createGeologicalShape, seeds):
                self.shapes.append(shape)

    def __createCorridors(self, level):
        # Initialize the map
        for row in range(self.rows):
            for col in range(self.cols):
                self.map[col,row] = None

        # Create the endpoints
        endpoints = [self.elevator_coords] + [
            (random.randint(0, self.cols-1), random.randint(0, self.rows-1))
            for x in range(self.num_rooms-1)]
        for col, row in endpoints:
            self.map[col,row] = MineWorkingCell(
                col, row, self.cell_height, self.cell_width,
                level, cell_type=MineWorkingCell.ENDPOINT)

        # Connect endpoints using straight lines, populating the
        # @self.corridor list as outcome.
        graph = Graph(len(endpoints))
        ctype = MineWorkingCell.CORRIDOR
        for i, (col, row) in enumerate(endpoints):
            neighbor = self.nearestNeighbor(endpoints, i, [i])
            ncol, nrow = endpoints[neighbor]
            if graph.mayConnect(neighbor, i):
                graph.connect(neighbor, i)
                self.makeCorridor((col,row), (ncol,nrow), level, ctype)
            else:
                # Find another neighbor to connect with
                blacklist = [i, neighbor]
                while len(blacklist) < len(endpoints):
                    neighbor = self.nearestNeighbor(endpoints, i, blacklist)
                    ncol, nrow = endpoints[neighbor]
                    if graph.mayConnect(neighbor, i):
                        graph.connect(neighbor, i)
                        self.makeCorridor((col,row), (ncol,nrow), level, ctype)
                        break
                    blacklist.append(neighbor)

        # Tell each cell who its neighbors are
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self.map[col, row]
                if cell is not None:
                    neighbors = []
                    for (ncol, nrow) in self.possibleNeighbors(col, row):
                        if self.map[ncol, nrow] != None:
                            neighbors.append((ncol, nrow))
                    cell.setNeighbors(neighbors)

    def __createElevator(self, num_levels):
        col, row = self.elevator_coords
        padding = -25
        self.elevator = MineWorkingCell(
            col, row,
            self.cell_height * (num_levels-1) * padding,
            self.cell_width,
            level=0,
            padding=1,
            num_dimensions=self.num_dimensions,
            cell_type=MineWorkingCell.CORRIDOR)

    def __createDrillholes(self):
        # Distribute drill holes on corridor cells, populating the
        # @self.drills list as it iterates the corridor cells.
        drill_distribution = [
            random.randint(0, len(self.corridor)-1)
            for x in range(self.num_drills)]

        for corridor_idx in drill_distribution:
            cell = self.corridor[corridor_idx]
            for i in range(drill_distribution.count(corridor_idx)):
                pcenter, normal = cell.randomPointOnTheWall()
                if pcenter is not None:
                    drillhole = DrillHole(
                        pcenter,
                        normal,
                        cell.col,
                        cell.row,
                        self.size_generator,
                        self.drill_interval_length,
                        self.num_dimensions)
                    drillhole.create()
                    self.drills.append(drillhole)

    def __createGeologicalShape(self, seed):
        xsize = math.ceil(self.shape_size_generators[0].generate(1)[0])
        ysize = math.ceil(self.shape_size_generators[1].generate(1)[0])
        if len(self.shape_size_generators) == 3:
            zsize = math.ceil(self.shape_size_generators[2].generate(1)[0])
            max_blocks = xsize * ysize * zsize
        else:
            zsize = None
            max_blocks = xsize * ysize
        shape = GeologicalShape(xsize, ysize, zsize, max_blocks)
        shape.create(seed)
        return shape

    def nearestNeighbor(self, coords, my_index, blacklist):
        """
        Compute the euclidean distance of coords[my_index] and all other
        members. Returns the index of the element with the shortest distance
        to my_index.
        """
        min_index, min_distance = 0, 999999999
        my_col, my_row = coords[my_index]
        for i, (col, row) in enumerate(coords):
            if i in blacklist:
                continue
            distance = math.sqrt((my_col-col)**2 + (my_row-row)**2)
            if distance < min_distance:
                min_index, min_distance = i, distance
        return min_index

    def possibleNeighbors(self, col, row):
        """
        Detect valid neighbors. Note that we simply connect with north,
        south, west and east.
        """
        neighbors = [(col, row-1), (col-1, row), (col+1, row), (col, row+1)]
        valid_neighbors = []
        for (ncol, nrow) in neighbors:
            if ncol >= 0 and ncol < self.cols and \
                nrow >= 0 and nrow < self.rows:
                valid_neighbors.append((ncol, nrow))
        return valid_neighbors

    def makeCorridor(self, from_coords, to_coords, level, value):
        """
        Connect two given cells by creating a corridor between
        them. The resulting cells are appended to @self.corridor
        and the grid at @self.map is updated accordingly.
        """
        h, w = self.cell_height, self.cell_width
        from_col, from_row = from_coords
        to_col, to_row = to_coords

        direction = 1 if to_col > from_col else -1
        for col in range(from_col, to_col+(1*direction), direction):
            cell = self.map[col, from_row]
            if cell == None:
                cell = self.map[col, from_row] = MineWorkingCell(
                    col, from_row, self.cell_height, self.cell_width, level)
            cell.type = value
            self.corridor.append(cell)

        direction = 1 if to_row > from_row else -1
        for row in range(from_row, to_row+(1*direction), direction):
            cell = self.map[to_col, row]
            if cell == None:
                cell = self.map[to_col, row] = MineWorkingCell(
                    to_col, row, self.cell_height, self.cell_width, level)
            cell.type = value
            self.corridor.append(cell)
