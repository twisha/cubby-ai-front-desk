"""~12 seed question-log entries, varied by mode. Includes three GAP
questions clustered on the same theme (summer camp) so the gaps panel shows a
grouped theme with count=3 and an 'Answer this' button -> the draft/approve
flywheel demo.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from backend.models.ask import AnswerMode, QuestionLog

_NOW = datetime(2026, 7, 11, 9, 0, 0)


def _ago(minutes: int) -> datetime:
    return _NOW - timedelta(minutes=minutes)


def seed_questions() -> list[QuestionLog]:
    return [
        # --- GROUNDED (the bread-and-butter) ---
        QuestionLog(id="q01", ts=_ago(5), text="Are you open on Veterans Day?",
                    mode=AnswerMode.GROUNDED, max_cosine=0.71, source_ids=["holidays-2026"],
                    answer="Yes — we're open on Veterans Day."),
        QuestionLog(id="q02", ts=_ago(22), text="What's the tuition for infants?",
                    mode=AnswerMode.GROUNDED, max_cosine=0.78, source_ids=["tuition"],
                    answer="Infant tuition (6 weeks–12 months) is $395 per week."),
        QuestionLog(id="q03", ts=_ago(40), text="I forgot to pack lunch, can you provide one?",
                    mode=AnswerMode.GROUNDED, max_cosine=0.66, source_ids=["lunch-policy"],
                    answer="Yes — we provide a backup lunch for a $6 charge and notify you in the app."),
        QuestionLog(id="q04", ts=_ago(70), text="What time do you open?",
                    mode=AnswerMode.GROUNDED, max_cosine=0.74, source_ids=["hours"],
                    answer="We open at 6:30am, Monday through Friday."),
        QuestionLog(id="q05", ts=_ago(95), text="How do I schedule a tour?",
                    mode=AnswerMode.GROUNDED, max_cosine=0.69, source_ids=["tours"],
                    answer="Tours are Tuesday and Thursday at 10:00am, or by appointment."),
        # --- Near-miss trap: handbook says OPEN on Columbus Day ---
        QuestionLog(id="q06", ts=_ago(110), text="Are you closed for Columbus Day?",
                    mode=AnswerMode.GROUNDED, max_cosine=0.63, source_ids=["holidays-2026"],
                    answer="No — we're open on Columbus Day."),
        # --- JUDGMENT (policy answerable, decision isn't) ---
        QuestionLog(id="q07", ts=_ago(130),
                    text="My kid had a fever last night — can she come in today?",
                    mode=AnswerMode.JUDGMENT, max_cosine=0.58, source_ids=["illness-policy"],
                    answer="Children must be fever-free (under 100.4°F) for 24 hours without "
                           "fever-reducing medication before returning. A staff member will confirm."),
        QuestionLog(id="q08", ts=_ago(155),
                    text="He felt warm this morning, is that okay for drop-off?",
                    mode=AnswerMode.JUDGMENT, max_cosine=0.55, source_ids=["illness-policy"],
                    answer="Our policy requires 24 hours fever-free without medication. Ms. Donnelly "
                           "will follow up."),
        # --- ESCALATED (sensitive; no AI answer) ---
        QuestionLog(id="q09", ts=_ago(180),
                    text="Please don't release Emma to her father.",
                    mode=AnswerMode.ESCALATED, max_cosine=0.34, source_ids=[],
                    answer=None),
        # --- GAP cluster: three summer-camp questions (theme count = 3) ---
        QuestionLog(id="q10", ts=_ago(200), text="Do you have summer camp dates?",
                    mode=AnswerMode.GAP, max_cosine=0.19, source_ids=[], answer=None),
        QuestionLog(id="q11", ts=_ago(215), text="Do you close for the summer?",
                    mode=AnswerMode.GAP, max_cosine=0.22, source_ids=[], answer=None),
        QuestionLog(id="q12", ts=_ago(240), text="Is there a summer program for preschoolers?",
                    mode=AnswerMode.GAP, max_cosine=0.17, source_ids=[], answer=None),
    ]
