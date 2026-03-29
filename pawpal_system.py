"""
PawPal+ Core System
===================
Modular pet care management system using OOP.

Ownership chain:
  Owner  ──owns──►  Pet  ──owns──►  Task
  Scheduler navigates this chain to build a DailySchedule.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Optional


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
    due_date: Optional[date] = None       # None means "any day" (not date-bound)
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

    def next_occurrence(self, from_date: Optional[date] = None) -> Optional[Task]:
        """
        Return a new Task for the next scheduled occurrence of this recurring task.
        Returns None if the task has no recurrence set.

        from_date defaults to today. The new task's due_date is set to:
          - daily     → from_date + 1 day
          - weekdays  → from_date + 1 day, skipping Saturday/Sunday
          - weekly    → from_date + 7 days
        """
        if not self.recurrence:
            return None

        base = from_date or date.today()

        if self.recurrence == "daily":
            next_date = base + timedelta(days=1)
        elif self.recurrence == "weekdays":
            next_date = base + timedelta(days=1)
            while next_date.weekday() >= 5:   # 5=Saturday, 6=Sunday
                next_date += timedelta(days=1)
        elif self.recurrence == "weekly":
            next_date = base + timedelta(weeks=1)
        else:
            next_date = base + timedelta(days=1)  # fallback: treat as daily

        # Return a fresh copy with reset completion and updated due_date
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            category=self.category,
            completed=False,
            due_date=next_date,
            earliest_start=self.earliest_start,
            latest_start=self.latest_start,
            recurrence=self.recurrence,
            notes=self.notes,
        )

    # -- Serialisation -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dictionary."""
        return {
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.value,
            "category": self.category.value,
            "completed": self.completed,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "earliest_start": self.earliest_start.strftime("%H:%M") if self.earliest_start else None,
            "latest_start": self.latest_start.strftime("%H:%M") if self.latest_start else None,
            "recurrence": self.recurrence,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Reconstruct a Task from a serialised dictionary."""
        def _time(s: Optional[str]) -> Optional[time]:
            if not s:
                return None
            h, m = s.split(":")
            return time(int(h), int(m))

        return cls(
            title=data["title"],
            duration_minutes=data["duration_minutes"],
            priority=data.get("priority", "medium"),
            category=data.get("category", "other"),
            completed=data.get("completed", False),
            due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            earliest_start=_time(data.get("earliest_start")),
            latest_start=_time(data.get("latest_start")),
            recurrence=data.get("recurrence"),
            notes=data.get("notes", ""),
        )

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

    def complete_task(self, task: Task, today: Optional[date] = None) -> Optional[Task]:
        """
        Mark a task complete. If it recurs, queue the next occurrence.

        Returns the newly created next-occurrence Task (already added to
        this pet's task list), or None for one-off tasks.
        """
        task.mark_complete()
        next_task = task.next_occurrence(from_date=today or date.today())
        if next_task:
            self.tasks.append(next_task)
        return next_task

    def filter_tasks(
        self,
        completed: Optional[bool] = None,
        category: Optional[Category] = None,
        priority: Optional[Priority] = None,
    ) -> list[Task]:
        """
        Return tasks filtered by optional criteria.
        Pass None for a criterion to skip that filter.
        """
        result = self.tasks
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        if category is not None:
            result = [t for t in result if t.category == category]
        if priority is not None:
            result = [t for t in result if t.priority == priority]
        return result

    def reset_daily_tasks(self) -> None:
        """Reset all recurring tasks at the start of a new day."""
        for task in self.tasks:
            if task.recurrence:
                task.reset()

    # -- Serialisation -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dictionary (owner reference excluded)."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], owner: Owner) -> Pet:
        """Reconstruct a Pet from a serialised dictionary."""
        pet = cls(
            name=data["name"],
            species=data["species"],
            age=data["age"],
            owner=owner,
        )
        pet.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        return pet

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

    # -- Serialisation -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise the full owner → pets → tasks graph to a dictionary."""
        return {
            "name": self.name,
            "available_start": self.available_start.strftime("%H:%M"),
            "available_end": self.available_end.strftime("%H:%M"),
            "pets": [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Owner:
        """Reconstruct an Owner (and all nested Pets/Tasks) from a dictionary."""
        def _time(s: str) -> time:
            h, m = s.split(":")
            return time(int(h), int(m))

        owner = cls(
            name=data["name"],
            available_start=_time(data.get("available_start", "07:00")),
            available_end=_time(data.get("available_end", "21:00")),
        )
        owner.pets = [Pet.from_dict(p, owner) for p in data.get("pets", [])]
        return owner

    def save_to_json(self, path: str = "data.json") -> None:
        """Persist the full owner graph to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, path: str = "data.json") -> Optional[Owner]:
        """Load an Owner from a JSON file. Returns None if the file doesn't exist."""
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return cls.from_dict(json.load(f))

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

    def _weighted_score(self, task: Task) -> float:
        """
        Compute a continuous priority score for a task. Lower = scheduled sooner.

        Factors and weights:
          - Priority tier:    high=0, medium=100, low=200  (dominant factor)
          - Category urgency: medication gets -10 bonus within its tier
          - Window tightness: tasks with an earlier latest_start are more urgent;
            we add a small fractional penalty proportional to the latest_start
            time so tighter windows sort before looser ones at equal priority.
          - Duration:         sub-penny tiebreaker so shorter tasks go first
            when everything else is equal (packs more tasks into the day).
        """
        priority_base = {Priority.HIGH: 0.0, Priority.MEDIUM: 100.0, Priority.LOW: 200.0}
        score = priority_base[task.priority]

        if task.category == Category.MEDICATION:
            score -= 10.0

        if task.latest_start:
            # Normalise to [0, 1): earlier deadline → smaller addend → higher urgency
            window_minutes = task.latest_start.hour * 60 + task.latest_start.minute
            score += window_minutes / 1440.0

        score += task.duration_minutes / 10_000.0
        return score

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by weighted score (ascending = most urgent first)."""
        return sorted(tasks, key=self._weighted_score)

    def find_next_available_slot(
        self,
        pet: Pet,
        duration_minutes: int,
        after_time: Optional[time] = None,
        plan_date: Optional[date] = None,
    ) -> Optional[datetime]:
        """
        Find the next free slot of at least `duration_minutes` for this pet.

        Generates today's schedule, then scans the gaps between scheduled
        tasks for a window that fits the requested duration.

        Returns the start datetime of the first fitting gap, or None if
        no slot is available within the owner's window.
        """
        plan_date = plan_date or date.today()
        schedule = self.generate_schedule(pet, plan_date=plan_date)

        candidate = datetime.combine(
            plan_date, after_time or pet.owner.available_start
        )
        day_end = datetime.combine(plan_date, pet.owner.available_end)
        busy = sorted(schedule.scheduled, key=lambda st: st.start_time)

        for st in busy:
            if candidate + timedelta(minutes=duration_minutes) <= st.start_time:
                return candidate          # gap before this task is big enough
            if st.end_time > candidate:
                candidate = st.end_time   # skip past the busy block

        # Check the gap after all scheduled tasks
        if candidate + timedelta(minutes=duration_minutes) <= day_end:
            return candidate

        return None

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
