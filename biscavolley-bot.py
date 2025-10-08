#!/usr/bin/env python

import logging
import os
from dotenv import load_dotenv
from telegram import Update, BotCommand, Bot
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

async def manage_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:


async def can_i_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ("private"):
        return True
    chat_admins = await update.effective_chat.get_administrators()
    return update.effective_user in (admin.user for admin in chat_admins)

async def manage_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        people = context.bot_data.get("people", [])
        if not people:
            await update.message.reply_text("Nessuna persona configurata per il ping. Per aggiungere o rimuovere: /people [add|remove|clear] [@username]")
            return
        message = "Persone configurate per il ping: \n"
        for person in people:
            message += f"- @{person}\n"
        message += "Per aggiungere o rimuovere: /people add|remove @username"
        await update.message.reply_text(message)
        return

    subcommand = context.args[0]
    if subcommand == "add":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /people add @username")
            return
        
        username = context.args[1].lstrip("@")
        if username not in context.bot_data["people"]:
            context.bot_data["people"].append(username)
            await update.message.reply_text(f"Added @{username} to the ping list.")
        else:
            await update.message.reply_text(f"@{username} is already in the ping list.")

    elif subcommand == "remove":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /people remove @username")
            return
        username = context.args[1].lstrip("@")
        if username in context.bot_data["people"]:
            context.bot_data["people"] = [p for p in context.bot_data["people"] if p != username]
            await update.message.reply_text(f"Removed @{username} from the ping list.")
        else:
            await update.message.reply_text(f"@{username} is not in the ping list.")
    elif subcommand == "clear":
        context.bot_data["people"] = []
        await update.message.reply_text("Ping-list cleared")
    else:
        await update.message.reply_text("Usage: /people [add|remove|clear] [@username]")


async def manage_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        delay = context.bot_data.get("delay", 3600)
        await update.message.reply_text(f"Current delay is {delay} seconds.")
        return

    subcommand = context.args[0]
    if subcommand == "set":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /delay set <seconds>")
            return
        try:
            delay = int(context.args[1])
            context.bot_data["delay"] = delay
            await update.message.reply_text(f"Delay set to {delay} seconds.")
        except ValueError:
            await update.message.reply_text("Invalid delay value. Please provide an integer.")
    else:
        await update.message.reply_text("Usage: /delay [set] [value]")


async def start_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /poll <day>")
        return
    day = "".join(context.args)
    question = f"Ci sarai ad allenamento il {day}?"
    options = ["Sì", "No"]

    msg = await update.effective_chat.send_poll(
        question=question,
        options=options,
        is_anonymous=False,
    )

    if await can_i_pin(update, context):
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            disable_notification=False,
        )

    missing_ids = context.bot_data.get("people", [])

    context.bot_data["polls"][msg.poll.id] = {
        "chat_id": update.effective_chat.id,
        "question": question,
        "options": options,
        "missing": missing_ids,
    }

    context.job_queue.run_repeating(
        reminder_job,
        interval=context.bot_data.get("delay", 3600),
        first=context.bot_data.get("delay", 3600),
        data=msg.poll.id,
        chat_id=update.effective_chat.id,
        name=f"reminder_{msg.poll.id}",
    )

async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    poll_id = ans.poll_id

    print("Triggered!")
    print(ans.user.username)
    
    if poll_id in context.bot_data["polls"]:
        if ans.user.username in context.bot_data["polls"][poll_id]["missing"]:
            context.bot_data["polls"][poll_id]["missing"].remove(ans.user.username)

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    poll_id = context.job.data
    print(context.bot_data)
    if poll_id not in context.bot_data["polls"]:
        # stop the job if the poll is not found
        context.job.schedule_removal()
        return
    poll = context.bot_data["polls"][poll_id]
    chat_id = poll["chat_id"]
    
    missing_members = poll["missing"]
    
    if not missing_members:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Tutti hanno votato al sondaggio!\n\"{poll['question']}\"",
        )
        context.job.schedule_removal()
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"\[\!\] Queste persone non hanno ancora votato al sondaggio: \n\- @{', @'.join(missing_members)} \n\"{poll['question']}\"",
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
    if "people" not in application.bot_data:
        application.bot_data["people"] = []
    if "delay" not in application.bot_data:
        application.bot_data["delay"] = 3600
    await application.bot.set_my_commands([
        BotCommand("poll", "Crea un sondaggio per un dato giorno"),
        BotCommand("stoppoll", "Ferma un sondaggio dato il suo id"),
        BotCommand("people", "Gestisce la lista di persone da pingare"),
        BotCommand("delay", "Gestisce il delay per i reminder"),
        BotCommand("ping", "Controlla se il bot è online"),
        BotCommand("commands", "Mostra i comandi disponibili"),
    ])

def main():
    persistence = PicklePersistence(filepath="biscavolleybot.pickle")
    app = Application.builder().token(TOKEN).persistence(persistence).post_init(post_init).build()
    app.add_handler(CommandHandler("poll", start_poll))
    app.add_handler(CommandHandler("people", manage_people))
    app.add_handler(CommandHandler("delay", manage_delay))
    app.add_handler(CommandHandler("stoppoll", stop_poll))
    app.add_handler(CommandHandler("ping", pong))
    app.add_handler(CommandHandler("commands", bot_commands))
    app.add_handler(PollHandler(receive_poll_update))
    app.add_handler(PollAnswerHandler(poll_answer))
    app.run_polling()

if __name__ == "__main__":
    main()
