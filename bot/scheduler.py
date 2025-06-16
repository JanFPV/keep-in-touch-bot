import asyncio
import random
import logging
from datetime import datetime, timedelta
import os

from dotenv import load_dotenv
from telegram import Bot
import storage

load_dotenv()

JITTER_PERCENT = float(os.getenv("INTERVAL_JITTER_PERCENT", 0.2))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", 3600))

# Diccionario con el próximo evento por grupo
scheduled_tasks = {}

def days_to_seconds(days: float):
    return int(days * 86400)

def get_next_interval(avg_days: int) -> int:
    """Devuelve un intervalo aleatorio en segundos, según promedio y variación"""
    jitter_range = avg_days * JITTER_PERCENT
    random_days = random.uniform(avg_days - jitter_range, avg_days + jitter_range)
    return days_to_seconds(random_days)

async def schedule_next(bot: Bot, chat_id: int):
    if not storage.is_group_active(chat_id):
        logging.info(f"[{chat_id}] Group is paused. Skipping scheduling.")
        return

    participants = storage.get_included_participants(chat_id)
    if not participants:
        logging.info(f"[{chat_id}] No included participants. Skipping.")
        return

    avg_days = storage.get_avg_days(chat_id)
    delay = get_next_interval(avg_days)
    run_at = datetime.now() + timedelta(seconds=delay)
    logging.info(f"[{chat_id}] Next message scheduled at {run_at}")

    async def job():
        await asyncio.sleep(delay)

        # Select a random participant
        participant = random.choice(participants)
        username = participant["username"]
        message = f"Hey @{username}, tell us about your life ✨"

        try:
            await bot.send_message(chat_id=chat_id, text=message)
            logging.info(f"[{chat_id}] Sent message to @{username}")
        except Exception as e:
            logging.error(f"[{chat_id}] Failed to send message: {e}")

        # Schedule again
        await schedule_next(bot, chat_id)

    # Start the task and store reference
    scheduled_tasks[chat_id] = asyncio.create_task(job())

async def periodic_scheduler(application):
    bot = application.bot
    while True:
        active_groups = storage.get_active_groups()
        for group in active_groups:
            chat_id = group["chat_id"]
            if chat_id not in scheduled_tasks or scheduled_tasks[chat_id].done():
                await schedule_next(bot, chat_id)
        await asyncio.sleep(CHECK_INTERVAL)

def start_scheduler(application):
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_scheduler(application))
