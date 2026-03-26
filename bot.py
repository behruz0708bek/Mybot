from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)
import sqlite3
import random, string

BOT_TOKEN = "8738889310:AAH9gWxECP_BYH5ZZu9moWZCttsIdGMRmVk"
ADMIN_ID = 7343837323

REQUIRED_CHANNELS = ["@tarjiima_kinolar_kanali"]

conn = sqlite3.connect("movies.db", check_same_thread=False)
cursor = conn.cursor()

ADD_MOVIE, REQUEST = range(2)

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY)")
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    for ch in REQUIRED_CHANNELS:
        member = await context.bot.get_chat_member(ch, user_id)
        if member.status == "left":
            await update.message.reply_text(f"Join {ch} first!")
            return

    keyboard = [
        [InlineKeyboardButton("🎬 Get Movie", callback_data="get_movie")],
        [InlineKeyboardButton("📺 Series", callback_data="series")],
        [InlineKeyboardButton("📩 Request Movie", callback_data="request")]
    ]

    await update.message.reply_text("Welcome!", reply_markup=InlineKeyboardMarkup(keyboard))


# ADMIN PANEL
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Movie", callback_data="add_movie")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ]

    await update.message.reply_text("Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))


# ADD MOVIE
async def add_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Send movie video:")
    return ADD_MOVIE


async def save_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    file_id = video.file_id

    cursor.execute("""CREATE TABLE IF NOT EXISTS movies(
        code TEXT,
        name TEXT,
        file_id TEXT
    )""")

    code = generate_code()

    cursor.execute("INSERT INTO movies(code, name, file_id) VALUES(?,?,?)",
                   (code, "Movie", file_id))
    conn.commit()

    await update.message.reply_text(f"Saved! Code: {code}")
    return ConversationHandler.END


# GET MOVIE
async def get_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Send movie code:")


async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()

    cursor.execute("SELECT file_id FROM movies WHERE code=?", (code,))
    result = cursor.fetchone()

    if result:
        await update.message.reply_video(result[0])
    else:
        await update.message.reply_text("Movie not found.")


# REQUEST SYSTEM
async def request_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Write your request:")
    return REQUEST


async def save_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    cursor.execute("""CREATE TABLE IF NOT EXISTS requests(
        user_id INTEGER,
        text TEXT
    )""")

    cursor.execute("INSERT INTO requests(user_id, text) VALUES(?,?)", (user_id, text))
    conn.commit()

    await context.bot.send_message(ADMIN_ID, f"New request:\n{text}")
    await update.message.reply_text("Request sent!")

    return ConversationHandler.END


# STATS
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f"Users: {total}")


# BROADCAST
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Send message:")
    context.user_data["broadcast"] = True


async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("broadcast"):
        text = update.message.text

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for u in users:
            try:
                await context.bot.send_message(u[0], text)
            except:
                pass

        await update.message.reply_text("Broadcast sent!")
        context.user_data["broadcast"] = False


# SERIES
async def show_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Series not added yet.")


# BUTTONS
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query.data

    if query == "add_movie":
        return await add_movie_start(update, context)
    elif query == "get_movie":
        return await get_movie(update, context)
    elif query == "request":
        return await request_start(update, context)
    elif query == "series":
        return await show_series(update, context)
    elif query == "stats":
        return await stats(update, context)
    elif query == "broadcast":
        return await broadcast(update, context)


# MAIN
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(CallbackQueryHandler(buttons))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_movie))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast))

    conv1 = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_movie_start, pattern="add_movie")],
        states={ADD_MOVIE: [MessageHandler(filters.VIDEO, save_movie)]},
        fallbacks=[]
    )

    conv2 = ConversationHandler(
        entry_points=[CallbackQueryHandler(request_start, pattern="request")],
        states={REQUEST: [MessageHandler(filters.TEXT, save_request)]},
        fallbacks=[]
    )

    app.add_handler(conv1)
    app.add_handler(conv2)

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
