import logging
import os

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from instagrapi import Client
from instagrapi.exceptions import (
    TwoFactorRequired,
    ChallengeRequired,
    BadCredentials,
    ReloginAttemptExceeded,
    PleaseWaitFewMinutes,
    ClientThrottledError,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.getLogger("instagrapi").setLevel(logging.DEBUG)

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

ASK_USERNAME, ASK_PASSWORD, ASK_2FA, ASK_CHALLENGE, ASK_SAVE_SESSION = range(5)
ASK_TITLE = 0
current_broadcast = None

cl_dict = {}

class InstagramLive:
    def __init__(self, client: Client):
        self.client = client
        self.broadcast_id = None
        self.stream_server = None
        self.stream_key = None

    def create_broadcast(self, title="Instagram Live"):
        data = {
            "_uuid": self.client.uuid,
            "_uid": self.client.user_id,
            "preview_height": 1920,
            "preview_width": 1080,
            "broadcast_message": title,
            "broadcast_type": "RTMP",
            "internal_only": 0,
            "_csrftoken": self.client.token,
        }
        try:
            response = self.client.private_request("live/create/", data=data)
            self.broadcast_id = response["broadcast_id"]
            upload_url = response["upload_url"].split(str(self.broadcast_id))
            if len(upload_url) >= 2:
                self.stream_server = upload_url[0]
                self.stream_key = f"{self.broadcast_id}{upload_url[1]}"
                return {"stream_server": self.stream_server, "stream_key": self.stream_key}
        except Exception as e:
            logging.error(f"Error during live creation: {e}")
            return None

    def start_broadcast(self):
        data = {
            "_uuid": self.client.uuid,
            "_uid": self.client.user_id,
            "should_send_notifications": 1,
            "_csrftoken": self.client.token,
        }
        try:
            self.client.private_request(f"live/{self.broadcast_id}/start/", data=data)
            return True
        except Exception as e:
            logging.error(f"Error starting the live: {e}")
            return False

    def end_broadcast(self):
        data = {
            "_uuid": self.client.uuid,
            "_uid": self.client.user_id,
            "_csrftoken": self.client.token,
        }
        try:
            self.client.private_request(f"live/{self.broadcast_id}/end_broadcast/", data=data)
            return True
        except Exception as e:
            logging.error(f"Error ending the live: {e}")
            return False

    def live_info(self):
        try:
            response = self.client.private_request(f"live/{self.broadcast_id}/info/")
            viewer_count = response.get('viewer_count', 'N/A')
            status = response.get('broadcast_status', 'N/A')
            return {
                "broadcast_id": self.broadcast_id,
                "stream_server": self.stream_server,
                "stream_key": self.stream_key,
                "viewer_count": viewer_count,
                "status": status,
            }
        except Exception as e:
            logging.error(f"Error retrieving live info: {e}")
            return None

    def get_comments(self):
        try:
            response = self.client.private_request(f"live/{self.broadcast_id}/get_comment/")
            if 'comments' in response:
                return [{"username": c["user"]["username"], "text": c["text"]} for c in response['comments']]
            return []
        except Exception as e:
            logging.error(f"Error retrieving comments: {e}")
            return None

    def get_viewer_list(self):
        try:
            response = self.client.private_request(f"live/{self.broadcast_id}/get_viewer_list/")
            users = []
            ids = []
            for user in response.get('users', []):
                users.append(user['username'])
                ids.append(user['pk'])
            logging.debug(f"Viewer list retrieved: {users}")
            return users, ids
        except Exception as e:
            logging.warning(f"Failed to retrieve viewer list: {e}")
            return [], []


def login_instagram(username, password=None, verification_code=None, session_file=None):
    cl = Client()

    if session_file and os.path.exists(session_file):
        try:
            cl.load_settings(session_file)
            if not cl.user_id:
                raise Exception("Saved session not valid.")
            else:
                cl.user_info_v1(cl.user_id)
                print("Session loaded successfully!")
                return cl
        except Exception as e:
            print("Error loading session:", e)
            os.remove(session_file)

    if not password:
        raise ValueError("No password provided.")

    try:
        success = cl.login(
            username=username,
            password=password,
            verification_code=verification_code or ""
        )
        if success:
            print("Login successful!")
            return cl
        else:
            print("Login failed with no specific error from instagrapi.")
            return None

    except TwoFactorRequired:
        raise TwoFactorRequired("two_factor_required")

    except ChallengeRequired:
        raise ChallengeRequired("challenge_required")

    except (BadCredentials, ReloginAttemptExceeded) as e:
        print(f"Bad credentials or too many relogin attempts: {e}")
        return None

    except (PleaseWaitFewMinutes, ClientThrottledError) as e:
        print(f"Instagram is throttling us: {e}")
        return None

    except Exception as e:
        print(f"Error logging in: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Login", "Start Live"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome! Please choose an option from the menu:",
        reply_markup=reply_markup
    )


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter your Instagram username:", reply_markup=ReplyKeyboardRemove())
    return ASK_USERNAME


async def ask_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    context.user_data["username"] = username
    session_file = f"{username}_session.json"

    if os.path.exists(session_file):
        await update.message.reply_text("Session found! Verifying...")
        try:
            cl = login_instagram(username, session_file=session_file)
            if cl and cl.user_id:
                cl_dict[update.effective_user.id] = cl
                await update.message.reply_text(
                    "You are already logged in with your saved session!",
                    reply_markup=ReplyKeyboardMarkup([["Start Live"]], resize_keyboard=True)
                )
                return ConversationHandler.END
        except Exception as e:
            await update.message.reply_text(f"Invalid or expired session. Error: {e}")

    await update.message.reply_text("Please enter your Instagram password:")
    return ASK_PASSWORD


async def ask_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    context.user_data["password"] = password
    username = context.user_data.get("username")
    session_file = f"{username}_session.json"

    await update.message.reply_text("Attempting login...")

    try:
        cl = login_instagram(username, password=password, session_file=session_file)
        if cl and cl.user_id:
            cl_dict[update.effective_user.id] = cl
            inline_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Yes, save session", callback_data="save_session"),
                    InlineKeyboardButton("No, do not save", callback_data="discard_session")
                ]
            ])
            await update.message.reply_text(
                "Login successful! Would you like to save the session for faster future logins?",
                reply_markup=inline_keyboard
            )
            return ASK_SAVE_SESSION
        else:
            await update.message.reply_text("Error during login, please try again.")
            return ConversationHandler.END

    except TwoFactorRequired:
        await update.message.reply_text("Instagram requires a 2FA code. Please enter it now:")
        return ASK_2FA

    except ChallengeRequired:
        await update.message.reply_text(
            "Instagram triggered a checkpoint challenge (approval required). "
            "You can open the IG app/website to approve it, or try an automatic approach."
        )
        inline_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Try Automatic Resolve", callback_data="auto_challenge"),
                InlineKeyboardButton("I'll Approve in IG App", callback_data="manual_challenge")
            ]
        ])
        await update.message.reply_text("Choose an option:", reply_markup=inline_keyboard)
        return ASK_CHALLENGE

    except Exception as e:
        await update.message.reply_text(f"Error during login: {e}")
        return ConversationHandler.END


async def ask_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    username = context.user_data.get("username")
    password = context.user_data.get("password")
    session_file = f"{username}_session.json"

    if data == "manual_challenge":
        await query.message.reply_text(
            "Okay, please open the Instagram app or website and confirm the login request manually. "
            "Then you can try /login again."
        )
        return ConversationHandler.END

    elif data == "auto_challenge":
        await query.message.reply_text("Attempting to resolve the challenge automatically... please wait.")
        try:
            cl = Client()
            if os.path.exists(session_file):
                cl.load_settings(session_file)

            cl.login(username, password=password)
            if cl.user_id:
                cl_dict[update.effective_user.id] = cl
                inline_keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Yes, save session", callback_data="save_session"),
                        InlineKeyboardButton("No, do not save", callback_data="discard_session")
                    ]
                ])
                await query.message.reply_text(
                    "Challenge resolved automatically, login successful! "
                    "Do you want to save the session?",
                    reply_markup=inline_keyboard
                )
                return ASK_SAVE_SESSION
            else:
                await query.message.reply_text(
                    "Automatic challenge resolution failed. "
                    "Try again later or approve in IG app."
                )
                return ConversationHandler.END
        except Exception as e:
            await query.message.reply_text(
                f"Error attempting auto-resolve: {e}. Try manually approving in the IG app."
            )
            return ConversationHandler.END


async def ask_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verification_code = update.message.text.strip()
    username = context.user_data.get("username")
    password = context.user_data.get("password")
    session_file = f"{username}_session.json"

    await update.message.reply_text("2FA verification in progress...")

    try:
        cl = login_instagram(
            username=username,
            password=password,
            verification_code=verification_code,
            session_file=session_file
        )
        if cl and cl.user_id:
            cl_dict[update.effective_user.id] = cl
            inline_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Yes, save session", callback_data="save_session"),
                    InlineKeyboardButton("No, do not save", callback_data="discard_session")
                ]
            ])
            await update.message.reply_text(
                "2FA login successful! Would you like to save the session for faster future logins?",
                reply_markup=inline_keyboard
            )
            return ASK_SAVE_SESSION
        else:
            await update.message.reply_text("Error entering 2FA code or another issue occurred.")
            return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"Error entering 2FA code: {e}")
        return ConversationHandler.END


async def ask_save_session_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    username = context.user_data.get("username")
    session_file = f"{username}_session.json"
    await query.answer()

    cl = cl_dict.get(update.effective_user.id)
    if data == "save_session":
        if cl:
            try:
                cl.dump_settings(session_file)
                await query.message.reply_text("Session saved successfully!")
            except Exception as e:
                await query.message.reply_text(f"Error while saving the session: {e}")
        else:
            await query.message.reply_text("Cannot save session (Client not found).")
    elif data == "discard_session":
        if os.path.exists(session_file):
            os.remove(session_file)
        await query.message.reply_text("Session not saved.")

    reply_markup = ReplyKeyboardMarkup([["Start Live"]], resize_keyboard=True)
    await query.message.reply_text(
        "Now you can start a live or use commands from the menu.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END


async def ask_live_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in cl_dict:
        await update.message.reply_text("You must first log in with /login")
        return ConversationHandler.END
    await update.message.reply_text(
        "Please enter the live title:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_TITLE


async def handle_live_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_broadcast
    if current_broadcast is not None:
        await update.message.reply_text("A live is already running.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    if user_id not in cl_dict:
        await update.message.reply_text("You must first log in with /login")
        return ConversationHandler.END

    cl = cl_dict[user_id]
    ig_live = InstagramLive(cl)
    title = update.message.text
    await update.message.reply_text("Creating live, please wait...")
    broadcast = ig_live.create_broadcast(title)

    if not broadcast:
        keyboard = [["Start Live"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Error creating the live. Please try again.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    started = ig_live.start_broadcast()
    if not started:
        keyboard = [["Start Live"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Error starting the live. Please try again.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    stream_url = broadcast["stream_server"]
    stream_key = broadcast["stream_key"]
    current_broadcast = ig_live.broadcast_id
    context.user_data["instagram_live"] = ig_live
    context.user_data["stream_url"] = stream_url
    context.user_data["stream_key"] = stream_key

    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Show Streaming URL", callback_data="url")],
        [InlineKeyboardButton("Show Streaming Key", callback_data="key")]
    ])
    await update.message.reply_text("Live successfully started! Use the buttons below:", reply_markup=inline_keyboard)

    keyboard = [["Stop Live", "Live Info"], ["Get Comments", "Get Viewer List"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Live commands:", reply_markup=reply_markup)
    return ConversationHandler.END


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "url":
        stream_url = context.user_data.get("stream_url", "URL not available.")
        await query.message.reply_text(f"{stream_url}")
    elif query.data == "key":
        stream_key = context.user_data.get("stream_key", "Key not available.")
        await query.message.reply_text(f"{stream_key}")


async def handle_live_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_broadcast
    if current_broadcast is None:
        await update.message.reply_text("No live is currently running.")
        return
    ig_live = context.user_data.get("instagram_live")
    info = ig_live.live_info()
    if info:
        msg = (
            f"📡 **Live Info:**\n"
            f"- Broadcast ID: {info['broadcast_id']}\n"
            f"- Server URL: {info['stream_server']}\n"
            f"- Stream Key: {info['stream_key']}\n"
            f"- Viewer Count: {info['viewer_count']}\n"
            f"- Status: {info['status']}"
        )
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("Error retrieving live information.")


async def handle_stop_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_broadcast
    if current_broadcast is None:
        await update.message.reply_text("No live is currently running.")
        return
    ig_live = context.user_data.get("instagram_live")
    await update.message.reply_text("Ending live...")
    success = ig_live.end_broadcast()
    if success:
        current_broadcast = None
        context.user_data.clear()
        keyboard = [["Login", "Start Live"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Live ended successfully.", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Error ending live.")


async def handle_get_comments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_broadcast
    if current_broadcast is None:
        await update.message.reply_text("No live is currently running.")
        return
    ig_live = context.user_data.get("instagram_live")
    comments = ig_live.get_comments()
    if comments:
        comment_messages = "\n".join(
            [f"💬 {comment['username']} > {comment['text']}" for comment in comments]
        )
        await update.message.reply_text(f"**Comments:**\n{comment_messages}")
    else:
        await update.message.reply_text("No comments.")


async def handle_get_viewer_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_broadcast
    if current_broadcast is None:
        await update.message.reply_text("No live is currently running.")
        return
    ig_live = context.user_data.get("instagram_live")
    viewers, ids = ig_live.get_viewer_list()
    if viewers:
        viewer_list = "\n".join([f"👤 {v}" for v in viewers])
        await update.message.reply_text(f"**Viewer List:**\n{viewer_list}")
    else:
        await update.message.reply_text("No one is watching the live.")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    login_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^(Login)$"), login_command)],
        states={
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_username)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_password)],
            ASK_2FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_2fa)],
            ASK_CHALLENGE: [
                CallbackQueryHandler(ask_challenge, pattern="^(auto_challenge|manual_challenge)$")
            ],
            ASK_SAVE_SESSION: [
                CallbackQueryHandler(ask_save_session_callback, pattern="^(save_session|discard_session)$")
            ],
        },
        fallbacks=[],
    )

    live_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^(Start Live)$"), ask_live_title)],
        states={
            ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_live_title)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_conv_handler)
    app.add_handler(live_conv_handler)

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(Stop Live)$"), handle_stop_live))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(Live Info)$"), handle_live_info))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(Get Comments)$"), handle_get_comments))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(Get Viewer List)$"), handle_get_viewer_list))

    app.add_handler(CallbackQueryHandler(handle_callback_query, pattern="^(url|key)$"))

    print("Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
