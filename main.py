"""
PawPal+ CLI Demo
================
Verify the backend logic end-to-end before connecting the Streamlit UI.
Run: python main.py
"""

from datetime import date, time

from pawpal_system import Category, Owner, Pet, Priority, Scheduler, Task


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Create owner
    # ------------------------------------------------------------------
    jordan = Owner(
        name="Jordan",
        available_start=time(7, 0),
        available_end=time(21, 0),
    )

    # ------------------------------------------------------------------
    # 2. Create pets and register them with the owner
    # ------------------------------------------------------------------
    mochi = Pet(name="Mochi", species="dog", age=3, owner=jordan)
    luna = Pet(name="Luna", species="cat", age=5, owner=jordan)

    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    # ------------------------------------------------------------------
    # 3. Add tasks to Mochi (dog tasks)
    # ------------------------------------------------------------------
    mochi.add_task(Task(
        title="Morning walk",
        duration_minutes=30,
        priority=Priority.HIGH,
        category=Category.WALK,
        recurrence="daily",
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
        title="Afternoon play",
        duration_minutes=20,
        priority=Priority.MEDIUM,
        category=Category.ENRICHMENT,
        earliest_start=time(14, 0),
    ))
    mochi.add_task(Task(
        title="Grooming brush",
        duration_minutes=15,
        priority=Priority.LOW,
        category=Category.GROOMING,
    ))

    # ------------------------------------------------------------------
    # 4. Add tasks to Luna (cat tasks)
    # ------------------------------------------------------------------
    luna.add_task(Task(
        title="Breakfast feeding",
        duration_minutes=5,
        priority=Priority.HIGH,
        category=Category.FEEDING,
        recurrence="daily",
    ))
    luna.add_task(Task(
        title="Thyroid medication",
        duration_minutes=5,
        priority=Priority.HIGH,
        category=Category.MEDICATION,
        earliest_start=time(8, 0),
        latest_start=time(9, 0),
        recurrence="daily",
        notes="Hide in treat",
    ))
    luna.add_task(Task(
        title="Interactive toy session",
        duration_minutes=15,
        priority=Priority.MEDIUM,
        category=Category.ENRICHMENT,
    ))

    # ------------------------------------------------------------------
    # 5. Print owner + pet overview
    # ------------------------------------------------------------------
    print(f"\n{'='*54}")
    print(f"  Owner: {jordan}")
    for pet in jordan.pets:
        print(f"  {pet}")
        for task in pet.tasks:
            print(f"    {task}")

    # ------------------------------------------------------------------
    # 6. Run the scheduler for all pets
    # ------------------------------------------------------------------
    scheduler = Scheduler()
    today = date.today()
    schedules = scheduler.generate_all_schedules(jordan, plan_date=today)

    for schedule in schedules:
        schedule.pretty_print()

    # ------------------------------------------------------------------
    # 7. Demo: mark a task complete and show it disappears from pending
    # ------------------------------------------------------------------
    print("--- Marking Mochi's 'Morning walk' as complete ---")
    mochi.tasks[0].mark_complete()
    print(f"Mochi pending tasks after completion: {len(mochi.pending_tasks())}")
    print(f"Mochi completed tasks: {[t.title for t in mochi.completed_tasks()]}")

    # ------------------------------------------------------------------
    # 8. Cross-pet overview via owner
    # ------------------------------------------------------------------
    print(f"\nAll pending tasks across all pets ({jordan.name}):")
    for pet, task in jordan.all_pending_tasks():
        print(f"  [{pet.name}] {task.title} ({task.priority.value})")


if __name__ == "__main__":
    main()
