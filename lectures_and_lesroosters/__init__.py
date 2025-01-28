import check50

import pandas as pd

@check50.check()
def exists():
    """output.csv bestaat"""
    check50.exists("output.csv")
    check50.include("studenten_en_vakken.csv", "vakken.csv", "zalen.csv")


@check50.check(exists)
def correct_column_names():
    """output.csv heeft de kolommen student, vak, activiteit, zaal, dag en tijdslot"""
    schedule = pd.read_csv("output.csv")

    if set(schedule.keys()) != {"student", "vak", "activiteit", "zaal", "dag", "tijdslot"}:
        raise check50.Mismatch(
            {"student", "vak", "activiteit", "zaal", "dag", "tijdslot"},
            set(schedule.keys())
        )

@check50.check(correct_column_names)
def no_duplicates():
    """Geen duplicaten in combinaties student, vak, activiteit"""
    schedule = pd.read_csv("output.csv")
    combo = ["student", "vak", "activiteit"]

    duplicates = schedule.duplicated(subset=combo)
    if duplicates.any():
        raise check50.Failure(
            "Rooster is ongeldig omdat de volgende student, vak en activiteit combinaties meerdere keren voorkomen:\n" +
            str(schedule[duplicates].drop_duplicates(subset=combo))
        )

@check50.check(no_duplicates)
def only_valid_timeslots():
    """Enkel de tijdsloten 9, 11, 13, 15 en 17 zijn gebruikt"""
    schedule = pd.read_csv("output.csv")
    used_timeslots = set(schedule["tijdslot"].unique())

    if used_timeslots - {9, 11, 13, 15, 17} != set():
        raise check50.Failure(
            "Rooster is ongeldig omdat de volgende tijdsloten zijn gebruikt:\n" +
            str(used_timeslots - {9, 11, 13, 15, 17})
        )

@check50.check(only_valid_timeslots)
def only_biggest_in_evening():
    """Het late tijdslot wordt alleen door de grootste zaal (C0.110) gebruikt"""
    schedule = pd.read_csv("output.csv")

    if 17 in schedule["tijdslot"].unique():
        evening_slot = schedule.groupby("tijdslot")
        evening_group = evening_slot.get_group(17)
        evening_group_in_wrong_room = evening_group[evening_group["zaal"] != "C0.110"]

        if not evening_group_in_wrong_room.empty:
            raise check50.Failure(
                "Rooster is ongeldig omdat er gebruik wordt gemaakt van het laatste tijdslot voor een andere zaal:\n" +
                str(evening_group_in_wrong_room[["dag", "tijdslot", "zaal", "vak"]])
            )

@check50.check(no_duplicates)
def no_room_collisions():
    """Er zijn geen dubbelgeboekte zaalsloten"""
    schedule = pd.read_csv("output.csv")
    
    schedule = schedule.drop_duplicates(subset=["zaal", "dag", "tijdslot", "vak"], keep="first")

    duplicates = schedule[schedule.duplicated(subset=["zaal", "dag", "tijdslot"], keep=False)]

    if not duplicates.empty:
        raise check50.Failure(
            "Rooster is ongeldig omdat er in hetzelfde zaalslot twee vakken zijn geroosterd:\n" +
            str(duplicates[[ "dag", "tijdslot", "zaal", "vak"]])
        )


@check50.check(correct_column_names)
def all_courses_scheduled():
    """Alle vakken zijn ingeroosterd"""
    schedule = pd.read_csv("output.csv")
    unique_courses = set(pd.read_csv("vakken.csv")["Vak"].unique())
    unique_scheduled_courses = set(schedule["vak"].unique())

    if unique_scheduled_courses - unique_courses != set():
        raise check50.Failure(
            "Rooster is ongeldig omdat de volgende vakken in het rooster zitten, maar niet in vakken.csv:\n" +
            str(unique_scheduled_courses - unique_courses)
        )

    if unique_courses - unique_scheduled_courses != set():
        raise check50.Failure(
            "Rooster is ongeldig omdat de volgende vakken niet in het rooster zitten, maar wel in vakken.csv:\n" +
            str(unique_courses - unique_scheduled_courses)
        )


@check50.check(correct_column_names)
def all_lectures_scheduled():
    """Alle hoorcolleges zijn ingeroosterd"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        n_lectures = row["#Hoorcolleges"]

        scheduled_lectures = schedule[
            (schedule["vak"] == course_name) &
            (schedule["activiteit"].str.startswith("h"))
        ].drop_duplicates(subset=["vak", "activiteit"])

        if len(scheduled_lectures) != n_lectures:
            if len(scheduled_lectures) == 0:
                raise check50.Failure(
                    f"Rooster is ongeldig omdat er voor het vak '{course_name}' precies {n_lectures} hoorcollege(s) moeten worden geroosterd. Maar er zijn geen hoorcolleges ingeroosterd."
                )

            raise check50.Failure(
                f"Rooster is ongeldig omdat er voor het vak '{course_name}' precies {n_lectures} hoorcollege(s) moeten worden geroosterd. Maar de volgende hoorcolleges zijn ingeroosterd:\n" +
                str(list(scheduled_lectures["vak"]))
            )

@check50.check(correct_column_names)
def all_workshops_scheduled():
    """Alle werkcolleges zijn ingeroosterd"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        n_workshops = row["#Werkcolleges"]
        
        scheduled_workshops = schedule[
            (schedule["vak"] == course_name) &
            (schedule["activiteit"].str.startswith("w"))
        ].drop_duplicates(subset=["vak", "activiteit"])

        if len(scheduled_workshops) < n_workshops:
            if len(scheduled_workshops) == 0:
                raise check50.Failure(
                     f"Rooster is ongeldig omdat er voor het vak '{course_name}' precies {n_workshops} werkcollegs(s) moeten worden geroosterd. Maar er zijn geen werkcolleges ingeroosterd."
                )

            raise check50.Failure(
                f"Rooster is ongeldig omdat er voor het vak '{course_name}' precies {n_workshops} werkcollege(s) moeten worden geroosterd. Maar de volgende werkcolleges zijn ingeroosterd:\n" +
                str(list(scheduled_workshops["vak"]))
            )

@check50.check(correct_column_names)
def all_practicals_scheduled():
    """Alle practica zijn ingeroosterd"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        n_practicals = row["#Werkcolleges"]
        
        scheduled_practicals = schedule[
            (schedule["vak"] == course_name) &
            (schedule["activiteit"].str.startswith("p"))
        ].drop_duplicates(subset=["vak", "activiteit"])

        if len(scheduled_practicals) < n_practicals:
            if len(scheduled_practicals) == 0:
                raise check50.Failure(
                     f"Rooster is ongeldig omdat er voor het vak '{course_name}' precies {n_practicals} practica moeten worden geroosterd. Maar er zijn geen practica ingeroosterd."
                )

            raise check50.Failure(
                f"Rooster is ongeldig omdat er voor het vak '{course_name}' precies {n_practicals} practica moeten worden geroosterd. Maar de volgende practica zijn ingeroosterd:\n" +
                str(list(scheduled_practicals["vak"]))
            )




# TODO all students in each lecture
# TODO all students in enough workshops
# TODO all students in enough practicals


# @check50.check(no_room_collisions)
# def are_all_courses_scheduled():
#     """Check if all courses are scheduled."""
#     schedule = pd.read_csv("output.csv")

#     courses = pd.read_csv("vakken.csv")

#     scheduled_courses = schedule.groupby(["course", "activity"])
#     scheduled = set()
#     for course, group in scheduled_courses:
#         scheduled.add(course)

#     necessary = set()
#     for i, row in courses.iterrows():
#         h = row["#Hoorcolleges"]
#         w = row["#Werkcolleges"]
#         p = row["#Practica"]
#         for j in range(h):
#             type = "h" + str(j + 1)
#             necessary.add((row["Vak"], type))
#         for j in range(w):
#             type = "w" + str(j + 1)
#             necessary.add((row["Vak"], type))
#         for j in range(h):
#             type = "h" + str(j + 1)
#             necessary.add((row["Vak"], type))

#     if not necessary.issubset(scheduled):
#         raise check50.Failure("Schedule is infeasible since not all activities are scheduled per course")


# @check50.check(are_all_courses_scheduled)
# def are_all_students_assigned():
#     """All students are assigned to all their activities."""
#     pass

# @check50.check(are_all_students_assigned)
# def not_exceed_free_slots():
#     """Schedule does not exceed the number of maximum free slots."""
#     schedule = pd.read_csv("output.csv")
    
#     malus, infeasible_students = check_free_slots(schedule)
#     if infeasible_students > 0:
#         raise check50.Failure(f"Schedule is infeasible due to too many free slots for {infeasible_students} students. "
#         "Score will still be calculated, no points are assigned for the three free slots")

#     return malus

# @check50.check(not_exceed_free_slots)
# def score(free_slots_malus):
#     """Your score is: """
#     schedule = pd.read_csv("output.csv")
#     rooms = pd.read_csv("zalen.csv")

#     overlap_malus = get_overlap_malus(schedule) # TODO
#     room_malus = get_room_malus(schedule, rooms)
#     evening_malus = get_evening_malus(schedule)

#     score = free_slots_malus + overlap_malus + room_malus + evening_malus
#     check50.log(f"Malus points for free slots: {free_slots_malus}")
#     check50.log(f"Malus points for overlap: {overlap_malus}")
#     check50.log(f"Malus points for rooms: {room_malus}")
#     check50.log(f"Malus points for evening slot: {evening_malus}")
#     check50.log(f"Total score: {score}")
    

# def get_overlap_malus(df):
#     """
#     Returns the number of malus points based on the overlap between courses per
#     student:
#     - 2 courses at the same time: 1 malus point
#     - 3 courses at the same time: 2 malus points
#     """
#     duplicate = df[df.duplicated(["student", "day", "time"])]
#     malus_points = duplicate.shape[0]

#     return malus_points


# def get_room_malus(schedule, rooms):
#     """
#     Returns the number of malus points based on the use of the evening slot and
#     the number of students that do not fit in the room
#     """
#     courses = schedule.groupby(["course", "activity", "room", "time", "day"])
#     malus_students_room = 0

#     for course, group in courses:
#         students = group.shape[0]
#         room = group.iloc[0]["room"]

#         for i, row in rooms.iterrows():
#             if rooms.iloc[i]["Zaalnummber"] == room:
#                 capacity = rooms.iloc[i]["Max. capaciteit"]
#                 if capacity - students < 0:
#                      malus_students_room += abs(capacity - students)

#     return malus_students_room

# def get_evening_malus(schedule):
#     courses = schedule.groupby(["course", "activity", "room", "time", "day"])
#     malus_evening_slot = 0
#     for course, group in courses:

#         # check usage evening slot
#         if group.iloc[0]["time"] == 17:
#             malus_evening_slot += 5

#     return malus_evening_slot

# def check_free_slots(df):
#     """
#     Returns the number of malus points based on the number of free slots per
#     student:
#     - 1 free slot -> 1 malus point
#     - 2 free slots -> 3 malus points
#     - 3 free slots -> infeasible schedule
#     """

#     student_day = df.groupby(["student", "day"])
#     infeasible_students = 0
#     malus = 0
#     for student, group in student_day:
#         prevmalus = malus
#         courses = group.sort_values("time")
#         slots = courses.drop_duplicates("time")

#         if len(slots) > 1:
#             first = slots.iloc[0]["time"]
#             last = slots.iloc[-1]["time"]

#             if len(slots) == 2:
#                 if last - first == 4:
#                     malus += 1
#                 elif last - first == 6:
#                     malus += 3
#                 elif last - first > 6:
#                     infeasible_students += 1

#             elif len(slots) == 3:
#                 if last - first == 6:
#                     malus += 1
#                 elif last - first == 8:
#                     malus += 3

#             elif len(slots) == 4:
#                 if last - first == 10:
#                     malus += 1

#     return malus, infeasible_students
