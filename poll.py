#!/usr/bin/env python

import logging
import os
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PollAnswerHandler,
    PollHandler,
    PicklePersistence,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")



async def start_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /poll <day>")
        return
    day = " ".join(context.args)
    question = f"Ci sarai ad allenamento il {day}?"
    options = ["Sì", "No"]

    msg = await update.effective_chat.send_poll(
        question=question,
        options=options,
        is_anonymous=False,
    )
    await context.bot.pin_chat_message(
        chat_id=update.effective_chat.id,
        message_id=msg.message_id,
        disable_notification=False,
    )

    context.bot_data["polls"][msg.poll.id] = {
        "chat_id": update.effective_chat.id,
        "question": question,
        "options": options,
        "voted": set(),
    }

    context.job_queue.run_repeating(
        reminder_job,
        interval=5,  # 1 hours
        first=5,
        data=msg.poll.id,
        chat_id=update.effective_chat.id,
        name=f"reminder_{msg.poll.id}",
    )

async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    poll_id = ans.poll_id
    if poll_id in context.bot_data["polls"]:
        context.bot_data["polls"][poll_id]["voted"].add(ans.user.id)

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    poll_id = context.job.data
    if poll_id not in context.bot_data["polls"]:
        # stop the job if the poll is not found
        context.job.schedule_removal()
        return
    poll = context.bot_data["polls"][poll_id]
    chat_id = poll["chat_id"]
    
    # get the list of members in the chat
    chat_members = await context.bot.get_chat_administrators(chat_id=chat_id)
    member_ids = {member.user.id for member in chat_members if not member.user.is_bot}
    
    missing_members_ids = member_ids - poll["voted"]
    
    if not missing_members_ids:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Tutti hanno votato al sondaggio '{poll['question']}'!",
        )
        context.job.schedule_removal()
        return

    # ping the missing members
    missing_members_mentions = [f"[@{member.user.username}](tg://user?id={member.user.id})" for member in chat_members if member.user.id in missing_members_ids]
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Promemoria: {', '.join(missing_members_mentions)} non hanno ancora votato al sondaggio '{poll['question']}'",
        parse_mode="MarkdownV2",
    )

async def stop_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /stoppoll <poll_id>")
        return
    poll_id = context.args[0]
    if poll_id not in context.bot_data["polls"]:
        await update.message.reply_text(f"Sondaggio {poll_id} non trovato")
        return

    # remove the job from the queue
    jobs = context.job_queue.get_jobs_by_name(f"reminder_{poll_id}")
    for job in jobs:
        job.schedule_removal()

    # remove the poll from the state
    del context.bot_data["polls"][poll_id]

    await update.message.reply_text(f"Sondaggio {poll_id} fermato")

async def pong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

async def bot_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands."""
    commands = await context.bot.get_my_commands()
    await update.message.reply_text(
        "Comandi disponibili:\n"
        + "\n".join([f"/{c.command} - {c.description}" for c in commands])
    )

async def receive_poll_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """This function is called when a poll is updated, but it does nothing."""
    # We don't need to do anything here, since we are only interested in poll answers
    pass


async def post_init(application: Application):
    if "polls" not in application.bot_data:
        application.bot_data["polls"] = {}
    await application.bot.set_my_commands([
        BotCommand("poll", "Crea un sondaggio per un dato giorno"),
        BotCommand("stoppoll", "Ferma un sondaggio dato il suo id"),
        BotCommand("ping", "Controlla se il bot è online"),
        BotCommand("commands", "Mostra i comandi disponibili"),
    ])

def main():
    persistence = PicklePersistence(filepath="biscavolleybot.pickle")
    app = Application.builder().token(TOKEN).persistence(persistence).post_init(post_init).build()
    app.add_handler(CommandHandler("poll", start_poll))
    app.add_handler(CommandHandler("stoppoll", stop_poll))
    app.add_handler(CommandHandler("ping", pong))
    app.add_handler(CommandHandler("commands", bot_commands))
    app.add_handler(PollHandler(receive_poll_update))
    app.add_handler(PollAnswerHandler(poll_answer))
    app.run_polling()

if __name__ == "__main__":
    main()
