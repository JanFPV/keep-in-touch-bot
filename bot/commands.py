from telegram import Update
from telegram.ext import ContextTypes
import storage

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🤖 *KeepInTouchBot* — Commands:

/about — What is this bot?
/interval <days> — Set average number of days between messages
/pause — Pause the bot
/resume — Resume the bot
/include <@username> — Include user in message rotation
/exclude <@username> — Exclude user from message rotation
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
    await update.message.reply_text(f"⏱ Average interval set to {days} days.")

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    storage.set_group_active(chat_id, False)
    await update.message.reply_text("Bot paused. I won’t ping anyone until resumed.")

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    storage.set_group_active(chat_id, True)
    await update.message.reply_text("Bot resumed. I’ll keep in touch again!")

async def include_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or not context.args[0].startswith("@"):
        await update.message.reply_text("Usage: /include @username")
        return

    username = context.args[0][1:]

    # Find by username (we only store username, so we don’t have user ID here)
    participants = storage.get_included_participants(chat_id) + storage.get_excluded_participants(chat_id)
    for p in participants:
        if p["username"].lower() == username.lower():
            storage.set_participant_included(chat_id, p["id"], True)
            await update.message.reply_text(f"✅ @{username} has been included.")
            return

    await update.message.reply_text(f"⚠️ User @{username} not found in group database.")

async def exclude_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or not context.args[0].startswith("@"):
        await update.message.reply_text("Usage: /exclude @username")
        return

    username = context.args[0][1:]

    participants = storage.get_included_participants(chat_id) + storage.get_excluded_participants(chat_id)
    for p in participants:
        if p["username"].lower() == username.lower():
            storage.set_participant_included(chat_id, p["id"], False)
            await update.message.reply_text(f"🚫 @{username} has been excluded.")
            return

    await update.message.reply_text(f"⚠️ User @{username} not found in group database.")
