"""
PawPal+ Core System
===================
Modular pet care management system using OOP.

Ownership chain:
  Owner  ──owns──►  Pet  ──owns──►  Task
  Scheduler navigates this chain to build a DailySchedule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    WALK = "walk"
    FEEDING = "feeding"
    MEDICATION = "medication"
    GROOMING = "grooming"
    ENRICHMENT = "enrichment"
    APPOINTMENT = "appointment"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """
    A single pet care activity.

    Attributes:
        title            Human-readable name (e.g. "Morning walk")
        duration_minutes How long the task takes
        priority         high / medium / low
        category         walk / feeding / medication / grooming / enrichment / appointment / other
        completed        Whether the task has been marked done today
        earliest_start   Optional: task cannot start before this time
        latest_start     Optional: task must start by this time (soft deadline)
        recurrence       Optional: "daily", "weekdays", "weekly", or None (one-off)
        notes            Free text for owner reminders
    """
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: Category = Category.OTHER
    completed: bool = False
    earliest_start: Optional[time] = None
    latest_start: Optional[time] = None
    recurrence: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        # Accept raw strings and coerce to enums for convenience
        if isinstance(self.priority, str):
            self.priority = Priority(self.priority.lower())
        if isinstance(self.category, str):
            self.category = Category(self.category.lower())
        # Validate duration
        if self.duration_minutes <= 0:
            raise ValueError(f"duration_minutes must be positive, got {self.duration_minutes}")
        # Validate time window consistency
        if self.earliest_start and self.latest_start:
            if self.earliest_start >= self.latest_start:
                raise ValueError(
                    f"earliest_start ({self.earliest_start}) must be before "
                    f"latest_start ({self.latest_start})"
                )

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def reset(self) -> None:
        """Reset completion status (e.g. at the start of a new day)."""
        self.completed = False

    def __str__(self) -> str:
        status = "✓" if self.completed else "○"
        window = ""
        if self.earliest_start and self.latest_start:
            window = (
                f" [{self.earliest_start.strftime('%H:%M')}–"
                f"{self.latest_start.strftime('%H:%M')}]"
            )
        return (
            f"{status} Task({self.title!r}, {self.duration_minutes}min, "
            f"{self.priority.value}, {self.category.value}{window})"
        )


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """
    Represents a pet. Owns a list of care tasks.

    The Pet is the unit of scheduling — each DailySchedule is built
    for one Pet, using its task list.
    """
    name: str
    species: str
    age: int          # years
    owner: Owner      # back-reference so schedule can read availability

    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> bool:
        """
        Remove the first task whose title matches (case-insensitive).
        Returns True if a task was removed, False if not found.
        """
        for i, t in enumerate(self.tasks):
            if t.title.lower() == title.lower():
                self.tasks.pop(i)
                return True
        return False

    def pending_tasks(self) -> list[Task]:
        """Return tasks that have not yet been marked complete."""
        return [t for t in self.tasks if not t.completed]

    def completed_tasks(self) -> list[Task]:
        """Return tasks that have been marked complete."""
        return [t for t in self.tasks if t.completed]

    def reset_daily_tasks(self) -> None:
        """Reset all recurring tasks at the start of a new day."""
        for task in self.tasks:
            if task.recurrence:
                task.reset()

    def __str__(self) -> str:
        return (
            f"Pet({self.name}, {self.species}, age {self.age}, "
            f"{len(self.tasks)} task(s))"
        )


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """
    Represents a pet owner. Manages multiple pets and sets the
    availability window used by the Scheduler.
    """
    name: str
    available_start: time = time(7, 0)    # earliest the owner can do tasks
    available_end: time = time(21, 0)     # latest the owner can do tasks

    pets: list[Pet] = field(default_factory=list)

    # -- Pet management ------------------------------------------------------

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def get_pet(self, name: str) -> Optional[Pet]:
        """Look up a pet by name (case-insensitive). Returns None if not found."""
        for p in self.pets:
            if p.name.lower() == name.lower():
                return p
        return None

    # -- Task access ---------------------------------------------------------

    def all_tasks(self) -> list[tuple[Pet, Task]]:
        """
        Return every task across all pets as (pet, task) pairs.
        Useful for a cross-pet overview.
        """
        return [(pet, task) for pet in self.pets for task in pet.tasks]

    def all_pending_tasks(self) -> list[tuple[Pet, Task]]:
        """Return only incomplete tasks across all pets."""
        return [(pet, task) for pet in self.pets for task in pet.pending_tasks()]

    # -- Availability --------------------------------------------------------

    @property
    def available_minutes(self) -> int:
        """Total minutes available in the owner's daily window."""
        start_dt = datetime.combine(date.today(), self.available_start)
        end_dt = datetime.combine(date.today(), self.available_end)
        return int((end_dt - start_dt).total_seconds() // 60)

    def __str__(self) -> str:
        return (
            f"Owner({self.name}, "
            f"{self.available_start.strftime('%H:%M')}–{self.available_end.strftime('%H:%M')}, "
            f"{len(self.pets)} pet(s))"
        )


# ---------------------------------------------------------------------------
# ScheduledTask + DailySchedule  (output layer)
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A Task that has been assigned a concrete start time in a DailySchedule."""
    task: Task
    start_time: datetime
    reason: str = ""

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.task.duration_minutes)

    def __str__(self) -> str:
        return (
            f"  {self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')} "
            f"[{self.task.priority.value.upper()}] {self.task.title}"
        )


@dataclass
class DailySchedule:
    """
    The output of the Scheduler: an ordered list of ScheduledTasks
    plus tasks that could not be fit into the day.
    """
    plan_date: date
    pet: Pet
    scheduled: list[ScheduledTask] = field(default_factory=list)
    skipped: list[tuple[Task, str]] = field(default_factory=list)

    @property
    def total_minutes_scheduled(self) -> int:
        return sum(st.task.duration_minutes for st in self.scheduled)

    def conflicts(self) -> list[tuple[ScheduledTask, ScheduledTask]]:
        """Return pairs of ScheduledTasks whose time windows overlap."""
        problems = []
        for i, a in enumerate(self.scheduled):
            for b in self.scheduled[i + 1:]:
                if a.start_time < b.end_time and b.start_time < a.end_time:
                    problems.append((a, b))
        return problems

    def pretty_print(self) -> None:
        print(f"\n{'='*54}")
        print(f"  PawPal+ Daily Schedule — {self.plan_date}")
        print(f"  Pet: {self.pet.name}  |  Owner: {self.pet.owner.name}")
        print(f"{'='*54}")
        if not self.scheduled:
            print("  (no tasks scheduled)")
        for st in self.scheduled:
            print(st)
            if st.reason:
                print(f"      ↳ {st.reason}")
        if self.skipped:
            print(f"\n  Skipped ({len(self.skipped)}):")
            for task, reason in self.skipped:
                print(f"    ✗ {task.title} — {reason}")
        conflicts = self.conflicts()
        if conflicts:
            print(f"\n  ⚠ Conflicts detected ({len(conflicts)}):")
            for a, b in conflicts:
                print(f"    {a.task.title} overlaps {b.task.title}")
        total_h = self.total_minutes_scheduled // 60
        total_m = self.total_minutes_scheduled % 60
        print(f"\n  Total time scheduled: {total_h}h {total_m}m")
        print(f"{'='*54}\n")


# ---------------------------------------------------------------------------
# Scheduler  — the "brain"
# ---------------------------------------------------------------------------

class Scheduler:
    """
    The scheduling engine. Retrieves tasks from a Pet (or all of an Owner's
    pets) and produces a time-stamped DailySchedule.

    Algorithm overview:
      1. Collect pending (incomplete) tasks from the pet.
      2. Sort them via _sort_tasks() — YOUR logic goes here.
      3. Walk through the sorted list greedily, assigning start times.
      4. Respect the owner's availability window and per-task time constraints.
      5. Record skipped tasks with a human-readable reason.
    """

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """
        Return tasks in the order they should be scheduled.

        TODO: Implement your sorting strategy here (~5-8 lines).

        You have access to:
            task.priority         → Priority.HIGH / .MEDIUM / .LOW
            task.category         → Category.MEDICATION / .WALK / etc.
            task.duration_minutes → integer
            task.earliest_start   → time or None
            task.latest_start     → time or None

        Decisions to make:
          1. Map Priority enum values to numeric weights so Python's
             sorted() can compare them (high=0, medium=1, low=2).
          2. Choose a tiebreaker for equal-priority tasks.
             (shorter first? tighter time window first?)
          3. Should MEDICATION always jump the queue regardless of priority?

        Return a NEW sorted list — do not mutate the input.
        """
        # YOUR CODE HERE
        raise NotImplementedError("Implement _sort_tasks() — see the docstring above.")

    # -- Public API ----------------------------------------------------------

    def generate_schedule(
        self,
        pet: Pet,
        plan_date: Optional[date] = None,
        tasks: Optional[list[Task]] = None,
    ) -> DailySchedule:
        """
        Build a DailySchedule for a single pet.

        Retrieves tasks from pet.pending_tasks() by default.
        Pass `tasks` explicitly to override (useful for testing).
        """
        if plan_date is None:
            plan_date = date.today()
        if tasks is None:
            tasks = pet.pending_tasks()

        schedule = DailySchedule(plan_date=plan_date, pet=pet)
        owner = pet.owner
        current_slot = datetime.combine(plan_date, owner.available_start)
        day_end = datetime.combine(plan_date, owner.available_end)

        for task in self._sort_tasks(tasks):
            task_end = current_slot + timedelta(minutes=task.duration_minutes)

            # Not enough day left at all?
            if task_end > day_end:
                schedule.skipped.append((
                    task,
                    f"not enough time remaining ({task.duration_minutes}min needed)",
                ))
                continue

            # Too early? Defer the slot to the task's earliest_start.
            if task.earliest_start:
                earliest_dt = datetime.combine(plan_date, task.earliest_start)
                if current_slot < earliest_dt:
                    current_slot = earliest_dt
                    task_end = current_slot + timedelta(minutes=task.duration_minutes)
                    if task_end > day_end:
                        schedule.skipped.append((
                            task,
                            f"earliest start {task.earliest_start.strftime('%H:%M')} "
                            f"leaves no time to complete it",
                        ))
                        continue

            # Missed the latest_start deadline?
            if task.latest_start:
                latest_dt = datetime.combine(plan_date, task.latest_start)
                if current_slot > latest_dt:
                    schedule.skipped.append((
                        task,
                        f"missed latest start deadline of {task.latest_start.strftime('%H:%M')}",
                    ))
                    continue

            schedule.scheduled.append(ScheduledTask(
                task=task,
                start_time=current_slot,
                reason=self._build_reason(task),
            ))
            current_slot = task_end

        return schedule

    def generate_all_schedules(
        self,
        owner: Owner,
        plan_date: Optional[date] = None,
    ) -> list[DailySchedule]:
        """
        Generate a DailySchedule for every pet registered under an owner.
        Returns one DailySchedule per pet.
        """
        return [
            self.generate_schedule(pet, plan_date=plan_date)
            for pet in owner.pets
        ]

    # -- Private helpers -----------------------------------------------------

    @staticmethod
    def _build_reason(task: Task) -> str:
        """Generate a human-readable explanation for why a task was placed here."""
        priority_phrases = {
            Priority.HIGH: "High priority",
            Priority.MEDIUM: "Medium priority",
            Priority.LOW: "Low priority",
        }
        base = priority_phrases[task.priority]
        if task.category == Category.MEDICATION:
            base += " — medication scheduled early to avoid missed doses"
        if task.recurrence:
            base += f"; recurs {task.recurrence}"
        return base
