import logging
import os
import random
from datetime import datetime, timedelta

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv

import storage

load_dotenv()

JITTER_PERCENT = float(os.getenv("INTERVAL_JITTER_PERCENT", 0.2))
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", 3600))
SCHEDULER_DB_PATH = os.getenv("SCHEDULER_DB_PATH", "data/scheduler.sqlite")


def _days_to_seconds(days: float) -> int:
    return int(days * 86400)


def _get_next_interval_seconds(avg_days: int) -> int:
    jitter_range = avg_days * JITTER_PERCENT
    random_days = random.uniform(avg_days - jitter_range, avg_days + jitter_range)
    return _days_to_seconds(random_days)


async def run_checkin(application, chat_id: int):
    if not storage.is_group_active(chat_id):
        logging.info(f"[{chat_id}] Group paused; skipping check-in.")
        return

    participant = storage.get_random_included_participant(chat_id)
    if not participant:
        logging.info(f"[{chat_id}] No included participants; skipping check-in.")
        return

    username = participant["username"]
    message = f"@{username} tell me about your life ✨"
    try:
        await application.bot.send_message(chat_id=chat_id, text=message)
        storage.update_last_ping(chat_id)
        logging.info(f"[{chat_id}] Sent check-in to @{username}")
    except Exception as exc:
        logging.error(f"[{chat_id}] Failed to send message: {exc}")


def schedule_next(scheduler: AsyncIOScheduler, application, chat_id: int):
    if not storage.is_group_active(chat_id):
        return

    if not storage.get_included_participants(chat_id):
        return

    avg_days = storage.get_avg_days(chat_id)
    delay_seconds = _get_next_interval_seconds(avg_days)
    run_at = datetime.now() + timedelta(seconds=delay_seconds)

    job_id = f"checkin:{chat_id}"
    scheduler.add_job(
        run_checkin,
        trigger=DateTrigger(run_date=run_at),
        args=[application, chat_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logging.info(f"[{chat_id}] Next check-in scheduled at {run_at.isoformat()}")


def start_scheduler(application):
    scheduler = AsyncIOScheduler(
        timezone="UTC",
        jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{SCHEDULER_DB_PATH}")},
    )
    scheduler.start()

    # Ensure all active groups have exactly one scheduled job.
    for group in storage.get_active_groups():
        schedule_next(scheduler, application, group["chat_id"])

    async def _rescheduler():
        for group in storage.get_active_groups():
            chat_id = group["chat_id"]
            job_id = f"checkin:{chat_id}"
            if scheduler.get_job(job_id) is None:
                schedule_next(scheduler, application, chat_id)

    # Periodic reconciliation to pick up newly registered groups.
    scheduler.add_job(
        _rescheduler,
        "interval",
        seconds=CHECK_INTERVAL_SECONDS,
        id="rescheduler",
        replace_existing=True,
    )

    application.bot_data["scheduler"] = scheduler
