"""
PawPal+ Core System
===================
Modular pet care management system using OOP.

Class hierarchy:
  Owner → Pet → Task → ScheduledTask → DailySchedule
  Scheduler orchestrates the planning algorithm.
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
# Core domain classes
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """Represents a pet owner with daily availability preferences."""
    name: str
    available_start: time = time(7, 0)   # earliest time owner can do tasks
    available_end: time = time(21, 0)    # latest time owner can do tasks

    @property
    def available_minutes(self) -> int:
        """Total minutes available in the day window."""
        start_dt = datetime.combine(date.today(), self.available_start)
        end_dt = datetime.combine(date.today(), self.available_end)
        return int((end_dt - start_dt).total_seconds() // 60)

    def __str__(self) -> str:
        return (
            f"Owner({self.name}, "
            f"available {self.available_start.strftime('%H:%M')}–"
            f"{self.available_end.strftime('%H:%M')})"
        )


@dataclass
class Pet:
    """Represents a pet with basic profile information."""
    name: str
    species: str
    age: int  # in years
    owner: Owner

    def __str__(self) -> str:
        return f"Pet({self.name}, {self.species}, age {self.age})"


@dataclass
class Task:
    """
    A single care task that can be scheduled.

    Attributes:
        title            Human-readable name (e.g. "Morning walk")
        duration_minutes How long the task takes
        priority         high / medium / low
        category         walk / feeding / medication / grooming / enrichment / appointment / other
        earliest_start   Optional: task cannot start before this time
        latest_start     Optional: task must start by this time (soft deadline)
        recurrence       Optional: "daily", "weekdays", "weekly", or None (one-off)
        notes            Free text for owner reminders
    """
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: Category = Category.OTHER
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

    def __str__(self) -> str:
        window = ""
        if self.earliest_start and self.latest_start:
            window = (
                f" [{self.earliest_start.strftime('%H:%M')}–"
                f"{self.latest_start.strftime('%H:%M')}]"
            )
        return (
            f"Task({self.title!r}, {self.duration_minutes}min, "
            f"{self.priority.value}, {self.category.value}{window})"
        )


@dataclass
class ScheduledTask:
    """A task that has been assigned a concrete start time."""
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
    plus any tasks that could not be fit into the day.
    """
    plan_date: date
    pet: Pet
    scheduled: list[ScheduledTask] = field(default_factory=list)
    skipped: list[tuple[Task, str]] = field(default_factory=list)  # (task, reason)

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
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Generates a DailySchedule for a pet given a list of Tasks.

    Algorithm overview:
      1. Sort tasks using _sort_tasks() — you implement the scoring logic.
      2. Walk through sorted tasks greedily, assigning start times.
      3. Respect the owner's available window and any per-task time constraints.
      4. Record skipped tasks with a reason.
    """

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """
        Return tasks sorted in the order they should be scheduled.

        TODO: Implement your sorting strategy here.

        Hints to consider:
          - Priority (high > medium > low) should be the primary factor.
          - Among equal priority, should shorter tasks go first (fit more in)?
            Or should tasks with tighter time windows go first?
          - Medications are time-sensitive — should category factor in?
          - You have ~5-8 lines of logic to write here.

        Parameters:
            tasks: unsorted list of Task objects

        Returns:
            A new list sorted in scheduling order.
        """
        # YOUR CODE HERE
        raise NotImplementedError("Implement _sort_tasks() — see the docstring above.")

    def _fits_in_window(self, task: Task, slot: datetime, day: date) -> tuple[bool, str]:
        """
        Check whether a task can start at `slot` without violating its time window.

        Returns (True, "") if it fits, or (False, reason_string) if not.
        """
        if task.earliest_start:
            earliest_dt = datetime.combine(day, task.earliest_start)
            if slot < earliest_dt:
                return False, f"starts before earliest allowed time {task.earliest_start.strftime('%H:%M')}"

        if task.latest_start:
            latest_dt = datetime.combine(day, task.latest_start)
            if slot > latest_dt:
                return False, f"no slot before latest start {task.latest_start.strftime('%H:%M')}"

        return True, ""

    def generate_schedule(
        self,
        pet: Pet,
        tasks: list[Task],
        plan_date: Optional[date] = None,
    ) -> DailySchedule:
        """
        Produce a DailySchedule for `pet` using `tasks`.

        Steps:
          1. Sort tasks via _sort_tasks().
          2. Greedily assign each task the next free slot.
          3. Skip tasks that no longer fit within the owner's window.
          4. Return a DailySchedule with scheduled + skipped tasks.
        """
        if plan_date is None:
            plan_date = date.today()

        schedule = DailySchedule(plan_date=plan_date, pet=pet)
        owner = pet.owner

        # Current pointer into the day — starts at owner's available_start
        current_slot = datetime.combine(plan_date, owner.available_start)
        day_end = datetime.combine(plan_date, owner.available_end)

        sorted_tasks = self._sort_tasks(tasks)

        for task in sorted_tasks:
            task_end = current_slot + timedelta(minutes=task.duration_minutes)

            # Does it exceed the owner's available window?
            if task_end > day_end:
                schedule.skipped.append(
                    (task, f"not enough time remaining in the day ({task.duration_minutes}min needed)")
                )
                continue

            # If we're too early for this task's window, defer (advance the slot)
            if task.earliest_start:
                earliest_dt = datetime.combine(plan_date, task.earliest_start)
                if current_slot < earliest_dt:
                    current_slot = earliest_dt
                    task_end = current_slot + timedelta(minutes=task.duration_minutes)
                    # Re-check whether it still fits in the day after deferring
                    if task_end > day_end:
                        schedule.skipped.append(
                            (task, f"earliest start {task.earliest_start.strftime('%H:%M')} leaves no time to complete it")
                        )
                        continue

            # Does it respect the task's latest_start hard deadline?
            fits, reason = self._fits_in_window(task, current_slot, plan_date)
            if not fits:
                schedule.skipped.append((task, reason))
                continue

            reasoning = self._build_reason(task, current_slot)
            schedule.scheduled.append(
                ScheduledTask(task=task, start_time=current_slot, reason=reasoning)
            )
            current_slot = task_end  # advance the pointer

        return schedule

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_reason(task: Task, slot: datetime) -> str:
        """Generate a human-readable explanation for why a task was placed here."""
        priority_phrases = {
            Priority.HIGH: "High priority",
            Priority.MEDIUM: "Medium priority",
            Priority.LOW: "Low priority",
        }
        base = priority_phrases[task.priority]
        if task.category == Category.MEDICATION:
            base += " — medication tasks are scheduled first to ensure they're not missed"
        if task.recurrence:
            base += f"; recurs {task.recurrence}"
        return base
