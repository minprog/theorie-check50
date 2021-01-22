#!/usr/bin/env python3
"""
This file uses check50 to check the output of an Chips & Circuits solution. It
does so by doing the following tests in this order:
    - Check if output.csv exits
    - Check if the file has valid values and is structured correctly
    - Check if all connections from the designated netlist have been made.
    - Check if coordinates of the nets are in the wire lists
    - Check if the wires do not overlap
    - Check if the wires actually connect the designated nets
    - Check if the length in output.csv is equal to the computed wire length
"""

import check50
import pandas as pd
import numpy as np

import collections
import csv
import logging
import os
import re


@check50.check()
def exists():
    """Check if output.csv exists."""
    check50.exists("output.csv")
    check50.include("data/")


@check50.check(exists)
def check_file():
    """The structure and values of output.json are correct."""
    # Check if output.csv has content.
    if os.stat("output.csv").st_size == 0:
        raise check50.Failure("Output.csv may not be empty. Provide at least "
                              "an header row and a row with the used chip and "
                              "wire length.")

    with open("output.csv") as csvfile:
        df = pd.read_csv(csvfile)

        # Check header for correct format.
        if list(df) != ["net", "wires"]:
            raise check50.Failure("Expected header of the csv to be "
                                  "'net,wires'")

        # Check footer for correct format.
        if len(df) < 1 or df["net"].iloc[-1][:5] != "chip_" or \
                df["net"].iloc[-1][6:11] != "_net_":

            raise check50.Failure("Expected last row of the csv to be "
                                  "'chip_<int>_net_<int>,<int>'")

        try:
            int(df["wires"].iloc[-1])
            chip_id = int(df["net"].iloc[-1][5:6])
            net_id = int(df["net"].iloc[-1][11:])

            # Check if chip in footer is either 1 or 2.
            if chip_id not in [0, 1, 2]:
                raise check50.Failure(f"Expected chip number to be 0, 1 or 2, "
                                      f"but found:\n\tchip_{chip_id} \ton row "
                                      f"{len(df) + 1}")

            if net_id not in list(range(1, 10)):
                raise check50.Failure(f"Expected netlist number to be 1 till 9,"
                                      f" but found:\n\tnet_{net_id} \ton row "
                                      f"{len(df) + 1}")
        except ValueError:
            raise check50.Failure("Expected last row of the csv to be "
                                  "'chip_<int>_net_<int>,<int>'")

        # Stop checking if no objects are in the output file.
        if len(df) == 1:
            return

        # Check if all connections are of correct types.
        pattern = r"^\(\d+,\d+\)$"
        net_bools = np.array(list(map(lambda x: bool(re.match(pattern, x)),
                                      df["net"][:-1])))

        if False in net_bools:
            idxs = np.where(net_bools == False)[0]
            error = "Invalid coordinates for nets found.\n    Expected " \
                    "coordinates with format '(<int>,<int>)', but found:\n"

            for idx in idxs:
                error = "".join([error, f"\t'{df['net'][idx]}' \ton row "
                                        f"{idx + 2}\n"])

            raise check50.Failure(error)

        # Check if all the wires are of correct types.
        pattern = r"^\d+,\d+(,\d+)?$"
        coords = [x[2:-2].split("),(") for x in df["wires"][:-1]]
        wire_bools = [list(map(lambda x: bool(re.match(pattern, x)), c))
                      for c in coords]
        wire_bools = [(i, "".join(["(", coords[i][j], ")"]))
                      for i, bools in enumerate(wire_bools)
                      for j, b in enumerate(bools) if not b]

        if wire_bools:
            error = "Invalid coordinates for wires found.\n    Expected " \
                    "coordinates with format '(<int>,<int>[,<int>])', but " \
                    "found:\n"

            for idx, coord in wire_bools:
                error = "".join([error, f"\t'{coord}' \ton row "
                                        f"{idx + 2}\n"])

            raise check50.Failure(error)


@check50.check(check_file)
def is_solution():
    """output.csv is a solution for the netlist + print"""
    with open("output.csv") as f:
        data = list(csv.DictReader(f))

    # Parse the last line containing
    config = data[-1]["net"]
    cost = data[-1]["wires"]    
    chip_id = config[len("chip_")]
    net_id = config[-1]

    # Remove the last line
    data = data[:-1]

    # Check whether the netlist in output.csv contains all and only nets from the specified netlist
    check_netlist_complete(chip_id, net_id, data)

    # Check whether the grid is valid
    grid = check_grid(chip_id, data)

    # For debugging purposes, log the grid to debug. Set this with "--log-level debug" when running check50
    logging.getLogger("check50").debug(grid.pretty_print())

    # Pass the cost of the grid to following checks
    return grid.get_cost()


def check_netlist_complete(chip_id, net_id, output_data):
    netlist_gates = set()
    with open(f"data/chip_{chip_id}/netlist_{net_id}.csv") as f:
        for line in csv.DictReader(f):
            gate_a_id = int(line["chip_a"])
            gate_b_id = int(line["chip_b"])
            netlist_gates.add((gate_a_id, gate_b_id))

    output_gates = []
    for line in output_data:
        gate_a_id, gate_b_id = line["net"].strip("()").split(",")
        gate_a_id = int(gate_a_id)
        gate_b_id = int(gate_b_id)
        output_gates.append((gate_a_id, gate_b_id))

    # output.csv dictates the order of nets
    for a, b in output_gates:
        if (a, b) not in netlist_gates and (b, a) in netlist_gates:
            netlist_gates.remove((b,a))
            netlist_gates.add((a,b))

    # Ensure there are no duplicate gates in output.csv
    if len(set(output_gates)) != len(output_gates):
        seen = set()
        duplicates = []
        for gate in output_gates:
            if gate not in seen:
                seen.add(gate)
            else:
                duplicates.append(gate)
        raise check50.Failure(f"Duplicate gates in output.csv, namely: {duplicates}")

    output_gates = set(output_gates)

    # Ensure all gates in output are also in the netlist and vice versa
    if netlist_gates != output_gates:
        missing_gates = netlist_gates - output_gates
        if missing_gates:
            raise check50.Failure(f"Missing the following net in output.csv: {missing_gates}")
        
        extra_gates = output_gates - netlist_gates
        raise check50.Failure(f"Found additional nets in output.csv that are not in the netlist: {extra_gates}")


def check_grid(chip_id, output_data):
    # Initiate the grid
    grid = Grid(f"data/chip_{chip_id}/print_{chip_id}.csv")

    # Create the nets from output.csv
    nets = []
    for line in output_data:
        gate_ids = line["net"].strip("()").split(",")
        gate_a = grid.get_gate(gate_ids[0])
        gate_b = grid.get_gate(gate_ids[1])

        wire_strings = re.findall(r"[0-9]+,[0-9]+(?:,[0-9]+)?", line["wires"])
        wires = [Wire(*ws.split(",")) for ws in wire_strings]

        nets.append(Net(gate_a, gate_b, wires))

    # Place the nets on the grid
    for net in nets:
        grid.place_net(net)

    return grid


@check50.check(is_solution)
def is_cost_correct(cost):
    """The cost is correct"""
    with open("output.csv") as f:
        data = list(csv.DictReader(f))
        output_cost = int(data[-1]["wires"])

    if output_cost != cost:
        raise check50.Failure(f"The cost in output.csv ({output_cost}) is incorrect, the actual cost is {cost}")


class UnconnectedNetError(check50.Failure):
    pass

class InteruptedNetError(check50.Failure):
    pass

class OccupiedByGateError(check50.Failure):
    pass


class Gate:
    def __init__(self, id, x, y):
        self.id = str(id)
        self.x = int(x)
        self.y = int(y)
        self.z = 0

    def __repr__(self):
        return f"G({self.id})"


class Wire:
    def __init__(self, x, y, z=0):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)

    def is_connected_to_gate(self, gate):
        return self._is_neighbor(gate, distance=0)

    def is_neighbor_of_wire(self, wire):
        return self._is_neighbor(wire)

    def _is_neighbor(self, other, distance=1):
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z) == distance

    def __repr__(self):
        return f"W({self.x, self.y, self.z})"


class Net:
    def __init__(self, gate_a, gate_b, wires):
        self.gate_a = gate_a
        self.gate_b = gate_b
        self.wires = wires

        self._check_connected()
        self._check_continuous()

    def _check_connected(self):
        if self.wires[0].is_connected_to_gate(self.gate_a) and self.wires[-1].is_connected_to_gate(self.gate_b):
            return

        if self.wires[0].is_connected_to_gate(self.gate_b) and self.wires[-1].is_connected_to_gate(self.gate_a):
            return

        raise UnconnectedNetError(f"{self} is not connected to gate {self.gate_a} and gate {self.gate_b}")

    def _check_continuous(self):
        cursor = self.wires[0]
        for wire in self.wires[1:]:
            if not cursor.is_neighbor_of_wire(wire):
                raise InteruptedNetError(f"{self} is interupted, wires {cursor} and {wire} do not connect to each other.")
            cursor = wire

    def __repr__(self):
        return f"N({self.gate_a.id},{self.gate_b.id})"


class Grid:
    NUMBER_OF_LAYERS = 8
    
    class Cell:
        def __init__(self):
            self.occupants = []
            self.is_gate = False

        def add_net(self, net):
            if self.is_gate:
                raise OccupiedByGateError(f"Net {net} crosses the following gate {self.occupants[0]}")
            self.occupants.append(net)

        def set_as_gate(self, gate):
            assert not self.is_gate
            self.occupants = [gate]
            self.is_gate = True

        def __repr__(self):
            return ",".join(repr(occ) for occ in self.occupants) if self.occupants else "."


    def __init__(self, print_filepath):
        self.gates = []
        with open(print_filepath) as f:
            for entry in csv.DictReader(f):
                x = int(entry["x"])
                y = int(entry["y"])
                self.gates.append(Gate(entry["chip"], x, y))

        self.nets = []

        self.width = max(gate.x for gate in self.gates) + 2
        self.height = max(gate.y for gate in self.gates) + 2

        create_layer = lambda: [[Grid.Cell() for _ in range(self.width)] for _ in range(self.height)]
        self._grid = [create_layer() for _ in range(Grid.NUMBER_OF_LAYERS)]

        for gate in self.gates:
            self.place_gate(gate)

    def place_gate(self, gate):
        gate_layer = self._grid[0]
        gate_layer[gate.y][gate.x].set_as_gate(gate)

    def place_net(self, net):
        self.nets.append(net)
        for wire in net.wires[1:-1]:
            self._grid[wire.z][wire.y][wire.x].add_net(net)

    def get_gate(self, gate_id):
        for gate in self.gates:
            if gate.id == gate_id:
                return gate

    def get_cost(self):
        cost = 0
        for z in range(Grid.NUMBER_OF_LAYERS):
            for y in range(self.height):
                for x in range(self.width):
                    cell = self._grid[z][y][x]

                    # If this is a gate, skip                    
                    if cell.is_gate:
                        continue

                    # Every piece of wire increases the cost by 1
                    cost += len(cell.occupants)

                    # If there's more than one piece of wire, apply the 300 penalty per additional wire
                    cost += max(0, len(cell.occupants) - 1) * 300
        
        # Wires run between intersections, but this representation uses intersections, so add 1 for each wire
        # (A wire with 1 intersection has length 2, 2 intersections has length 3, and so on)
        cost += len(self.nets)

        return cost

    def pretty_print(self):
        fmt = ""
        for i in range(Grid.NUMBER_OF_LAYERS):
            fmt += self._pretty_print_layer(i) + "\n"
        return fmt        

    def pretty_print_gates(self):
        return self._pretty_print_layer(0)

    def _pretty_print_layer(self, layer_number):
        layer = self._grid[layer_number]

        cell_width = 0
        for y in reversed(range(self.height)):
            for x in range(self.width):
                cell_width = max(cell_width, len(str(layer[y][x])))

        fmt = " ".join(["".rjust(cell_width)] + [str(i + 1).rjust(cell_width) for i in range(self.width)]) + "\n"
        for y in reversed(range(self.height)):
            fmt += str(y + 1).rjust(cell_width) + " "
            
            for x in range(self.width):
                fmt += str(layer[y][x]).rjust(cell_width) + " "
            fmt += "\n"

        return fmt