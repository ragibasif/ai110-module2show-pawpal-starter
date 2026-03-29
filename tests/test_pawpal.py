"""
PawPal+ Test Suite
==================
Run: python -m pytest
"""

import pytest
from datetime import date, time

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
