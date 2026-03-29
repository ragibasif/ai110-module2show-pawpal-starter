"""
PawPal+ Streamlit UI
====================
Connects the backend logic layer (pawpal_system.py) to an interactive UI.
Features: owner setup, pet registration, task management, smart scheduling,
          JSON persistence, and emoji/color-coded priority display.
"""

from datetime import date, time

import streamlit as st

from pawpal_system import Category, Owner, Pet, Priority, Scheduler, Task

# ---------------------------------------------------------------------------
# Constants — emoji maps for visual clarity
# ---------------------------------------------------------------------------

PRIORITY_EMOJI = {
    Priority.HIGH:   "🔴 High",
    Priority.MEDIUM: "🟡 Medium",
    Priority.LOW:    "🟢 Low",
}

CATEGORY_EMOJI = {
    Category.WALK:        "🦮 Walk",
    Category.FEEDING:     "🍽️ Feeding",
    Category.MEDICATION:  "💊 Medication",
    Category.GROOMING:    "✂️ Grooming",
    Category.ENRICHMENT:  "🎾 Enrichment",
    Category.APPOINTMENT: "🏥 Appointment",
    Category.OTHER:       "📋 Other",
}

DATA_FILE = "data.json"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — powered by Python classes.")

# ---------------------------------------------------------------------------
# Session state — load persisted owner on first run
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = Owner.load_from_json(DATA_FILE)   # None if no file yet

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()


def _save() -> None:
    """Persist current owner state to disk after any mutation."""
    if st.session_state.owner:
        st.session_state.owner.save_to_json(DATA_FILE)


# ---------------------------------------------------------------------------
# Step 1: Register / update owner
# ---------------------------------------------------------------------------

st.header("1. Owner Setup")

with st.form("owner_form"):
    existing: Owner | None = st.session_state.owner
    col1, col2, col3 = st.columns(3)
    with col1:
        owner_name = st.text_input("Your name", value=existing.name if existing else "Jordan")
    with col2:
        avail_start = st.time_input(
            "Available from",
            value=existing.available_start if existing else time(7, 0),
        )
    with col3:
        avail_end = st.time_input(
            "Available until",
            value=existing.available_end if existing else time(21, 0),
        )
    submitted_owner = st.form_submit_button("Save owner")

if submitted_owner:
    if st.session_state.owner is None:
        st.session_state.owner = Owner(
            name=owner_name,
            available_start=avail_start,
            available_end=avail_end,
        )
    else:
        o = st.session_state.owner
        o.name = owner_name
        o.available_start = avail_start
        o.available_end = avail_end
    _save()
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
        owner.add_pet(Pet(name=pet_name, species=species, age=int(age), owner=owner))
        _save()
        st.success(f"Added **{pet_name}** the {species}!")

if owner.pets:
    st.write(f"Registered pets: {', '.join(f'**{p.name}**' for p in owner.pets)}")
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
            priority_label = st.selectbox("Priority 🎯", list(PRIORITY_EMOJI.values()))
            priority_val = [k for k, v in PRIORITY_EMOJI.items() if v == priority_label][0].value
        with col5:
            category_label = st.selectbox("Category", list(CATEGORY_EMOJI.values()))
            category_val = [k for k, v in CATEGORY_EMOJI.items() if v == category_label][0].value

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
            target_pet.add_task(Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority_val,
                category=category_val,
                earliest_start=earliest,
                latest_start=latest,
                recurrence=None if recurrence == "(none)" else recurrence,
                notes=notes,
            ))
            _save()
            st.success(f"Added **{task_title}** to {selected_pet_name}.")
        except ValueError as e:
            st.error(f"Invalid task: {e}")

    # Show tasks per pet with emoji + mark-complete button
    for pet in owner.pets:
        if pet.tasks:
            done_count = len(pet.completed_tasks())
            with st.expander(f"{pet.name}'s tasks ({len(pet.tasks)} total, {done_count} done)"):
                for task in pet.tasks:
                    col_a, col_b, col_c = st.columns([3, 2, 1])
                    with col_a:
                        status = "✅" if task.completed else "⬜"
                        st.write(
                            f"{status} **{task.title}**  \n"
                            f"{CATEGORY_EMOJI[task.category]} · "
                            f"{PRIORITY_EMOJI[task.priority]} · "
                            f"{task.duration_minutes}min"
                        )
                    with col_b:
                        if task.notes:
                            st.caption(f"📝 {task.notes}")
                    with col_c:
                        if not task.completed:
                            if st.button("✓ Done", key=f"done_{pet.name}_{task.title}"):
                                pet.complete_task(task)
                                _save()
                                st.rerun()

# ---------------------------------------------------------------------------
# Step 4: Generate schedule
# ---------------------------------------------------------------------------

st.header("4. Today's Schedule")

plan_date = st.date_input("Schedule date", value=date.today())

if st.button("🗓️ Generate schedule", type="primary"):
    if not owner.pets:
        st.warning("Add at least one pet first.")
    else:
        scheduler: Scheduler = st.session_state.scheduler
        any_scheduled = False

        for pet in owner.pets:
            pending = pet.pending_tasks()
            if not pending:
                st.info(f"✅ {pet.name} has no pending tasks today.")
                continue

            schedule = scheduler.generate_schedule(pet=pet, plan_date=plan_date)
            any_scheduled = True

            st.subheader(f"🐾 {pet.name}'s plan — {plan_date}")

            if schedule.scheduled:
                rows = []
                for st_task in schedule.scheduled:
                    rows.append({
                        "Time": f"{st_task.start_time.strftime('%H:%M')}–{st_task.end_time.strftime('%H:%M')}",
                        "Task": st_task.task.title,
                        "Priority": PRIORITY_EMOJI[st_task.task.priority],
                        "Category": CATEGORY_EMOJI[st_task.task.category],
                        "Min": st_task.task.duration_minutes,
                        "Why": st_task.reason,
                    })
                st.table(rows)
            else:
                st.write("No tasks could be scheduled.")

            if schedule.skipped:
                with st.expander(f"⏭️ Skipped tasks ({len(schedule.skipped)})"):
                    for task, reason in schedule.skipped:
                        st.write(
                            f"✗ {PRIORITY_EMOJI[task.priority]} **{task.title}** — {reason}"
                        )

            conflicts = schedule.conflicts()
            if conflicts:
                for a, b in conflicts:
                    st.warning(
                        f"⚠️ Conflict: **{a.task.title}** "
                        f"({a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')}) "
                        f"overlaps **{b.task.title}** "
                        f"({b.start_time.strftime('%H:%M')}–{b.end_time.strftime('%H:%M')})"
                    )

            total_h = schedule.total_minutes_scheduled // 60
            total_m = schedule.total_minutes_scheduled % 60
            st.caption(f"⏱️ Total scheduled: {total_h}h {total_m}m")
            st.divider()

        # Next-available-slot finder
        if any_scheduled and len(owner.pets) > 0:
            st.subheader("🔍 Find Next Available Slot")
            col_p, col_d = st.columns(2)
            with col_p:
                slot_pet_name = st.selectbox(
                    "Pet", [p.name for p in owner.pets], key="slot_pet"
                )
            with col_d:
                slot_duration = st.number_input(
                    "Duration needed (min)", min_value=1, max_value=480, value=30, key="slot_dur"
                )
            if st.button("Find slot"):
                slot_pet = owner.get_pet(slot_pet_name)
                slot = scheduler.find_next_available_slot(
                    slot_pet, int(slot_duration), plan_date=plan_date
                )
                if slot:
                    end = slot.strftime("%H:%M")
                    from datetime import timedelta
                    end_dt = slot + timedelta(minutes=int(slot_duration))
                    st.success(
                        f"Next free {slot_duration}-min slot for **{slot_pet_name}**: "
                        f"**{slot.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}**"
                    )
                else:
                    st.warning(f"No free {slot_duration}-min slot found for {slot_pet_name} today.")
