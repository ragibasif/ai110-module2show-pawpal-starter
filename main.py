"""
PawPal+ CLI Demo
================
Verify all backend logic end-to-end before connecting the Streamlit UI.
Run: python main.py
"""

from datetime import date, datetime, time, timedelta

from tabulate import tabulate

from pawpal_system import (
    Category, DailySchedule, Owner, Pet, Priority, Scheduler,
    ScheduledTask, Task,
)

# Emoji maps for terminal output
PRIORITY_EMOJI = {Priority.HIGH: "🔴", Priority.MEDIUM: "🟡", Priority.LOW: "🟢"}
CATEGORY_EMOJI = {
    Category.WALK: "🦮", Category.FEEDING: "🍽️", Category.MEDICATION: "💊",
    Category.GROOMING: "✂️", Category.ENRICHMENT: "🎾",
    Category.APPOINTMENT: "🏥", Category.OTHER: "📋",
}


def section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def main() -> None:
    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    jordan = Owner(name="Jordan", available_start=time(7, 0), available_end=time(21, 0))
    mochi = Pet(name="Mochi", species="dog", age=3, owner=jordan)
    luna  = Pet(name="Luna",  species="cat", age=5, owner=jordan)
    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    mochi.add_task(Task("Grooming brush",       15, Priority.LOW,    Category.GROOMING))
    mochi.add_task(Task("Breakfast feeding",    10, Priority.HIGH,   Category.FEEDING,   recurrence="daily"))
    mochi.add_task(Task("Heartworm medication",  5, Priority.HIGH,   Category.MEDICATION,
                        earliest_start=time(8, 0), latest_start=time(10, 0),
                        recurrence="daily", notes="Give with food"))
    mochi.add_task(Task("Morning walk",         30, Priority.HIGH,   Category.WALK,       recurrence="daily"))
    mochi.add_task(Task("Afternoon play",       20, Priority.MEDIUM, Category.ENRICHMENT, earliest_start=time(14, 0)))

    luna.add_task(Task("Thyroid medication",     5, Priority.HIGH,   Category.MEDICATION,
                       earliest_start=time(8, 0), latest_start=time(9, 0), recurrence="daily"))
    luna.add_task(Task("Breakfast feeding",      5, Priority.HIGH,   Category.FEEDING,    recurrence="daily"))
    luna.add_task(Task("Interactive toy session",15, Priority.MEDIUM, Category.ENRICHMENT))

    scheduler = Scheduler()
    today = date.today()

    # ------------------------------------------------------------------
    # 1. Overview
    # ------------------------------------------------------------------
    section("Owner & Pets")
    print(jordan)
    for pet in jordan.pets:
        print(f"  {pet}")

    # ------------------------------------------------------------------
    # 2. Weighted sorting demo
    # ------------------------------------------------------------------
    section("Weighted Sort Order (score = priority + category urgency + window tightness)")
    rows = [
        [
            f"{PRIORITY_EMOJI[t.priority]} {t.priority.value}",
            f"{CATEGORY_EMOJI[t.category]} {t.category.value}",
            t.title,
            t.duration_minutes,
            f"{scheduler._weighted_score(t):.4f}",
        ]
        for t in scheduler._sort_tasks(mochi.tasks)
    ]
    print(tabulate(rows, headers=["Priority", "Category", "Task", "Min", "Score"],
                   tablefmt="rounded_outline"))

    # ------------------------------------------------------------------
    # 3. Filtering demo
    # ------------------------------------------------------------------
    section("Filtering: Mochi's HIGH priority tasks")
    high = mochi.filter_tasks(priority=Priority.HIGH)
    rows = [[f"{PRIORITY_EMOJI[t.priority]} {t.priority.value}",
             f"{CATEGORY_EMOJI[t.category]} {t.category.value}", t.title]
            for t in high]
    print(tabulate(rows, headers=["Priority", "Category", "Task"], tablefmt="rounded_outline"))

    # ------------------------------------------------------------------
    # 4. Daily schedules
    # ------------------------------------------------------------------
    section("Daily Schedules — All Pets")
    for pet in jordan.pets:
        schedule = scheduler.generate_schedule(pet, plan_date=today)
        print(f"\n  🐾 {pet.name}'s schedule ({today})")
        rows = [
            [
                f"{st.start_time.strftime('%H:%M')}–{st.end_time.strftime('%H:%M')}",
                f"{PRIORITY_EMOJI[st.task.priority]} {st.task.priority.value}",
                f"{CATEGORY_EMOJI[st.task.category]} {st.task.title}",
                f"{st.task.duration_minutes}min",
                st.reason,
            ]
            for st in schedule.scheduled
        ]
        print(tabulate(rows, headers=["Time", "Priority", "Task", "Dur", "Reason"],
                       tablefmt="rounded_outline"))
        if schedule.skipped:
            print(f"  Skipped: {', '.join(t.title for t, _ in schedule.skipped)}")

    # ------------------------------------------------------------------
    # 5. Find next available slot (Challenge 1 — advanced algorithm)
    # ------------------------------------------------------------------
    section("Find Next Available Slot")
    for pet in jordan.pets:
        slot = scheduler.find_next_available_slot(pet, duration_minutes=25, plan_date=today)
        if slot:
            end = slot + timedelta(minutes=25)
            print(f"  {pet.name}: next free 25-min slot → {slot.strftime('%H:%M')}–{end.strftime('%H:%M')}")
        else:
            print(f"  {pet.name}: no 25-min slot available today")

    # ------------------------------------------------------------------
    # 6. Conflict detection
    # ------------------------------------------------------------------
    section("Conflict Detection Demo")
    demo_pet = Pet(name="Demo", species="dog", age=1, owner=jordan)
    t_a = Task("Task A", 60, Priority.HIGH)
    t_b = Task("Task B", 60, Priority.HIGH)
    slot_dt = datetime.combine(today, time(9, 0))
    manual = DailySchedule(plan_date=today, pet=demo_pet)
    manual.scheduled.append(ScheduledTask(task=t_a, start_time=slot_dt))
    manual.scheduled.append(ScheduledTask(task=t_b, start_time=slot_dt))
    conflicts = manual.conflicts()
    rows = [[a.task.title, f"{a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')}",
             b.task.title, f"{b.start_time.strftime('%H:%M')}–{b.end_time.strftime('%H:%M')}"]
            for a, b in conflicts]
    if rows:
        print(tabulate(rows, headers=["Task A", "Window A", "Task B", "Window B"],
                       tablefmt="rounded_outline"))

    # ------------------------------------------------------------------
    # 7. Recurring tasks
    # ------------------------------------------------------------------
    section("Recurring Task Demo")
    print(f"Mochi tasks before: {len(mochi.tasks)}")
    walk = next(t for t in mochi.tasks if t.title == "Morning walk")
    nxt = mochi.complete_task(walk, today=today)
    print(f"Mochi tasks after completing 'Morning walk': {len(mochi.tasks)}")
    if nxt:
        print(f"  → Next occurrence: '{nxt.title}' due {nxt.due_date}")

    # ------------------------------------------------------------------
    # 8. JSON persistence (Challenge 2)
    # ------------------------------------------------------------------
    section("JSON Persistence")
    jordan.save_to_json("data.json")
    print("  Saved → data.json")
    loaded = Owner.load_from_json("data.json")
    print(f"  Loaded: {loaded}")
    for pet in loaded.pets:
        print(f"    {pet}")

    # ------------------------------------------------------------------
    # 9. Cross-pet pending task table
    # ------------------------------------------------------------------
    section("All Pending Tasks Across All Pets")
    rows = [
        [
            pet.name,
            f"{PRIORITY_EMOJI[task.priority]} {task.priority.value}",
            f"{CATEGORY_EMOJI[task.category]} {task.title}",
            f"{task.duration_minutes}min",
            task.recurrence or "—",
        ]
        for pet, task in jordan.all_pending_tasks()
    ]
    print(tabulate(rows, headers=["Pet", "Priority", "Task", "Dur", "Recurs"],
                   tablefmt="rounded_outline"))


if __name__ == "__main__":
    main()
