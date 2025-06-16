import os
import logging
from dotenv import load_dotenv
from telegram import Update, ChatMember, ChatMemberUpdated
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ChatMemberHandler,
)

import storage
from scheduler import start_scheduler
from commands import (
    help_command,
    about_command,
    include_command,
    exclude_command,
    interval_command,
    pause_command,
    resume_command,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def on_startup(application):
    logging.info("Starting KeepInTouchBot...")
    storage.init_db()
    start_scheduler(application)

async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    chat_id = chat.id
    logging.info(f"Bot added to group {chat.title} ({chat_id})")

    # Register group
    default_avg = int(os.getenv("DEFAULT_AVG_DAYS", 30))
    storage.register_group(chat_id, default_avg)

    # Get current members and register
    admins = await context.bot.getChatAdministrators(chat_id)
    for admin in admins:
        user = admin.user
        storage.add_or_update_participant(
            chat_id=chat_id,
            user_id=user.id,
            username=user.username or user.first_name,
        )

    included = storage.get_included_participants(chat_id)
    usernames = [u["username"] for u in included]
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"👋 Hello! I'm KeepInTouchBot.\n\n"
            f"Currently keeping in touch with: {', '.join('@'+u for u in usernames)}\n"
            f"⏱ Average interval: {default_avg} days.\n"
            f"Use /help to see all available commands."
        )
    )

async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member_update: ChatMemberUpdated = update.chat_member
    chat = update.effective_chat

    if not chat or chat.type not in ["group", "supergroup"]:
        return

    new_status = chat_member_update.new_chat_member.status
    user = chat_member_update.new_chat_member.user

    # Solo interesan los usuarios que entran o vuelven a estar activos
    if new_status in ["member", "administrator", "creator"]:
        storage.add_or_update_participant(chat.id, user.id, user.username or user.full_name, include=True)

    # Opcional: si quieres marcar usuarios que salieron como excluidos:
    elif new_status in ["left", "kicked"]:
        storage.set_participant_included(chat.id, user.id, False)

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

    # Command handlers
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("include", include_command))
    application.add_handler(CommandHandler("exclude", exclude_command))
    application.add_handler(CommandHandler("interval", interval_command))
    application.add_handler(CommandHandler("pause", pause_command))
    application.add_handler(CommandHandler("resume", resume_command))

    # Group entry handler
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))

    application.run_polling()

if __name__ == "__main__":
    main()
