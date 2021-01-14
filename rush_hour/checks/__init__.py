#!/usr/bin/env python3
"""
This file uses check50 to check the output of a Rush Hour solution. It does so
by doing the following tests in this order:
    - Check if output.csv exits
    - Check if the file has valid values and is structured correctly
    - Check if all moves are valid and can be performed in order.
    - Check if the red car is moved towards the edge of the board.

NOTE: This check50 does not compute the score of the solution since it is just
      counting the number of lines in the output.csv.

@author: Okke van Eck
@contact: okke.van.eck@gmail.com
"""

import check50
import pandas as pd
import numpy as np
import csv
import os

# Global for tracking the boards borders. This global must be set by each check.
BOARD_SIZE = 0

# Global for tracking the file the board lives in. This global can be changed in the
# sub-folders according to their board size.
BOARD_FILE = "board.csv"


@check50.check()
def exists():
    """output.csv exists."""
    check50.exists("output.csv")
    check50.include(BOARD_FILE)


@check50.check(exists)
def check_file():
    """The structure and values of output.csv are correct."""
    # Check if output.csv has content.
    if os.stat("output.csv").st_size == 0:
        raise check50.Failure("Output.csv may not be empty. Provide at least a header row.")

    with open("output.csv") as csvfile:
        df = pd.read_csv(csvfile)

        # Check header for correct format.
        if list(df) != ["car", "move"]:
            raise check50.Failure("Expected header of the csv to be 'car,move'")

        # Stop checking if there are no moves in the output file.
        if len(df) == 1:
            return

        # Check if all values in the car column are alphabetical
        car_name_bools = np.array([x.isalpha() for x in df["car"]])
        if False in car_name_bools:
            idxs = np.where(car_name_bools == False)[0]
            error = "Invalid characters(s) used for a car. Expected only " \
                    "letters, but found:\n"

            for idx in idxs:
                error = "".join([error, f"\t'{df['car'][idx]}' \ton row "
                                        f"{idx+2}\n"])

            raise check50.Failure(error)

        # Check if all car letters are valid.
        with open(BOARD_FILE) as boardfile:
            board_df = pd.read_csv(boardfile)
            car_exists_bools = df.car.isin(board_df.car).values

            if False in car_exists_bools:
                idxs = np.where(car_exists_bools == False)[0]
                error = "Invalid letter(s) used for a car. The following " \
                        "letters are not on the board:\n"

                for idx in idxs:
                    error = "".join([error, f"\t'{df['car'][idx]}' \ton row "
                                            f"{idx + 2}\n"])

                raise check50.Failure(error)

        # Check if all values in the move column are integers
        if df["move"].dtype != "int":
            if df["move"].dtype == "float":
                error = "Invalid value(s) used for a move. Expected " \
                        "only integers but floats were used."
            else:
                error = "Invalid value(s) used for a move. Expected, " \
                        "integers but found:\n"

                for i, item in enumerate(df['move']):
                    try:
                        int(item)
                    except ValueError:
                        error = "".join([error, f"\t'{df['move'][i]}' \ton "
                                                f"row {i}\n"])

            raise check50.Failure(error)


@check50.check(check_file)
def check_moves():
    """The moves are valid and the red car exits."""
    
    # Load the current board
    with open(BOARD_FILE) as board_file:
        board = Board.load(board_file)
        vehicles = board.vehicles

    # Perform each move in output.csv
    with open("output.csv") as output_file:
        for entry in csv.DictReader(output_file):
            
            # Find which vehicle needs to be moved
            vehicle = [vehicle for vehicle in vehicles if vehicle.name == entry["car"]][0]

            # Perform the move
            try:
                board = board.move(vehicle, int(entry["move"]))
            except Collision as collision:
                raise check50.Failure(f"Two vehicles collided while trying to move {entry['car']} with {entry['move']}.\n"
                                      f"This is the state in which the collision happened:\n{board.pretty_print()}")
            except WallHit as wall_hit:
                raise check50.Failure(f"Vehicle {entry['car']} hit the wall while trying to move it with {entry['move']}.\n"
                                      f"This is the state in which the collision happened:\n{board.pretty_print()}")

    # Check that board is solved in the end
    if not board.is_solved():
        raise check50.Failure(f"The board is not solved after resolving all moves, this is the final state:\n{board.pretty_print()}")


class Collision(Exception):
    pass


class WallHit(Exception):
    pass


class Board:
    EMPTY_TILE = "_"

    def __init__(self, size):
        self.size = size
        self.vehicles = []
        self._board = [[Board.EMPTY_TILE] * self.size for _ in range(self.size)]

    @staticmethod
    def load(file):
        board = Board(BOARD_SIZE)

        for entry in csv.DictReader(file):
            # Create a vehicle from all the static data
            vehicle = Vehicle(entry["car"], entry["orientation"], int(entry["length"]))

            # Go back to zero indexed col, row
            col = int(entry["col"]) - 1
            row = int(entry["row"]) - 1

            # Place the vehicle on the board at col,row
            board.place(vehicle, col, row)
            
            # Assert that it's retrievable after the fact
            assert board.location_of(vehicle) == (col, row)

        return board

    def place(self, vehicle, col, row):
        # Get all the locations that the vehicle is going to occupy
        if vehicle.orientation == "V":
            locations = [(col, row + i) for i in range(vehicle.length)]
        else:
            locations = [(col + i, row) for i in range(vehicle.length)]

        # Place the vehicle at all its locations
        for col, row in locations:
            if col not in range(self.size) or row not in range(self.size):
                raise WallHit(f"Vehicle {vehicle} hit the wall at {col + 1}, {row + 1}")

            if self._board[col][row] != Board.EMPTY_TILE:
                raise Collision(f"Collision at {col + 1},{row + 1} with {vehicle} and {self._board[col][row]}")
            
            self._board[col][row] = vehicle

        # Keep track of all vehicles on the board
        self.vehicles.append(vehicle)

    def move(self, vehicle, steps):
        # Simplify a longer move into a series of moves of 1 or -1
        moves = [1] * steps if steps >= 0 else [-1] * abs(steps)        

        # Repeatedly perform a move by placing all the vehicles on a new board
        cursor_board = self
        for move in moves:
            # Create a new board
            new_board = Board(cursor_board.size)
            
            # Place all other vehicles than the one to be moved on the board
            other_vehicles = [v for v in self.vehicles if v != vehicle]

            for other_vehicle in other_vehicles:
                new_board.place(other_vehicle, *cursor_board.location_of(other_vehicle))

            # Move the vehicle
            col, row = cursor_board.location_of(vehicle)
            if vehicle.orientation == "V":
                row += move
            else:
                col += move
            
            # Add the vehicle to the board
            new_board.place(vehicle, col, row)

            # Move the cursor to the newly created board           
            cursor_board = new_board

        return cursor_board

    def location_of(self, vehicle):
        for row in range(self.size):
            for col in range(self.size):
                if self._board[col][row] == vehicle:
                    return col, row

    def is_solved(self):
        goal_col = self.size - 1
        goal_row = (self.size - 1) // 2
        vehicle_at_goal = self._board[goal_col][goal_row] 
        return vehicle_at_goal != Board.EMPTY_TILE and vehicle_at_goal.is_red_car()


    def pretty_print(self):
        max_name_length = max(len(vehicle.name) for vehicle in self.vehicles)

        fmt = ""
        for row in range(self.size):
            for col in range(self.size):
                fmt += str(self._board[col][row]).rjust(max_name_length) + " "
            fmt += "\n"
        return fmt


class Vehicle:
    def __init__(self, name, orientation, length):
        self.name = name
        self.orientation = orientation
        self.length = length

    def is_red_car(self):
        return self.name == "X"

    def __eq__(self, other):
        return isinstance(other, Vehicle) and self.name == other.name

    def __repr__(self):
        return self.name