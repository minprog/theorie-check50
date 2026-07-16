#!/usr/bin/env python3
"""
Generates a valid example_output.csv for a lectures_and_lesroosters instance
(science_park or lab42) by greedily assigning every lecture, workshop and
practicum to a fresh room/day/timeslot combination, so no room is ever
double-booked and every group respects its capacity.

Usage: python3 generate_example_output.py <instance_dir>
"""

import itertools
import sys

import pandas as pd

TIMESLOTS = [9, 11, 13, 15]


def slot_generator(rooms):
    for day in itertools.count(1):
        for timeslot in TIMESLOTS:
            for room in rooms:
                yield room, f"Dag{day}", timeslot


def chunks(seq, size):
    size = int(size)
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def enrolled_names(students, vak):
    vak_columns = ["Vak1", "Vak2", "Vak3", "Vak4", "Vak5"]
    enrolled = students[(students[vak_columns] == vak).any(axis=1)]
    return sorted(set(enrolled["Voornaam"]))


def main():
    instance_dir = sys.argv[1]

    vakken = pd.read_csv(f"{instance_dir}/vakken.csv")
    zalen = pd.read_csv(f"{instance_dir}/zalen.csv")
    students = pd.read_csv(f"{instance_dir}/studenten_en_vakken.csv")

    rooms = list(zalen.iloc[:, 0])
    slots = slot_generator(rooms)

    rows = []
    for _, course in vakken.iterrows():
        vak = course["Vak"]
        names = enrolled_names(students, vak)

        for h in range(1, int(course["#Hoorcolleges"]) + 1):
            room, day, timeslot = next(slots)
            for name in names:
                rows.append((name, vak, f"h{h}", room, day, timeslot))

        for w in range(1, int(course["#Werkcolleges"]) + 1):
            for group in chunks(names, course["Max. stud. Werkcollege"]):
                room, day, timeslot = next(slots)
                for name in group:
                    rows.append((name, vak, f"w{w}", room, day, timeslot))

        for p in range(1, int(course["#Practica"]) + 1):
            for group in chunks(names, course["Max. stud. Practicum"]):
                room, day, timeslot = next(slots)
                for name in group:
                    rows.append((name, vak, f"p{p}", room, day, timeslot))

    schedule = pd.DataFrame(
        rows, columns=["student", "vak", "activiteit", "zaal", "dag", "tijdslot"]
    )
    schedule.to_csv(f"{instance_dir}/example_output.csv", index=False)


if __name__ == "__main__":
    main()
