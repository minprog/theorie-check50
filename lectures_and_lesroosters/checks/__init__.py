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


@check50.check(only_biggest_in_evening)
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


@check50.check(no_room_collisions)
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


@check50.check(all_courses_scheduled)
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


@check50.check(all_lectures_scheduled)
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


@check50.check(all_workshops_scheduled)
def all_practicals_scheduled():
    """Alle practica zijn ingeroosterd"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        n_practicals = row["#Practica"]

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




def _enrolled_students(vak, students):
    """Return the set of (first name) students enrolled in vak."""
    vak_columns = ["Vak1", "Vak2", "Vak3", "Vak4", "Vak5"]
    enrolled = students[(students[vak_columns] == vak).any(axis=1)]
    return set(enrolled["Voornaam"])


@check50.check(all_practicals_scheduled)
def all_students_in_each_lecture():
    """Alle ingeschreven studenten zijn aanwezig bij elk hoorcollege"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")
    students = pd.read_csv("studenten_en_vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        enrolled = _enrolled_students(course_name, students)

        lectures = schedule[
            (schedule["vak"] == course_name) &
            (schedule["activiteit"].str.startswith("h"))
        ]

        for activiteit, group in lectures.groupby("activiteit"):
            attending = set(group["student"])
            missing = enrolled - attending

            if missing:
                raise check50.Failure(
                    f"Rooster is ongeldig omdat niet alle ingeschreven studenten van '{course_name}' "
                    f"aanwezig zijn bij hoorcollege '{activiteit}'. Ontbrekende studenten:\n" +
                    str(missing)
                )


@check50.check(all_students_in_each_lecture)
def all_students_in_enough_workshops():
    """Alle ingeschreven studenten zijn ingedeeld in elk werkcollege"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")
    students = pd.read_csv("studenten_en_vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        n_workshops = row["#Werkcolleges"]

        enrolled = _enrolled_students(course_name, students)

        for n in range(1, n_workshops + 1):
            activiteit = f"w{n}"
            attending = set(schedule[
                (schedule["vak"] == course_name) &
                (schedule["activiteit"] == activiteit)
            ]["student"])
            missing = enrolled - attending

            if missing:
                raise check50.Failure(
                    f"Rooster is ongeldig omdat niet alle ingeschreven studenten van '{course_name}' "
                    f"zijn ingedeeld in werkcollege '{activiteit}'. Ontbrekende studenten:\n" +
                    str(missing)
                )


@check50.check(all_students_in_enough_workshops)
def all_students_in_enough_practicals():
    """Alle ingeschreven studenten zijn ingedeeld in elk practicum"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")
    students = pd.read_csv("studenten_en_vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        n_practicals = row["#Practica"]

        enrolled = _enrolled_students(course_name, students)

        for n in range(1, n_practicals + 1):
            activiteit = f"p{n}"
            attending = set(schedule[
                (schedule["vak"] == course_name) &
                (schedule["activiteit"] == activiteit)
            ]["student"])
            missing = enrolled - attending

            if missing:
                raise check50.Failure(
                    f"Rooster is ongeldig omdat niet alle ingeschreven studenten van '{course_name}' "
                    f"zijn ingedeeld in practicum '{activiteit}'. Ontbrekende studenten:\n" +
                    str(missing)
                )


@check50.check(all_students_in_enough_practicals)
def workshops_not_over_capacity():
    """Geen enkel werkcollege zit boven de maximale capaciteit"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        if row["#Werkcolleges"] == 0:
            continue

        max_capacity = row["Max. stud. Werkcollege"]

        workshops = schedule[
            (schedule["vak"] == course_name) &
            (schedule["activiteit"].str.startswith("w"))
        ]

        for (activiteit, zaal, dag, tijdslot), group in workshops.groupby(["activiteit", "zaal", "dag", "tijdslot"]):
            n_students = len(group)
            if n_students > max_capacity:
                raise check50.Failure(
                    f"Rooster is ongeldig omdat werkcollege '{activiteit}' van '{course_name}' "
                    f"({zaal}, {dag} {tijdslot}) {n_students} studenten heeft, terwijl maximaal "
                    f"{max_capacity} zijn toegestaan."
                )


@check50.check(workshops_not_over_capacity)
def practicals_not_over_capacity():
    """Geen enkel practicum zit boven de maximale capaciteit"""
    schedule = pd.read_csv("output.csv")
    courses = pd.read_csv("vakken.csv")

    for _, row in courses.iterrows():
        course_name = row["Vak"]
        if row["#Practica"] == 0:
            continue

        max_capacity = row["Max. stud. Practicum"]

        practicals = schedule[
            (schedule["vak"] == course_name) &
            (schedule["activiteit"].str.startswith("p"))
        ]

        for (activiteit, zaal, dag, tijdslot), group in practicals.groupby(["activiteit", "zaal", "dag", "tijdslot"]):
            n_students = len(group)
            if n_students > max_capacity:
                raise check50.Failure(
                    f"Rooster is ongeldig omdat practicum '{activiteit}' van '{course_name}' "
                    f"({zaal}, {dag} {tijdslot}) {n_students} studenten heeft, terwijl maximaal "
                    f"{max_capacity} zijn toegestaan."
                )


def _get_overlap_malus(schedule):
    """
    Ieder vakconflict (meer dan één activiteit op hetzelfde moment) in het
    rooster van één student levert één maluspunt op.
    """
    conflicts = schedule[schedule.duplicated(["student", "dag", "tijdslot"])]
    return conflicts.shape[0]


def _get_room_malus(schedule, rooms):
    """Één maluspunt per student die niet meer in de zaal past."""
    sessions = schedule.groupby(["vak", "activiteit", "zaal", "dag", "tijdslot"])
    malus = 0

    for (_, _, zaal, _, _), group in sessions:
        n_students = group.shape[0]
        capacity = rooms.loc[rooms["Zaalnummber"] == zaal, "Max. capaciteit"].iloc[0]

        if n_students > capacity:
            malus += n_students - capacity

    return malus


def _get_evening_malus(schedule):
    """Gebruik van het avondslot (tijdslot 17) kost vijf maluspunten per zaalslot."""
    sessions = schedule.groupby(["vak", "activiteit", "zaal", "dag", "tijdslot"])
    return sum(5 for (_, _, _, _, tijdslot), _ in sessions if tijdslot == 17)


def _get_free_slots_malus(schedule):
    """
    Een tussenslot voor een student op een dag levert één maluspunt op. Twee
    tussensloten op één dag voor een student levert drie maluspunten op.
    """
    valid_timeslots = sorted(schedule["tijdslot"].unique())
    slot_index = {slot: i for i, slot in enumerate(valid_timeslots)}
    malus_per_n_gaps = {0: 0, 1: 1, 2: 3}

    malus = 0
    for _, group in schedule.groupby(["student", "dag"]):
        occupied = sorted(slot_index[t] for t in group["tijdslot"].unique())

        if len(occupied) > 1:
            n_gaps = (occupied[-1] - occupied[0] + 1) - len(occupied)
            malus += malus_per_n_gaps.get(n_gaps, 0)

    return malus


@check50.check(practicals_not_over_capacity)
def score():
    """Score"""
    schedule = pd.read_csv("output.csv")
    rooms = pd.read_csv("zalen.csv")

    overlap_malus = _get_overlap_malus(schedule)
    room_malus = _get_room_malus(schedule, rooms)
    evening_malus = _get_evening_malus(schedule)
    free_slots_malus = _get_free_slots_malus(schedule)

    total_score = overlap_malus + room_malus + evening_malus + free_slots_malus

    check50.log(f"Maluspunten voor vakconflicten: {overlap_malus}")
    check50.log(f"Maluspunten voor te volle zalen: {room_malus}")
    check50.log(f"Maluspunten voor het avondslot: {evening_malus}")
    check50.log(f"Maluspunten voor tussensloten: {free_slots_malus}")
    check50.log(f"Totaal aantal maluspunten: {total_score}")
