"""
AstroFit engine — the "brain".
Simulates how an astronaut's body changes in microgravity and adjusts their workout plan.

All numbers are a SIMPLIFIED MODEL for the competition, not medical data.
Bone loss is tuned to roughly 1.5-2% per month with no exercise.
"""
import copy

# ---------------------------------------------------------------- constants
SCORES = ["leg_bone", "spine_bone", "leg_muscle", "upper_muscle", "core_muscle", "heart"]
LABELS = {
    "leg_bone": "Leg bone",
    "spine_bone": "Spine bone",
    "leg_muscle": "Leg muscle",
    "upper_muscle": "Upper-body muscle",
    "core_muscle": "Core muscle",
    "heart": "Heart fitness",
}

# % lost per day in microgravity with NO exercise
DAILY_LOSS = {"leg_bone": 0.055, "spine_bone": 0.060, "leg_muscle": 0.11,
              "upper_muscle": 0.06, "core_muscle": 0.08, "heart": 0.07}

# % protected per 10 minutes of each exercise (anything not listed = 0)
_EX = {
    "squats":      {"leg_bone": 0.012, "spine_bone": 0.008, "leg_muscle": 0.030, "core_muscle": 0.008},
    "deadlifts":   {"leg_bone": 0.006, "spine_bone": 0.015, "leg_muscle": 0.020, "core_muscle": 0.015},
    "treadmill":   {"leg_bone": 0.010, "spine_bone": 0.003, "leg_muscle": 0.010, "heart": 0.025},
    "bike":        {"leg_muscle": 0.008, "heart": 0.030},
    "bench_press": {"upper_muscle": 0.030, "spine_bone": 0.003},
    "core_work":   {"core_muscle": 0.035, "spine_bone": 0.004},
}
EXERCISES = {ex: {s: v.get(s, 0.0) for s in SCORES} for ex, v in _EX.items()}

MAX_DAILY_MIN = 120          # astronauts get ~2 h of exercise a day
STEP = 10                    # plan changes happen in 10-minute blocks
MAX_MOVES_PER_UPDATE = 6     # at most 60 min changed per update -> gradual, avoids injury
MAX_MIN_PER_EXERCISE = 180   # anything above this in a log is rejected as an input error
DEFAULT_GOALS = {"leg_bone": 95.0, "spine_bone": 95.0, "leg_muscle": 92.0,
                 "upper_muscle": 92.0, "core_muscle": 92.0, "heart": 92.0}


# ---------------------------------------------------------------- core model
def daily_update(scores, workout, factor=1.0, sleep_ok=True, food_ok=True):
    """One day in space. Returns NEW scores (does not modify the input).

    factor: how fast THIS astronaut loses strength (1.0 = average). Every body is different.
    """
    new = {}
    for s in SCORES:
        loss = DAILY_LOSS[s] * factor
        protect = sum(EXERCISES[ex][s] * mins / 10
                      for ex, mins in workout.items() if ex in EXERCISES)
        if not sleep_ok:
            protect *= 0.8                    # poor sleep = weaker workout
        if not food_ok and "bone" in s:
            protect *= 0.7                    # low protein / vitamin D = less bone benefit
        new[s] = max(0.0, min(100.0, scores[s] - loss + protect))
    return new


def predict(scores, plan, days_left, factor=1.0):
    """Run the plan every day until landing. Returns a list of scores, one per day (day 0 = today)."""
    timeline = [dict(scores)]
    current = dict(scores)
    for _ in range(max(0, days_left)):
        current = daily_update(current, plan, factor)
        timeline.append(current)
    return timeline


# ---------------------------------------------------------------- planner
def _value(exercise, deficits):
    """How much an exercise helps the scores that are falling short (weighted by how short)."""
    return sum(EXERCISES[exercise][s] * gap for s, gap in deficits.items())


def adjust_plan(scores, plan, days_left, goals=None, factor=1.0,
                max_moves=MAX_MOVES_PER_UPDATE):
    """Change the workout plan so every score reaches its landing-day goal.

    Returns (new_plan, list_of_change_messages).
    """
    goals = goals or DEFAULT_GOALS
    plan = copy.deepcopy(plan)
    changes = []

    available = list(EXERCISES)
    for e in available:
        plan.setdefault(e, 0)

    # move 10-minute blocks toward the weakest scores
    moves = 0
    while moves < max_moves:
        final = predict(scores, plan, days_left, factor)[-1]
        deficits = {s: goals[s] - final[s] for s in SCORES if final[s] < goals[s]}
        if not deficits:
            break
        best = max(available, key=lambda e: _value(e, deficits))
        total = sum(plan.values())
        if total + STEP <= MAX_DAILY_MIN:
            plan[best] += STEP
            changes.append(f"+{STEP} min {best}")
        else:
            donors = [e for e in plan if plan[e] >= STEP and e != best]
            if not donors:
                break
            donor = min(donors, key=lambda e: _value(e, deficits))
            if _value(donor, deficits) >= _value(best, deficits):
                break                          # nothing better to swap
            plan[donor] -= STEP
            plan[best] += STEP
            changes.append(f"-{STEP} min {donor}, +{STEP} min {best}")
        moves += 1

    plan = {e: m for e, m in plan.items() if m > 0}
    return plan, _summarise(changes)


def _summarise(changes):
    """Merge repeated '+10 min squats' lines into '+30 min squats'."""
    totals = {}
    other = []
    for c in changes:
        for part in c.split(", "):
            bits = part.split(" min ")
            if len(bits) == 2 and bits[0][0] in "+-" and bits[0][1:].isdigit():
                totals[bits[1]] = totals.get(bits[1], 0) + int(bits[0])
            else:
                other.append(part)
    out = other + [f"{'+' if v > 0 else ''}{v} min {ex}" for ex, v in totals.items() if v != 0]
    return out


# ---------------------------------------------------------------- learning
def calibrate(history, current_factor=1.0):
    """Weekly test: compare what really happened with the model, and learn this
    astronaut's personal loss rate ('factor').

    history: list of dicts {scores_before, workout, sleep_ok, food_ok, scores_after}
    Tries factors 0.5-2.0 and keeps the one whose replay best matches reality.
    """
    if len(history) < 3:
        return current_factor, "Not enough data yet (need 3+ days). Keeping current estimate."
    start = history[0]["scores_before"]
    actual = history[-1]["scores_after"]
    best_f, best_err = current_factor, float("inf")
    for i in range(50, 201, 5):
        f = i / 100
        sim = dict(start)
        for day in history:
            sim = daily_update(sim, day["workout"], f, day["sleep_ok"], day["food_ok"])
        err = sum((sim[s] - actual[s]) ** 2 for s in SCORES)
        if err < best_err:
            best_f, best_err = f, err
    msg = f"Personal loss rate updated: {current_factor:.2f} -> {best_f:.2f}"
    return best_f, msg


# ---------------------------------------------------------------- input checks
def validate_workout(workout):
    """Return a list of problems with a logged workout (empty list = OK)."""
    errors = []
    for ex, mins in workout.items():
        if ex not in EXERCISES:
            errors.append(f"Unknown exercise '{ex}'")
        elif not isinstance(mins, (int, float)) or mins < 0:
            errors.append(f"{ex}: minutes must be a positive number")
        elif mins > MAX_MIN_PER_EXERCISE:
            errors.append(f"{ex}: {mins} min looks wrong (max {MAX_MIN_PER_EXERCISE}). Sensor or typing error?")
    return errors


def status(score, goal):
    """green / yellow / red for the dashboard."""
    if score >= goal:
        return "green"
    if score >= goal - 5:
        return "yellow"
    return "red"


# ---------------------------------------------------------------- quick test
if __name__ == "__main__":
    start = {s: 100.0 for s in SCORES}
    lazy_plan = {"bike": 40, "treadmill": 20}
    days = 180

    print("No exercise, 180 days:", {LABELS[s]: round(v, 1) for s, v in predict(start, {}, days)[-1].items()})
    print("Lazy plan, 180 days:  ", {LABELS[s]: round(v, 1) for s, v in predict(start, lazy_plan, days)[-1].items()})

    new_plan, changes = adjust_plan(start, lazy_plan, days, max_moves=20)
    print("\nPlanner changes:", changes)
    print("New plan:", new_plan)
    print("New plan, 180 days:   ", {LABELS[s]: round(v, 1) for s, v in predict(start, new_plan, days)[-1].items()})

    print("Validation:", validate_workout({"treadmill": 900, "yoga": 10}))

    # calibration test: real astronaut loses 1.4x faster than average
    hist, sc = [], dict(start)
    for _ in range(7):
        after = daily_update(sc, new_plan, factor=1.4)
        hist.append(dict(scores_before=sc, workout=new_plan, sleep_ok=True, food_ok=True,
                         scores_after=after))
        sc = after
    print(calibrate(hist, 1.0))
