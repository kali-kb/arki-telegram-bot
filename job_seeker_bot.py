import os
from warnings import filterwarnings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, InlineQueryResultArticle, ReplyKeyboardMarkup, KeyboardButton, InputTextMessageContent, CallbackQuery, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, MessageHandler, ConversationHandler, filters
from telegram.warnings import PTBUserWarning
from dotenv import load_dotenv
import urllib.parse
import logging
import json



filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)



with open('saved_jobs.json', 'r') as f:
    jobs = json.load(f)

with open('mock-server/inlinequery_results.json', 'r') as f:
    search_results = json.load(f)

# Enable logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )

# logger = logging.getLogger(__name__)

load_dotenv()

token = os.getenv('JOBSEEKER_BOT_TOKEN')
app = ApplicationBuilder().token(token).build()

START_MESSAGE = '''
Hello, you can use this bot to search, save and apply to jobs pick options shown below
'''
FULL_NAME, CV, COVER_LETTER = range(3)


def parse_args(args_str: str):
    args = dict(urllib.parse.parse_qsl(args_str))
    return args


def saved_job_message_creator(job):
    message = (
        f"<i>Saved Job</i> \n\n"
        f"<b>Job Title</b>: {job['title']}\n"
        f"<b>Company</b>: {job['company']}\n"
        f"<b>Location</b>: {job['location']}\n"
        f"<b>Description</b>: {job['description']}"
    )

    return message

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    keyboards = [
        ["Search a job", "Saved jobs"],
        ["Invite", "Guides"]
    ]

    if context.args:
        parameter = context.args[0]
        job = parse_args(parameter)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"job with id {job['job_id']} is saved for user {update.effective_user.username}")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=START_MESSAGE,
        reply_markup=ReplyKeyboardMarkup(
            keyboards,
            resize_keyboard=True,
        )
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message.text
    valid_messages = ["Search a job", "Saved jobs", "Invite", "Guides"]

    # if msg not in valid_messages:
    #     await update.message.reply_text(text="I didn't get that")
    #     return

    if msg == "Search a job":
        search_options = [
            [InlineKeyboardButton(text="Simple Search(Inline)", switch_inline_query_current_chat="")],
            # [InlineKeyboardButton(text="Advanced Search", callback_data="0")]
        ]
        reply_message = "Choose a way of searching that is convenient to you\n\n<b>Simple Search</b>: <i>Uses inline query</i>\n\n<b>Advanced Search</b>: <i>Uses web app</i>"
        await update.message.reply_text(
            text=reply_message,
            reply_markup=InlineKeyboardMarkup(search_options),
            parse_mode="HTML"
        )

    if msg == "Saved jobs":
        if not any(job["tg_user_id"] == str(update.effective_chat.id) for job in jobs):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="You have no saved jobs"
            )
        else:
            for job in jobs:
                if job["tg_user_id"] == str(update.effective_chat.id):
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=saved_job_message_creator(job),
                        reply_markup=InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton(text="Apply", callback_data="apply_btn"),
                                InlineKeyboardButton(text="Unsave", callback_data="unsave_btn")                
                            ]
                        ]),
                        parse_mode="HTML"
                    )


    if msg == "Invite":
        text_to_copy = "t.me/arki_jobs"
        reply_message = f"Share this link with your friends \n\n 🔗 {text_to_copy}"
        await update.message.reply_text(text=reply_message, parse_mode="HTML")

    
    if msg == "Guides":
        await update.message.reply_text(text="Not yet implemented")


async def job_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query
    query_result = []
    for result in search_results:
        print(result)
        title = result["job_title"].lower()
        if query.lower() in title:
            result_article = InlineQueryResultArticle(
                id=result["job_id"],
                title=result["job_title"],
                thumbnail_url=result["company_image"],
                description=f"{result['company_name']}\n{result['location']}",
                input_message_content=InputTextMessageContent(
                    message_text=f"<b>Job Title</b>: {result['job_title']}\n<b>Company</b>: {result['company_name']}\n<b>Location</b>: {result['location']}",
                    parse_mode="HTML",
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        # [InlineKeyboardButton(text="Apply", url=result["apply_link"])]
                        [InlineKeyboardButton(text="Apply", callback_data="apply_inline_btn")]
                    ]
                )
            )
            query_result.append(result_article)
    await update.inline_query.answer(query_result)
    print(query)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    print("cd:", query.data)
    #this implementation makes the bot quit inline context and return to regular chat
    if query.data == "apply_inline_btn" or query.data == "apply_btn":
        await query.answer()
        print("Hello")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Let's continue the application process in our private chat. Please click the button below to start.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Start Application", callback_data="start_application")
            ]])
        )

    elif query.data == "start_application":
        await query.answer()
        print("executing")
        if "form_data" in context.user_data:
            del context.user_data["form_data"]
            print("exists")
            await context.bot.send_message(chat_id=query.from_user.id, text="What is your name? Send full, or use /cancel to cancel application process", reply_markup=ReplyKeyboardRemove())
        else:
            print("doesnt exist")
            await context.bot.send_message(chat_id=query.from_user.id, text="What is your name? Send full name, or use /cancel to cancel application process", reply_markup=ReplyKeyboardRemove())
        return FULL_NAME


    if query.data == "unsave_btn":
        yes_no_keyboard = [
            [
                InlineKeyboardButton(text="✅ Yes", callback_data="yes_btn"),
                InlineKeyboardButton(text="❌ No", callback_data="no_btn")
            ]
        ]
        await update.callback_query.edit_message_text(
            text="Are you sure you want to unsave this job?",
            reply_markup=InlineKeyboardMarkup(yes_no_keyboard)
        )
        context.user_data["previous_message"] = {"previous_text": update.callback_query.message.text, "previous_reply_markup": update.callback_query.message.reply_markup}

    if query.data == "yes_btn":
        await query.answer(text="Your saved jobs has been removed")
        await update.callback_query.delete_message()

    if query.data == "no_btn":
        await update.callback_query.edit_message_text(
            text=context.user_data["previous_message"]["previous_text"],
            reply_markup=context.user_data["previous_message"]["previous_reply_markup"] 
        )
        del context.user_data["previous_message"]

    if query.data == "save_form":
        #send POST request to backend
        # await update.callback_query.message.edit_text(text="form saved successfully")
        await update.callback_query.delete_message()
        await update.callback_query.message.reply_text(text="form saved successfully")
        del context.user_data["form_data"]
    if query.data == "cancel_form":
        await update.callback_query.delete_message()
        del context.user_data["form_data"]


#################--FORM--#####################


async def ask_cv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(context.user_data)
    context.user_data["form_data"] = {}
    context.user_data["form_data"].update({"full_name": update.message.text})
    await update.message.reply_text(text="Submit your CV, the document must be in .pdf format, or use /cancel to cancel application process", reply_markup=ReplyKeyboardRemove())
    return CV

async def ask_cover_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(context.user_data["form_data"])
    context.user_data["form_data"].update({"cv": update.message.document}) #do an s3 upload as well
    await update.message.reply_text(text="Submit your cover letter", reply_markup=ReplyKeyboardRemove())
    return COVER_LETTER

async def incorrect_format_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(text="Incorrect format the document should be: pdf")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Application process cancelled. You can start over anytime.")
    return ConversationHandler.END
async def form_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["form_data"].update({"cover_letter": update.message.text})
    print(context.user_data)
    buttons = [
        [InlineKeyboardButton("Save Form", callback_data="save_form")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_form")]
    ]
    form_data = (
        f"<b>Full Name</b>: {context.user_data['form_data']['full_name']}\n"
        f"<b>Cover Letter</b>: {context.user_data['form_data']['cover_letter']}"
    )
    doc = context.user_data['form_data']['cv']
    await update.message.reply_document(document=doc , caption=form_data, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    return ConversationHandler.END



#################--FORM--#####################
      

app.add_handler(CommandHandler("start", start))
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(callback_query_handler)],
    states={
        FULL_NAME: [MessageHandler(filters.TEXT, ask_cv)],
        CV: [
            MessageHandler(filters.Document.PDF, ask_cover_letter),
            # MessageHandler(filters.ALL, incorrect_format_handler)
        ],
        COVER_LETTER: [MessageHandler(filters.TEXT, form_done)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
app.add_handler(InlineQueryHandler(job_search_handler))
app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

app.add_handler(CallbackQueryHandler(callback_query_handler))
print("job seeker bot running...")

app.run_polling()
