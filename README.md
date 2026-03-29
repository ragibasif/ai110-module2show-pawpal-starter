# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

PawPal+ includes algorithmic logic beyond simple task lists:

- **Priority sorting** — tasks are sorted high → medium → low; within the same priority, `medication` category jumps to the front, then shorter tasks go first as a tiebreaker.
- **Time-window deferral** — tasks with an `earliest_start` are deferred (not dropped) until the right time window opens.
- **Conflict detection** — `DailySchedule.conflicts()` flags any overlapping ScheduledTasks, useful as a safety net for schedules assembled outside the Scheduler.
- **Recurring tasks** — completing a daily/weekday/weekly task via `Pet.complete_task()` automatically queues the next occurrence with a computed `due_date`.
- **Filtering** — `Pet.filter_tasks(priority=..., category=..., completed=...)` supports any combination of criteria.

## Testing PawPal+

```bash
python -m pytest          # run full suite
python -m pytest -v       # verbose output
```

Test coverage includes: task completion, input validation, priority sorting, medication tiebreaker, recurring next-occurrence dates, conflict detection, scheduler integration (conflict-free output, skipped tasks on tight windows).

Confidence level: ★★★★☆ — core scheduling behaviors are fully covered. Edge cases not yet tested: weekdays recurrence skipping weekends, tasks spanning midnight, an owner with zero available minutes.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
