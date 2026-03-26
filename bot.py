from telegram import *
from telegram.ext import *
import sqlite3
import random, string

BOT_TOKEN = "8738889310:AAH9gWxECP_BYH5ZZu9moWZCttsIdGMRmVk"
ADMIN_ID = 7343837323

REQUIRED_CHANNELS = ["@tarjiima_kinolar_kanali"]

conn = sqlite3.connect("movies.db", check_same_thread=False)
cursor = conn.cursor()

# STATES
ADD_MOVIE, REQUEST = range(2)

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# START
def start(update, context):
    user_id = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    for ch in REQUIRED_CHANNELS:
        member = context.bot.get_chat_member(ch, user_id)
        if member.status == "left":
            update.message.reply_text(f"Join {ch} first!")
            return

    keyboard = [
        [InlineKeyboardButton("🎬 Get Movie", callback_data="get_movie")],
        [InlineKeyboardButton("📺 Series", callback_data="series")],
        [InlineKeyboardButton("📩 Request Movie", callback_data="request")]
    ]

    update.message.reply_text("Welcome!", reply_markup=InlineKeyboardMarkup(keyboard))


# ADMIN PANEL
def admin_panel(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Movie", callback_data="add_movie")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ]

    update.message.reply_text("Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))


# ADD MOVIE
def add_movie_start(update, context):
    update.callback_query.message.reply_text("Send movie video:")
    return ADD_MOVIE


def save_movie(update, context):
    video = update.message.video
    file_id = video.file_id

    code = generate_code()

    cursor.execute("INSERT INTO movies(code, name, file_id) VALUES(?,?,?)",
                   (code, "Movie", file_id))
    conn.commit()

    update.message.reply_text(f"Saved! Code: {code}")
    return ConversationHandler.END


# GET MOVIE
def get_movie(update, context):
    update.callback_query.message.reply_text("Send movie code:")


def send_movie(update, context):
    code = update.message.text.strip().upper()

    cursor.execute("SELECT file_id FROM movies WHERE code=?", (code,))
    result = cursor.fetchone()

    if result:
        update.message.reply_video(result[0])
    else:
        update.message.reply_text("Movie not found.")


# REQUEST
def request_start(update, context):
    update.callback_query.message.reply_text("Write your request:")
    return REQUEST


def save_request(update, context):
    text = update.message.text
    user_id = update.effective_user.id

    cursor.execute("INSERT INTO requests(user_id, text) VALUES(?,?)", (user_id, text))
    conn.commit()

    context.bot.send_message(ADMIN_ID, f"New request:\n{text}")
    update.message.reply_text("Request sent!")

    return ConversationHandler.END


# STATS
def stats(update, context):
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    update.callback_query.message.reply_text(f"Users: {total}")


# BROADCAST
def broadcast(update, context):
    update.callback_query.message.reply_text("Send message:")
    context.user_data["broadcast"] = True


def send_broadcast(update, context):
    if context.user_data.get("broadcast"):
        text = update.message.text

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for u in users:
            try:
                context.bot.send_message(u[0], text)
            except:
                pass

        update.message.reply_text("Broadcast sent!")
        context.user_data["broadcast"] = False


# BUTTONS
def buttons(update, context):
    query = update.callback_query.data

    if query == "add_movie":
        return add_movie_start(update, context)
    elif query == "get_movie":
        return get_movie(update, context)
    elif query == "request":
        return request_start(update, context)
    elif query == "stats":
        return stats(update, context)
    elif query == "broadcast":
        return broadcast(update, context)


# MAIN
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin_panel))

    dp.add_handler(CallbackQueryHandler(buttons))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, send_movie))
    dp.add_handler(MessageHandler(Filters.text, send_broadcast))

    conv1 = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_movie_start, pattern="add_movie")],
        states={ADD_MOVIE: [MessageHandler(Filters.video, save_movie)]},
        fallbacks=[]
    )

    conv2 = ConversationHandler(
        entry_points=[CallbackQueryHandler(request_start, pattern="request")],
        states={REQUEST: [MessageHandler(Filters.text, save_request)]},
        fallbacks=[]
    )

    dp.add_handler(conv1)
    dp.add_handler(conv2)

    print("Bot running...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
