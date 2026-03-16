def check_violation(objects):

    bike_count = 0
    person_count = 0

    for obj in objects:

        label = obj[0]

        if label == "motorcycle":
            bike_count += 1

        if label == "person":
            person_count += 1

    if bike_count > 0 and person_count > 2:
        return "Triple Riding Violation"

    return "No Violation"