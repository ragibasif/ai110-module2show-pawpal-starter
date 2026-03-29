"""
PawPal+ CLI Demo
================
Verify all backend logic end-to-end before connecting the Streamlit UI.
Run: python main.py
"""

from datetime import date, time

from pawpal_system import Category, Owner, Pet, Priority, Scheduler, Task


def section(title: str) -> None:
    print(f"\n{'─'*54}")
    print(f"  {title}")
    print(f"{'─'*54}")


def main() -> None:
    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    jordan = Owner(name="Jordan", available_start=time(7, 0), available_end=time(21, 0))

    mochi = Pet(name="Mochi", species="dog", age=3, owner=jordan)
    luna  = Pet(name="Luna",  species="cat", age=5, owner=jordan)
    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    # Add tasks out-of-priority order to prove sorting works
    mochi.add_task(Task(
        title="Grooming brush",
        duration_minutes=15,
        priority=Priority.LOW,
        category=Category.GROOMING,
    ))
    mochi.add_task(Task(
        title="Breakfast feeding",
        duration_minutes=10,
        priority=Priority.HIGH,
        category=Category.FEEDING,
        recurrence="daily",
    ))
    mochi.add_task(Task(
        title="Heartworm medication",
        duration_minutes=5,
        priority=Priority.HIGH,
        category=Category.MEDICATION,
        earliest_start=time(8, 0),
        latest_start=time(10, 0),
        recurrence="daily",
        notes="Give with food",
    ))
    mochi.add_task(Task(
        title="Morning walk",
        duration_minutes=30,
        priority=Priority.HIGH,
        category=Category.WALK,
        recurrence="daily",
    ))
    mochi.add_task(Task(
        title="Afternoon play",
        duration_minutes=20,
        priority=Priority.MEDIUM,
        category=Category.ENRICHMENT,
        earliest_start=time(14, 0),
    ))

    luna.add_task(Task(
        title="Thyroid medication",
        duration_minutes=5,
        priority=Priority.HIGH,
        category=Category.MEDICATION,
        earliest_start=time(8, 0),
        latest_start=time(9, 0),
        recurrence="daily",
    ))
    luna.add_task(Task(
        title="Breakfast feeding",
        duration_minutes=5,
        priority=Priority.HIGH,
        category=Category.FEEDING,
        recurrence="daily",
    ))
    luna.add_task(Task(
        title="Interactive toy session",
        duration_minutes=15,
        priority=Priority.MEDIUM,
        category=Category.ENRICHMENT,
    ))

    # ------------------------------------------------------------------
    # 1. Owner + Pet overview
    # ------------------------------------------------------------------
    section("Owner & Pet Overview")
    print(jordan)
    for pet in jordan.pets:
        print(f"  {pet}")

    # ------------------------------------------------------------------
    # 2. Sorting demo — tasks added out of order, printed sorted
    # ------------------------------------------------------------------
    section("Sorting Demo (high→medium→low; medication first within tier)")
    scheduler = Scheduler()
    sorted_tasks = scheduler._sort_tasks(mochi.tasks)
    for task in sorted_tasks:
        print(f"  [{task.priority.value:6}] [{task.category.value:11}] {task.title}")

    # ------------------------------------------------------------------
    # 3. Filtering demo
    # ------------------------------------------------------------------
    section("Filtering Demo")
    high_tasks = mochi.filter_tasks(priority=Priority.HIGH)
    print(f"Mochi's HIGH priority tasks ({len(high_tasks)}):")
    for t in high_tasks:
        print(f"  {t.title}")

    med_tasks = mochi.filter_tasks(category=Category.MEDICATION)
    print(f"\nMochi's MEDICATION tasks ({len(med_tasks)}):")
    for t in med_tasks:
        print(f"  {t.title}")

    # ------------------------------------------------------------------
    # 4. Generate schedules
    # ------------------------------------------------------------------
    section("Daily Schedule — All Pets")
    today = date.today()
    for pet in jordan.pets:
        schedule = scheduler.generate_schedule(pet, plan_date=today)
        schedule.pretty_print()

    # ------------------------------------------------------------------
    # 5. Conflict detection demo
    # ------------------------------------------------------------------
    # The greedy scheduler is conflict-free by construction (it advances
    # current_slot after every placed task). conflicts() is a safety net
    # for schedules assembled outside the Scheduler (e.g. manual edits).
    # We demonstrate it by building an overlapping schedule directly.
    section("Conflict Detection Demo")
    from datetime import datetime
    from pawpal_system import DailySchedule, ScheduledTask

    demo_pet = Pet(name="Demo", species="dog", age=1, owner=jordan)
    t_a = Task(title="Task A", duration_minutes=60, priority=Priority.HIGH)
    t_b = Task(title="Task B", duration_minutes=60, priority=Priority.HIGH)
    slot = datetime.combine(today, time(9, 0))
    manual_schedule = DailySchedule(plan_date=today, pet=demo_pet)
    manual_schedule.scheduled.append(ScheduledTask(task=t_a, start_time=slot))
    manual_schedule.scheduled.append(ScheduledTask(task=t_b, start_time=slot))  # same slot!
    conflicts = manual_schedule.conflicts()
    if conflicts:
        print(f"⚠ {len(conflicts)} conflict(s) detected:")
        for a, b in conflicts:
            print(f"  '{a.task.title}' 09:00–10:00 overlaps '{b.task.title}' 09:00–10:00")
    else:
        print("No conflicts detected.")

    # ------------------------------------------------------------------
    # 6. Recurring task demo
    # ------------------------------------------------------------------
    section("Recurring Task Demo")
    print(f"Mochi tasks before completing 'Morning walk': {len(mochi.tasks)}")
    walk = next(t for t in mochi.tasks if t.title == "Morning walk")
    next_task = mochi.complete_task(walk, today=today)
    print(f"Mochi tasks after completing 'Morning walk':  {len(mochi.tasks)}")
    if next_task:
        print(f"Next occurrence queued: '{next_task.title}' due {next_task.due_date}")

    # ------------------------------------------------------------------
    # 7. Cross-pet pending task overview
    # ------------------------------------------------------------------
    section("All Pending Tasks Across All Pets")
    for pet, task in jordan.all_pending_tasks():
        print(f"  [{pet.name:6}] {task.title} ({task.priority.value})")


if __name__ == "__main__":
    main()
