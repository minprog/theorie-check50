import check50

import pandas as pd

@check50.check()
def exists():
    """Check if output.csv exists."""
    check50.exists("output.csv")
    check50.include("studenten_en_vakken.csv", "vakken.csv", "zalen.csv")

@check50.check(exists)
def no_duplicates():
    """No duplicates in (student, course, activity) combinations."""
    schedule = pd.read_csv("output.csv")

    duplicate = schedule[schedule.duplicated(["student", "course", "activity"])]
    if duplicate.shape[0] != 0:
        raise check50.Failure("Schedule is infeasible due to double scheduled activities")


@check50.check(no_duplicates)
def only_biggest_in_evening():
    """Only the biggest room is used in the evening slot."""
    schedule = pd.read_csv("output.csv")

    if 17 in schedule["time"].unique():
        evening_slot = schedule.groupby("time")
        evening_group = evening_slot.get_group(17)
        if not evening_group.all()["room"] or evening_group["room"].iloc[0] != "C0.110":
            raise check50.Failure("Schedule is infeasible due to wrong usage of the evening slot")


@check50.check(only_biggest_in_evening)
def are_all_courses_scheduled():
    """Check if all courses are scheduled."""
    schedule = pd.read_csv("output.csv")

    courses = pd.read_csv("vakken.csv")

    scheduled_courses = schedule.groupby(["course", "activity"])
    scheduled = set()
    for course, group in scheduled_courses:
        scheduled.add(course)

    necessary = set()
    for i, row in courses.iterrows():
        h = row["#Hoorcolleges"]
        w = row["#Werkcolleges"]
        p = row["#Practica"]
        for j in range(h):
            type = "h" + str(j + 1)
            necessary.add((row["Vak"], type))
        for j in range(w):
            type = "w" + str(j + 1)
            necessary.add((row["Vak"], type))
        for j in range(h):
            type = "h" + str(j + 1)
            necessary.add((row["Vak"], type))

    if not necessary.issubset(scheduled):
        raise check50.Failure("Schedule is infeasible since not all activities are scheduled per course")


@check50.check(are_all_courses_scheduled)
def are_all_students_assigned():
    """All students are assigned to all their activities."""
    pass

@check50.check(are_all_students_assigned)
def not_exceed_free_slots():
    """Schedule does not exceed the number of maximum free slots."""
    schedule = pd.read_csv("output.csv")
    
    malus, infeasible_students = check_free_slots(schedule)
    if infeasible_students > 0:
        raise check50.Failure(f"Schedule is infeasible due to too many free slots for {infeasible_students} students. "
        "Score will still be calculated, no points are assigned for the three free slots")

    return malus

@check50.check(not_exceed_free_slots)
def score(free_slots_malus):
    """Your score is: """
    schedule = pd.read_csv("output.csv")
    rooms = pd.read_csv("zalen.csv")

    overlap_malus = get_overlap_malus(schedule) # TODO
    room_malus = get_room_malus(schedule, rooms)
    evening_malus = get_evening_malus(schedule)

    score = free_slots_malus + overlap_malus + room_malus + evening_malus
    check50.log(f"Malus points for free slots: {free_slots_malus}")
    check50.log(f"Malus points for overlap: {overlap_malus}")
    check50.log(f"Malus points for rooms: {room_malus}")
    check50.log(f"Malus points for evening slot: {evening_malus}")
    check50.log(f"Total score: {score}")
    

def get_overlap_malus(df):
    """
    Returns the number of malus points based on the overlap between courses per
    student:
    - 2 courses at the same time: 1 malus point
    - 3 courses at the same time: 2 malus points
    """
    duplicate = df[df.duplicated(["student", "day", "time"])]
    malus_points = duplicate.shape[0]

    return malus_points


def get_room_malus(schedule, rooms):
    """
    Returns the number of malus points based on the use of the evening slot and
    the number of students that do not fit in the room
    """
    courses = schedule.groupby(["course", "activity", "room", "time", "day"])
    malus_students_room = 0

    for course, group in courses:
        students = group.shape[0]
        room = group.iloc[0]["room"]

        for i, row in rooms.iterrows():
            if rooms.iloc[i]["Zaalnummber"] == room:
                capacity = rooms.iloc[i]["Max. capaciteit"]
                if capacity - students < 0:
                     malus_students_room += abs(capacity - students)

    return malus_students_room

def get_evening_malus(schedule):
    courses = schedule.groupby(["course", "activity", "room", "time", "day"])
    malus_evening_slot = 0
    for course, group in courses:

        # check usage evening slot
        if group.iloc[0]["time"] == 17:
            malus_evening_slot += 5

    return malus_evening_slot

def check_free_slots(df):
    """
    Returns the number of malus points based on the number of free slots per
    student:
    - 1 free slot -> 1 malus point
    - 2 free slots -> 3 malus points
    - 3 free slots -> infeasible schedule
    """

    student_day = df.groupby(["student", "day"])
    infeasible_students = 0
    malus = 0
    for student, group in student_day:
        prevmalus = malus
        courses = group.sort_values("time")
        slots = courses.drop_duplicates("time")

        if len(slots) > 1:
            first = slots.iloc[0]["time"]
            last = slots.iloc[-1]["time"]

            if len(slots) == 2:
                if last - first == 4:
                    malus += 1
                elif last - first == 6:
                    malus += 3
                elif last - first > 6:
                    infeasible_students += 1

            elif len(slots) == 3:
                if last - first == 6:
                    malus += 1
                elif last - first == 8:
                    malus += 3

            elif len(slots) == 4:
                if last - first == 10:
                    malus += 1

    return malus, infeasible_students
