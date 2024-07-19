from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, WebAppInfo
from telegram.constants import ChatAction
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
from os import getenv
from functools import wraps
import random
import json


data = None
applicants=None
with open('jobs.json', 'r') as f:
    data = json.load(f)

with open('applicants.json', 'r') as f:
    applicants = json.load(f)

load_dotenv()

token = getenv('EMPLOYER_BOT_TOKEN')
app = ApplicationBuilder().token(token).build()

employer_registered = False
# Suggested code may be subject to a license. Learn more: ~LicenseLog:1655545878.

# print(data)


def send_action(action):
    """Sends `action` while processing func command."""
    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return await func(update, context,  *args, **kwargs)
        return command_func
    
    return decorator

def applicant_message_builder(applicant):
    message = (
        f"<b>Applicant Name</b>: {applicant['applicant_name']}\n"
        f"<b>Location</b>: {applicant['location']}\n"
        f"<b>Profession</b>: {applicant['profession']}\n"
        f"<b>Experience</b>: {applicant['experience']}\n"
        f"<b>Cover Letter</b>: \n \t <i>{applicant['cover_letter']}</i>\n"
    )
    return message

def jobdetail_message_builder(job):
    # message = data[0]
    message = (
        f"<b>Company</b>: {job['company']}\n"
        f"<b>Job Type</b>: {job['job_type']}\n"
        f"<b>Job Sector</b>: {job['job_sector']}\n"
        f"<b>Job Title</b>: {job['job_title']}\n"
        f"<b>Salary</b>: {job['salary']}\n"
        f"<b>Description</b>: \n {job['description']}\n"
        f"--------------------"
        f"\n\n"
        f"@arki_jobs"
    )
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_keyboards = [["Post a Job","Posted Jobs"] , ["Guides","Give FeedBack"]]
    user = update.effective_user
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"What would you like to do today? {user.username}",
        reply_markup=ReplyKeyboardMarkup(reply_keyboards, resize_keyboard=True)
    )


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings_list = [[InlineKeyboardButton("Choose Language", callback_data="0")]]
    settings = InlineKeyboardMarkup(settings_list)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚙️settings",
        reply_markup=settings
    )

@send_action(ChatAction.TYPING)
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    # await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    if query.data == "delete_job_btn":
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    elif query.data == "list_applicants":
        job = query.message.text
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Applicants For Job\n-------------------\n{job}")
        for applicant in applicants:
            print(applicant["username"])
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=applicant_message_builder(applicant),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Contact", url=f"https://t.me/{applicant['username'][1:]}")]])
            )

async def reply_keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "Post a Job":
        # Handle post job request
        if employer_registered:
            miniapp_form_btn = [[InlineKeyboardButton("Open Job Post Form", callback_data="1")]]
            reply_markup = InlineKeyboardMarkup(miniapp_form_btn)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="submit your job details by clicking the button below:",
                reply_markup=reply_markup                
            )
        else:
            await update.message.reply_text(
                text="You have not registered yet, please register first",
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        text="Open Registration Form",
                        web_app=WebAppInfo(url="https://cea3-34-140-89-220.ngrok-free.app/#company-registration")
                    )
                )
            )
           
    elif update.message.text == "Posted Jobs":
   
        for job in data:
            # applicants_count = random.randint(1, 100)
            message = jobdetail_message_builder(job)
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(text="Delete Job", callback_data="delete_job_btn"),
                        InlineKeyboardButton(text=f"Applicants", callback_data="list_applicants")
                    ]
                ])
            )

    # elif update.message.text == "Guides":
    #     # Handle guides request
    elif update.message.text == "Give FeedBack":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="we will appreciate your feedback, it helps us improve the platform, tell us what you think about it and what needs to improve"
        )



    # else:
    #     await update.message.reply_text("Invalid command")


messsage_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), reply_keyboard_handler)

app.add_handler(messsage_handler)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("settings", settings))
app.add_handler(CallbackQueryHandler(callback_query_handler))
print("bot running...")

app.run_polling()
