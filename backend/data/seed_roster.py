"""8 fictional children spread across the four parent states and both age
bands, including one child crossing the 2-year boundary (cycle 6mo -> 12mo).

Dates are chosen relative to the demo 'today' (2026-07-11) so the scheduler
produces an interesting spread of tiers. No real personal data.
"""
from __future__ import annotations

from datetime import date

from backend.models.roster import Child


def seed_children() -> list[Child]:
    return [
        # OVERDUE — also the scan-demo child. Matches the CD-51 fixtures
        # (Chen, Maya). Report 3 weeks past due; scanning the valid form
        # (signed 2026-06-20) accepts and flips her to compliant.
        Child(
            id="chen-maya", name="Maya Chen", parent_name="Priya Chen",
            dob=date(2022, 9, 14),
            last_exam_date=date(2025, 6, 20), parent_state="overdue",
        ),
        # DUE_SOON_ACKNOWLEDGED — the paused-reminders badge. appt <= due.
        # Also the "bad scan" demo child: cd51_name_unclear_photo.jpg has an
        # illegible scribble in the name field (everything else on the form
        # is valid) -> needs_review, isolated to just the name issue.
        Child(
            id="okafor-aisha", name="Aisha Okafor", parent_name="Ngozi Okafor",
            dob=date(2021, 3, 2),
            last_exam_date=date(2025, 8, 12), parent_state="due_soon_acknowledged",
            acknowledged_appt_date=date(2026, 8, 12),
        ),
        # DUE_SOON_UNRESPONSIVE — standard tier (~30 days). Matches the
        # cd51_novak_liam_valid_photo.jpg fixture (signed 2026-06-18);
        # scanning it accepts and flips him to compliant.
        Child(
            id="novak-liam", name="Liam Novak", parent_name="Tomasz Novak",
            dob=date(2022, 1, 20),
            last_exam_date=date(2025, 8, 5), parent_state="due_soon_unresponsive",
        ),
        # DUE_SOON_UNRESPONSIVE — urgent tier (~14 days). Also the Parent-tab
        # ReminderCard demo child. Matches cd51_reyes_sofia_valid_photo.jpg
        # (signed 2026-06-25); scanning it accepts and flips her to compliant.
        Child(
            id="reyes-sofia", name="Sofia Reyes", parent_name="Camila Reyes",
            dob=date(2023, 2, 10),
            last_exam_date=date(2025, 7, 25), parent_state="due_soon_unresponsive",
        ),
        # COMPLIANT — AGE-2 BOUNDARY. Exam taken at ~1.7y (6mo cycle);
        # child is now >2, so the next cycle lengthens to 12mo. The dashboard
        # shows the transition.
        Child(
            id="kim-noah", name="Noah Kim", parent_name="Grace Kim",
            dob=date(2024, 6, 15),
            last_exam_date=date(2026, 3, 1), parent_state="compliant",
        ),
        # COMPLIANT — preschool, 12mo.
        Child(
            id="thompson-ava", name="Ava Thompson", parent_name="Daniel Thompson",
            dob=date(2020, 11, 5),
            last_exam_date=date(2026, 5, 10), parent_state="compliant",
        ),
        # COMPLIANT — preschool, 12mo.
        Child(
            id="patel-ethan", name="Ethan Patel", parent_name="Priyanka Patel",
            dob=date(2023, 8, 22),
            last_exam_date=date(2026, 6, 1), parent_state="compliant",
        ),
        # COMPLIANT — infant/young toddler, 6mo cycle.
        Child(
            id="rossi-mia", name="Mia Rossi", parent_name="Marco Rossi",
            dob=date(2025, 1, 30),
            last_exam_date=date(2026, 5, 15), parent_state="compliant",
        ),
    ]
