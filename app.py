"""
PawPal+ Streamlit UI
====================
Connects the backend logic layer (pawpal_system.py) to an interactive UI.
"""

from datetime import date, time

import streamlit as st

from pawpal_system import Category, Owner, Pet, Priority, Scheduler, Task

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — powered by your own Python classes.")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
# Streamlit re-runs the entire script on every interaction.
# We guard object creation with "not in st.session_state" so the Owner
# and all its pets/tasks survive across button clicks.

if "owner" not in st.session_state:
    st.session_state.owner: Owner = None   # type: ignore[assignment]

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()

# ---------------------------------------------------------------------------
# Step 1: Register owner
# ---------------------------------------------------------------------------

st.header("1. Owner Setup")

with st.form("owner_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col2:
        avail_start = st.time_input("Available from", value=time(7, 0))
    with col3:
        avail_end = st.time_input("Available until", value=time(21, 0))
    submitted_owner = st.form_submit_button("Save owner")

if submitted_owner:
    st.session_state.owner = Owner(
        name=owner_name,
        available_start=avail_start,
        available_end=avail_end,
    )
    st.success(f"Owner **{owner_name}** saved ({avail_start.strftime('%H:%M')}–{avail_end.strftime('%H:%M')}).")

if st.session_state.owner is None:
    st.info("Fill in your name above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Step 2: Add a pet
# ---------------------------------------------------------------------------

st.header("2. Your Pets")

with st.form("pet_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
    with col3:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=3)
    submitted_pet = st.form_submit_button("Add pet")

if submitted_pet:
    if owner.get_pet(pet_name):
        st.warning(f"A pet named **{pet_name}** already exists.")
    else:
        new_pet = Pet(name=pet_name, species=species, age=age, owner=owner)
        owner.add_pet(new_pet)
        st.success(f"Added **{pet_name}** the {species}!")

if owner.pets:
    pet_names = [p.name for p in owner.pets]
    st.write(f"Registered pets: {', '.join(f'**{n}**' for n in pet_names)}")
else:
    st.info("No pets yet — add one above.")

# ---------------------------------------------------------------------------
# Step 3: Add tasks to a pet
# ---------------------------------------------------------------------------

st.header("3. Care Tasks")

if not owner.pets:
    st.info("Add a pet first before adding tasks.")
else:
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            selected_pet_name = st.selectbox("For which pet?", [p.name for p in owner.pets])
        with col2:
            task_title = st.text_input("Task title", value="Morning walk")

        col3, col4, col5 = st.columns(3)
        with col3:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with col4:
            priority = st.selectbox("Priority", ["high", "medium", "low"])
        with col5:
            category = st.selectbox(
                "Category",
                ["walk", "feeding", "medication", "grooming", "enrichment", "appointment", "other"],
            )

        col6, col7 = st.columns(2)
        with col6:
            use_window = st.checkbox("Set time window?")
        with col7:
            recurrence = st.selectbox("Recurrence", ["(none)", "daily", "weekdays", "weekly"])

        earliest = latest = None
        if use_window:
            wc1, wc2 = st.columns(2)
            with wc1:
                earliest = st.time_input("Earliest start", value=time(8, 0))
            with wc2:
                latest = st.time_input("Latest start", value=time(10, 0))

        notes = st.text_input("Notes (optional)", value="")
        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        target_pet = owner.get_pet(selected_pet_name)
        try:
            new_task = Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                category=category,
                earliest_start=earliest,
                latest_start=latest,
                recurrence=None if recurrence == "(none)" else recurrence,
                notes=notes,
            )
            target_pet.add_task(new_task)
            st.success(f"Added **{task_title}** to {selected_pet_name}.")
        except ValueError as e:
            st.error(f"Invalid task: {e}")

    # Show current tasks per pet
    for pet in owner.pets:
        if pet.tasks:
            with st.expander(f"{pet.name}'s tasks ({len(pet.tasks)})"):
                for task in pet.tasks:
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        status = "✓" if task.completed else "○"
                        st.write(
                            f"{status} **{task.title}** — "
                            f"{task.duration_minutes}min, {task.priority.value}, {task.category.value}"
                        )
                    with col_b:
                        if not task.completed:
                            if st.button("Done", key=f"done_{pet.name}_{task.title}"):
                                task.mark_complete()
                                st.rerun()

# ---------------------------------------------------------------------------
# Step 4: Generate schedule
# ---------------------------------------------------------------------------

st.header("4. Today's Schedule")

plan_date = st.date_input("Schedule date", value=date.today())

if st.button("Generate schedule", type="primary"):
    if not owner.pets:
        st.warning("Add at least one pet first.")
    else:
        all_empty = all(not pet.pending_tasks() for pet in owner.pets)
        if all_empty:
            st.warning("All tasks are already completed! Reset or add new tasks.")
        else:
            for pet in owner.pets:
                pending = pet.pending_tasks()
                if not pending:
                    st.info(f"{pet.name} has no pending tasks.")
                    continue

                try:
                    schedule = st.session_state.scheduler.generate_schedule(
                        pet=pet, plan_date=plan_date
                    )
                except NotImplementedError:
                    st.error(
                        "**`_sort_tasks()` is not implemented yet.** "
                        "Open `pawpal_system.py` and fill in the TODO in `Scheduler._sort_tasks()`."
                    )
                    st.stop()

                st.subheader(f"🐾 {pet.name}'s plan — {plan_date}")

                if not schedule.scheduled:
                    st.write("No tasks could be scheduled.")
                else:
                    for st_task in schedule.scheduled:
                        st.markdown(
                            f"**{st_task.start_time.strftime('%H:%M')}–"
                            f"{st_task.end_time.strftime('%H:%M')}** "
                            f"[{st_task.task.priority.value.upper()}] "
                            f"{st_task.task.title}  \n"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;↳ *{st_task.reason}*"
                        )

                if schedule.skipped:
                    with st.expander(f"Skipped tasks ({len(schedule.skipped)})"):
                        for task, reason in schedule.skipped:
                            st.write(f"✗ **{task.title}** — {reason}")

                conflicts = schedule.conflicts()
                if conflicts:
                    st.warning(f"⚠ {len(conflicts)} conflict(s) detected:")
                    for a, b in conflicts:
                        st.write(f"  {a.task.title} overlaps {b.task.title}")

                total_h = schedule.total_minutes_scheduled // 60
                total_m = schedule.total_minutes_scheduled % 60
                st.caption(f"Total scheduled: {total_h}h {total_m}m")
                st.divider()
