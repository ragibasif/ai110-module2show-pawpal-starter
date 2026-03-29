"""
PawPal+ Test Suite
==================
Run: python -m pytest
"""

import pytest
from datetime import date, datetime, time

from pawpal_system import Category, Owner, Pet, Priority, Scheduler, Task


# ---------------------------------------------------------------------------
# Fixtures — reusable test objects
# ---------------------------------------------------------------------------

@pytest.fixture
def owner():
    return Owner(name="Jordan", available_start=time(7, 0), available_end=time(21, 0))


@pytest.fixture
def pet(owner):
    return Pet(name="Mochi", species="dog", age=3, owner=owner)


@pytest.fixture
def simple_task():
    return Task(title="Morning walk", duration_minutes=30, priority=Priority.HIGH, category=Category.WALK)


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

def test_task_mark_complete(simple_task):
    """mark_complete() should flip completed from False to True."""
    assert simple_task.completed is False
    simple_task.mark_complete()
    assert simple_task.completed is True


def test_task_reset(simple_task):
    """reset() should set completed back to False."""
    simple_task.mark_complete()
    simple_task.reset()
    assert simple_task.completed is False


def test_task_invalid_duration():
    """Task with non-positive duration should raise ValueError."""
    with pytest.raises(ValueError):
        Task(title="Bad task", duration_minutes=0)


def test_task_invalid_time_window():
    """earliest_start after latest_start should raise ValueError."""
    with pytest.raises(ValueError):
        Task(
            title="Impossible window",
            duration_minutes=10,
            earliest_start=time(10, 0),
            latest_start=time(9, 0),
        )


def test_task_string_priority_coercion():
    """Priority and category should accept plain strings."""
    t = Task(title="Feed", duration_minutes=5, priority="high", category="feeding")
    assert t.priority == Priority.HIGH
    assert t.category == Category.FEEDING


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

def test_pet_add_task_increases_count(pet, simple_task):
    """Adding a task should increase the pet's task list by one."""
    before = len(pet.tasks)
    pet.add_task(simple_task)
    assert len(pet.tasks) == before + 1


def test_pet_remove_task(pet, simple_task):
    """remove_task() should delete the task and return True."""
    pet.add_task(simple_task)
    result = pet.remove_task("Morning walk")
    assert result is True
    assert len(pet.tasks) == 0


def test_pet_remove_task_not_found(pet):
    """remove_task() should return False when the title doesn't exist."""
    assert pet.remove_task("Nonexistent task") is False


def test_pet_pending_tasks_excludes_completed(pet):
    """pending_tasks() should not include completed tasks."""
    t1 = Task(title="Walk", duration_minutes=20, priority=Priority.HIGH)
    t2 = Task(title="Feed", duration_minutes=10, priority=Priority.HIGH)
    pet.add_task(t1)
    pet.add_task(t2)
    t1.mark_complete()
    pending = pet.pending_tasks()
    assert len(pending) == 1
    assert pending[0].title == "Feed"


def test_pet_reset_daily_tasks(pet):
    """reset_daily_tasks() should reset only recurring tasks."""
    recurring = Task(title="Walk", duration_minutes=20, priority=Priority.HIGH, recurrence="daily")
    one_off = Task(title="Vet visit", duration_minutes=60, priority=Priority.HIGH)
    pet.add_task(recurring)
    pet.add_task(one_off)
    recurring.mark_complete()
    one_off.mark_complete()
    pet.reset_daily_tasks()
    assert recurring.completed is False   # reset because it recurs
    assert one_off.completed is True      # unchanged — one-off


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

def test_owner_add_pet_increases_count(owner, pet):
    """add_pet() should register the pet under the owner."""
    owner.add_pet(pet)
    assert len(owner.pets) == 1


def test_owner_get_pet(owner, pet):
    """get_pet() should find a pet by name (case-insensitive)."""
    owner.add_pet(pet)
    found = owner.get_pet("mochi")
    assert found is pet


def test_owner_get_pet_not_found(owner):
    """get_pet() should return None for an unknown name."""
    assert owner.get_pet("Ghost") is None


def test_owner_all_tasks(owner, pet, simple_task):
    """all_tasks() should return (pet, task) pairs across all pets."""
    pet.add_task(simple_task)
    owner.add_pet(pet)
    pairs = owner.all_tasks()
    assert len(pairs) == 1
    assert pairs[0] == (pet, simple_task)


def test_owner_all_pending_tasks_excludes_completed(owner, pet):
    """all_pending_tasks() should omit completed tasks."""
    t1 = Task(title="Walk", duration_minutes=20, priority=Priority.HIGH)
    t2 = Task(title="Feed", duration_minutes=10, priority=Priority.HIGH)
    pet.add_task(t1)
    pet.add_task(t2)
    t1.mark_complete()
    owner.add_pet(pet)
    pending = owner.all_pending_tasks()
    assert len(pending) == 1
    assert pending[0][1].title == "Feed"


def test_owner_available_minutes(owner):
    """available_minutes should reflect the 07:00–21:00 window = 840 min."""
    assert owner.available_minutes == 840


# ---------------------------------------------------------------------------
# Sorting tests
# ---------------------------------------------------------------------------

def test_sort_high_before_medium_before_low(owner, pet):
    """_sort_tasks should return tasks in high → medium → low order."""
    low  = Task(title="Low task",  duration_minutes=10, priority=Priority.LOW)
    med  = Task(title="Med task",  duration_minutes=10, priority=Priority.MEDIUM)
    high = Task(title="High task", duration_minutes=10, priority=Priority.HIGH)
    pet.add_task(low)
    pet.add_task(med)
    pet.add_task(high)

    scheduler = Scheduler()
    result = scheduler._sort_tasks(pet.tasks)
    priorities = [t.priority for t in result]
    assert priorities == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]


def test_sort_medication_first_within_priority(owner, pet):
    """Within the same priority, MEDICATION tasks should appear before others."""
    walk = Task(title="Walk", duration_minutes=30,
                priority=Priority.HIGH, category=Category.WALK)
    meds = Task(title="Meds", duration_minutes=5,
                priority=Priority.HIGH, category=Category.MEDICATION)
    pet.add_task(walk)
    pet.add_task(meds)

    scheduler = Scheduler()
    result = scheduler._sort_tasks(pet.tasks)
    assert result[0].category == Category.MEDICATION


def test_sort_shorter_tasks_first_as_tiebreaker(owner, pet):
    """Among same priority and category, shorter duration should come first."""
    long_task  = Task(title="Long",  duration_minutes=60, priority=Priority.MEDIUM)
    short_task = Task(title="Short", duration_minutes=10, priority=Priority.MEDIUM)
    pet.add_task(long_task)
    pet.add_task(short_task)

    scheduler = Scheduler()
    result = scheduler._sort_tasks(pet.tasks)
    assert result[0].duration_minutes == 10


# ---------------------------------------------------------------------------
# Recurring task tests
# ---------------------------------------------------------------------------

def test_recurring_task_creates_next_occurrence(pet):
    """complete_task() on a daily recurring task should append a new Task."""
    recurring = Task(title="Walk", duration_minutes=20,
                     priority=Priority.HIGH, recurrence="daily")
    pet.add_task(recurring)
    before = len(pet.tasks)

    today = date.today()
    next_task = pet.complete_task(recurring, today=today)

    assert len(pet.tasks) == before + 1
    assert next_task is not None
    assert next_task.completed is False
    assert next_task.due_date == today + __import__("datetime").timedelta(days=1)


def test_non_recurring_task_no_next_occurrence(pet):
    """complete_task() on a one-off task should not add a new Task."""
    one_off = Task(title="Vet visit", duration_minutes=60, priority=Priority.HIGH)
    pet.add_task(one_off)
    before = len(pet.tasks)

    result = pet.complete_task(one_off)
    assert result is None
    assert len(pet.tasks) == before  # no new task added


def test_weekly_recurrence_due_date(pet):
    """Weekly task next occurrence should be exactly 7 days later."""
    weekly = Task(title="Bath", duration_minutes=30,
                  priority=Priority.LOW, recurrence="weekly")
    pet.add_task(weekly)
    today = date.today()
    next_task = pet.complete_task(weekly, today=today)
    from datetime import timedelta
    assert next_task.due_date == today + timedelta(weeks=1)


# ---------------------------------------------------------------------------
# Conflict detection tests
# ---------------------------------------------------------------------------

def test_conflict_detection_catches_overlap(owner, pet):
    """conflicts() should return a pair when two ScheduledTasks overlap."""
    from datetime import datetime
    from pawpal_system import DailySchedule, ScheduledTask

    t_a = Task(title="Task A", duration_minutes=60, priority=Priority.HIGH)
    t_b = Task(title="Task B", duration_minutes=60, priority=Priority.HIGH)
    slot = datetime.combine(date.today(), time(9, 0))

    schedule = DailySchedule(plan_date=date.today(), pet=pet)
    schedule.scheduled.append(ScheduledTask(task=t_a, start_time=slot))
    schedule.scheduled.append(ScheduledTask(task=t_b, start_time=slot))

    assert len(schedule.conflicts()) == 1


def test_no_conflict_for_sequential_tasks(owner, pet):
    """conflicts() should return empty list for back-to-back non-overlapping tasks."""
    from datetime import datetime, timedelta
    from pawpal_system import DailySchedule, ScheduledTask

    t_a = Task(title="Task A", duration_minutes=30, priority=Priority.HIGH)
    t_b = Task(title="Task B", duration_minutes=30, priority=Priority.HIGH)
    slot_a = datetime.combine(date.today(), time(9, 0))
    slot_b = slot_a + timedelta(minutes=30)

    schedule = DailySchedule(plan_date=date.today(), pet=pet)
    schedule.scheduled.append(ScheduledTask(task=t_a, start_time=slot_a))
    schedule.scheduled.append(ScheduledTask(task=t_b, start_time=slot_b))

    assert schedule.conflicts() == []


# ---------------------------------------------------------------------------
# Scheduler integration tests
# ---------------------------------------------------------------------------

def test_scheduler_produces_conflict_free_schedule(owner, pet):
    """The greedy Scheduler should never produce conflicting ScheduledTasks."""
    pet.add_task(Task(title="Walk",  duration_minutes=30, priority=Priority.HIGH))
    pet.add_task(Task(title="Feed",  duration_minutes=10, priority=Priority.HIGH))
    pet.add_task(Task(title="Groom", duration_minutes=20, priority=Priority.LOW))

    schedule = Scheduler().generate_schedule(pet, plan_date=date.today())
    assert schedule.conflicts() == []


# ---------------------------------------------------------------------------
# Weighted scoring tests
# ---------------------------------------------------------------------------

def test_weighted_score_medication_beats_walk_same_priority(owner, pet):
    """Medication should have a lower weighted score than a walk at same priority."""
    meds = Task(title="Meds", duration_minutes=5,
                priority=Priority.HIGH, category=Category.MEDICATION)
    walk = Task(title="Walk", duration_minutes=5,
                priority=Priority.HIGH, category=Category.WALK)
    s = Scheduler()
    assert s._weighted_score(meds) < s._weighted_score(walk)


def test_weighted_score_tighter_window_sorts_first(owner, pet):
    """A task with an earlier latest_start should score lower (more urgent)."""
    tight = Task(title="Tight", duration_minutes=10, priority=Priority.HIGH,
                 earliest_start=time(8, 0), latest_start=time(9, 0))
    loose = Task(title="Loose", duration_minutes=10, priority=Priority.HIGH,
                 earliest_start=time(8, 0), latest_start=time(18, 0))
    s = Scheduler()
    assert s._weighted_score(tight) < s._weighted_score(loose)


def test_weighted_score_high_always_beats_medium(owner, pet):
    """Any high-priority task should score lower than any medium-priority task."""
    high = Task(title="H", duration_minutes=240, priority=Priority.HIGH)
    med  = Task(title="M", duration_minutes=1,   priority=Priority.MEDIUM)
    s = Scheduler()
    assert s._weighted_score(high) < s._weighted_score(med)


# ---------------------------------------------------------------------------
# find_next_available_slot tests
# ---------------------------------------------------------------------------

def test_find_slot_returns_start_of_day_when_no_tasks(owner, pet):
    """With no tasks, the first available slot should be the owner's available_start."""
    slot = Scheduler().find_next_available_slot(pet, duration_minutes=30, plan_date=date.today())
    assert slot is not None
    assert slot.time() == owner.available_start


def test_find_slot_after_scheduled_tasks(owner, pet):
    """Slot finder should return a gap after existing tasks."""
    pet.add_task(Task(title="Walk", duration_minutes=60, priority=Priority.HIGH))
    slot = Scheduler().find_next_available_slot(pet, duration_minutes=10, plan_date=date.today())
    assert slot is not None
    # Should be at 08:00 (after 07:00–08:00 walk)
    assert slot >= datetime.combine(date.today(), time(7, 0))


def test_find_slot_returns_none_when_day_full(owner):
    """Should return None when no gap of the required size exists."""
    # 14-hour window, fill it with a 14-hour task so nothing fits
    full_owner = Owner(name="Busy", available_start=time(7, 0), available_end=time(21, 0))
    full_pet = Pet(name="P", species="dog", age=1, owner=full_owner)
    full_pet.add_task(Task(title="All day", duration_minutes=840, priority=Priority.HIGH))
    slot = Scheduler().find_next_available_slot(full_pet, duration_minutes=30, plan_date=date.today())
    assert slot is None


# ---------------------------------------------------------------------------
# JSON persistence tests
# ---------------------------------------------------------------------------

def test_owner_save_and_load_roundtrip(tmp_path, owner, pet, simple_task):
    """save_to_json + load_from_json should reconstruct the full object graph."""
    pet.add_task(simple_task)
    owner.add_pet(pet)
    path = str(tmp_path / "test_data.json")
    owner.save_to_json(path)

    loaded = Owner.load_from_json(path)
    assert loaded is not None
    assert loaded.name == owner.name
    assert loaded.available_start == owner.available_start
    assert len(loaded.pets) == 1
    assert loaded.pets[0].name == pet.name
    assert len(loaded.pets[0].tasks) == 1
    assert loaded.pets[0].tasks[0].title == simple_task.title


def test_load_returns_none_for_missing_file():
    """load_from_json should return None if the file doesn't exist."""
    result = Owner.load_from_json("/nonexistent/path/data.json")
    assert result is None


def test_task_serialisation_roundtrip():
    """Task.to_dict() → Task.from_dict() should preserve all fields."""
    original = Task(
        title="Meds",
        duration_minutes=5,
        priority=Priority.HIGH,
        category=Category.MEDICATION,
        completed=True,
        due_date=date(2026, 4, 1),
        earliest_start=time(8, 0),
        latest_start=time(10, 0),
        recurrence="daily",
        notes="With food",
    )
    restored = Task.from_dict(original.to_dict())
    assert restored.title == original.title
    assert restored.priority == original.priority
    assert restored.category == original.category
    assert restored.completed == original.completed
    assert restored.due_date == original.due_date
    assert restored.earliest_start == original.earliest_start
    assert restored.latest_start == original.latest_start
    assert restored.recurrence == original.recurrence
    assert restored.notes == original.notes


def test_scheduler_skips_tasks_that_exceed_day(owner):
    """Tasks that don't fit in the day window should appear in skipped."""
    tight_owner = Owner(name="Tight", available_start=time(9, 0), available_end=time(9, 10))
    pet = Pet(name="Buddy", species="dog", age=2, owner=tight_owner)
    pet.add_task(Task(title="Quick feed", duration_minutes=5,  priority=Priority.HIGH))
    pet.add_task(Task(title="Long walk",  duration_minutes=120, priority=Priority.MEDIUM))

    schedule = Scheduler().generate_schedule(pet, plan_date=date.today())
    scheduled_titles = [st.task.title for st in schedule.scheduled]
    skipped_titles   = [t.title for t, _ in schedule.skipped]

    assert "Quick feed" in scheduled_titles
    assert "Long walk"  in skipped_titles
