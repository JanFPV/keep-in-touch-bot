from telegram import Update
from telegram.ext import ContextTypes

from bot import storage

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🤖 *KeepInTouchBot* — Commands:

/about — What is this bot?
/interval <days> — Set average days between check-ins
/pause — Pause check-ins for this group
/resume — Resume check-ins for this group
/include — Include yourself in rotation
/exclude — Exclude yourself from rotation
/help — Show this message
""", parse_mode="Markdown")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
I'm KeepInTouchBot 🤖✨

I randomly pick one person in this group every few weeks and ask them how life is going, so we all stay in touch 🧡
""")

async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command can only be used in a group.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /interval <days>")
        return

    days = int(context.args[0])
    if not 5 <= days <= 365:
        await update.message.reply_text("Please choose a number between 5 and 365.")
        return

    storage.set_avg_days(update.effective_chat.id, days)
    scheduler = context.application.bot_data.get("scheduler")
    if scheduler:
        from bot.scheduler import schedule_next

        schedule_next(scheduler, context.application, update.effective_chat.id)
    await update.message.reply_text(f"⏱ Average interval set to {days} days.")

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    storage.set_group_active(chat_id, False)
    scheduler = context.application.bot_data.get("scheduler")
    if scheduler:
        scheduler.remove_job(f"checkin:{chat_id}")
    await update.message.reply_text("Bot paused. I won’t ping anyone until resumed.")

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    storage.set_group_active(chat_id, True)
    scheduler = context.application.bot_data.get("scheduler")
    if scheduler:
        from bot.scheduler import schedule_next

        schedule_next(scheduler, context.application, chat_id)
    await update.message.reply_text("Bot resumed. I’ll keep in touch again!")

async def include_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if not user:
        return

    display_name = user.username or user.full_name
    storage.add_or_update_participant(chat_id, user.id, display_name, include=True)
    scheduler = context.application.bot_data.get("scheduler")
    if scheduler:
        from bot.scheduler import schedule_next

        schedule_next(scheduler, context.application, chat_id)
    await update.message.reply_text(f"✅ @{display_name} is included.")

async def exclude_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if not user:
        return

    display_name = user.username or user.full_name
    storage.add_or_update_participant(chat_id, user.id, display_name, include=False)
    await update.message.reply_text(f"🚫 @{display_name} is excluded.")
