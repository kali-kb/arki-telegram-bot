import os
from warnings import filterwarnings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, InlineQueryResultArticle, ReplyKeyboardMarkup, KeyboardButton, InputTextMessageContent, CallbackQuery, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, MessageHandler, ConversationHandler, filters
from telegram.warnings import PTBUserWarning
from dotenv import load_dotenv
from datetime import datetime
import aiohttp
from io import BytesIO
import urllib.parse
import logging
import json
import api


filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)



# with open('saved_jobs.json', 'r') as f:
#     jobs = json.load(f)


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
Hello, you can use this bot to search, save, and apply to jobs. Pick options shown below.
'''

FULL_NAME, CV, COVER_LETTER = range(3)
experience_in_years = {"Junior Level": "0 - 2 Years", "Mid-Level": "2 - 5 Years", "Senior Level": "5+ Years"}


def show_readable_date(date_string):
    date_object = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    formatted_date = date_object.strftime("%B %d, %Y at %I:%M %p")
    return formatted_date


def parse_args(args_str):
    if isinstance(args_str, list):
        args_str = ' '.join(args_str)
    if args_str.startswith('[') and args_str.endswith(']'):
        args_str = args_str[1:-1]
    args = {}
    pairs = args_str.split('=')
    for i in range(0, len(pairs) - 1, 2):
        key = pairs[i].strip()
        value = pairs[i + 1].strip()
        args[key] = value
    return args

def job_detail_message(job):
    
    message = (
        f"<b><i>Selected Job</i></b>\n"
        f"-----------------------\n"
        f"<b>Job Title</b>: {job['title']}\n"
        f"<b>Company</b>: {job['user']['company']['company_name'] if job['user']['role'] == 'company' else 'Private Client'}\n"
        f"<b>Location</b>: {job['city']}\n"
        f"<b>Job Type</b>: {job['job_site'].capitalize()} {job['employment_type'].capitalize().replace('_', ' ')}\n"
        f"<b>Education Required</b> {job['education_level'].capitalize().replace('_', ' ')}\n"
        f"<b>Experience Required</b>: {job['experience_required']} ({experience_in_years[job['experience_required']]})\n"
    )

    if job['salary']:
        message += f"<b>Salary</b>: {job['salary']}\n"

    message += (        
        f"<b>Posted at</b>: {show_readable_date(job['created_at'])}\n" 
        f"<b>Description</b>: \n\t<i>{job['description']}</i>"
    )

    return message


def saved_job_message_creator(saved_job):
    # print(saved_job)
    # print(saved_job['job']['experience_required'])
    message = (
        f"<i>Saved Job</i> \n\n"
        f"-----------------------\n"
        f"<b>Job Title</b>: {saved_job['job']['title']}\n"
        f"<b>Job Type</b>: {saved_job['job']['employment_type'].capitalize().replace('_', ' ')}\n"
        f"<b>Education Required</b> {saved_job['job']['education_level'].capitalize().replace('_', ' ')}\n"
        f"<b>Experience Required</b>: {saved_job['job']['experience_required']} ({experience_in_years[saved_job['job']['experience_required']]})\n"
        # f"<b>Company</b>: {saved_job['job']['company']}\n"
        f"<b>Location</b>: {saved_job['job']['city']}\n"
        f"<b>Description</b>: {saved_job['job']['description']}"
    )

    return message

def authenticate(context, update):
    if "current_user" not in context.user_data:
        response = api.get_user(update.effective_user.id)
        if response["status"] == "error" and response["message"] == "user not found":
            payload = {"telegram_user_id": update.effective_user.id, "role": "job_seeker"}
            created_user_data = api.create_user(payload)
            if current_user_data:
                context.user_data["current_user"] = created_user_data
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Something went wrong")
                return
        else:
            user = response["user"]
            context.user_data["current_user"] = user



async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboards = [
        ["Search a job", "Saved jobs"],
        ["Invite", "Guides"]
    ]
    print(context.args)
    print(parse_args(context.args))
    if context.args and 'save_job' in parse_args(context.args):
        # print("user:", context.user_data)
        parameter = context.args[0]
        param = parse_args(parameter)
        job_id = param["job_id"]
        
        authenticate(context, update)

        user_id = context.user_data["current_user"]["user_id"]
        response = api.save_job(job_id, user_id)
        if response["status"] == "success":
            print(response)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"job saved successfully")
            # await context.bot.send_message(chat_id=update.effective_chat.id, text=f"job with id {param['job_id']} is saved for user {update.effective_user.username}")
        elif response["status"] == "error" and response["message"] == "Job already saved":
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"You have already saved the job")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"job not saved something went wrong")
    
    #this needs to be refactored
    elif context.args and 'apply_job' in parse_args(context.args):
        parameter = context.args[0]
        param = parse_args(parameter)
        job_id = param["job_id"]
        authenticate(context, update)

        user_id = context.user_data["current_user"]["user_id"]
        chosen_job = api.get_job(job_id)
        print(chosen_job)
        if chosen_job["status"] == "success":
            job = chosen_job["job_data"]
            message = job_detail_message(job)
            button = [
                [InlineKeyboardButton("Apply", callback_data=f"apply_btn:{job_id}")]
            ]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=InlineKeyboardMarkup(button), parse_mode="HTML")
        elif chosen_job["status"] == "error" and chosen_job["message"] == "job not found":
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Job not found")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Something went wrong")
       
    

    else:
        if context.user_data.get('current_user'):
            print("current user", context.user_data.get('current_user'))
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=START_MESSAGE,
                reply_markup=ReplyKeyboardMarkup(
                    keyboards,
                    resize_keyboard=True,
                )
            )
        else:
            print("telegram user id:", update.effective_user.id)
            data = api.get_user(update.effective_user.id)
            print("d: ", data)
            if data["status"] == "success":
                context.user_data['current_user'] = data["user"]
            elif data["status"] == "error" and data["message"] == "user not found":
                payload = {"telegram_user_id": update.effective_user.id, "role": "job_seeker"}
                data = api.create_user(payload)
                context.user_data["current_user"] = data
                print("current user: ", context.user_data.get('current_user'))
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
            [InlineKeyboardButton(text="Start Inline Search", switch_inline_query_current_chat="")],
            # [InlineKeyboardButton(text="Simple Search(Inline)", switch_inline_query_current_chat="")],
            # [InlineKeyboardButton(text="Advanced Search", callback_data="0")]
        ]
        reply_message = "You can search jobs by title in the inline query which appears when you click the button below"
        # reply_message = "Choose a way of searching that is convenient to you\n\n<b>Simple Search</b>: <i>Uses inline query</i>\n\n<b>Advanced Search</b>: <i>Uses web app</i>"
        await update.message.reply_text(
            text=reply_message,
            reply_markup=InlineKeyboardMarkup(search_options),
            parse_mode="HTML"
        )

    if msg == "Saved jobs":
        user_id = context.user_data["current_user"]["user_id"]
        saved_jobs = api.list_saved_job(user_id)
        if saved_jobs == []:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="You have no saved jobs"
            )
        else:
            for saved_job in saved_jobs:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=saved_job_message_creator(saved_job),
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(text="Apply", callback_data=f"apply_btn:{saved_job['job_id']}"),
                            InlineKeyboardButton(text="Unsave", callback_data=f"unsave_btn:{saved_job['saved_job_id']}")                
                        ]
                    ]),
                    parse_mode="HTML"
                )

    if msg == "Invite":
        text_to_copy = "t.me/arki_jobs"
        reply_message = f"🚀 Invite your friends to join our job-seeking community! 🤝\n\nShare the link below and unlock a world of career opportunities for your network:\n\n🔗 {text_to_copy}\n\nHelp your friends discover their dream jobs today! 💼✨"
        await update.message.reply_text(text=reply_message, parse_mode="HTML")

    
    if msg == "Guides":
        await update.message.reply_text(text="Our usage guides are coming soon! Stay tuned for exciting updates and valuable resources to enhance your job-seeking journey.")

async def job_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query
    query_result = []
    search_results = api.search_jobs(query)
    for job in search_results:
        print(job)
        job_poster = job['user']['company']['company_name'] if job['user']['role'] == 'company' else "Private Client" 
        logo_img = job['user']['company']['logo_img_url'] if job['user']['role'] == 'company' and job['user']['company']['logo_img_url'] else "https://res.cloudinary.com/djlxfcael/image/upload/v1723195790/20240806_164459_0000_u8lmrz.png"
        result_article = InlineQueryResultArticle(
            id=job["job_id"],
            title=job["title"],
            thumbnail_url=logo_img,
            description=f"{job_poster}\n{job['city']} {job['employment_type'].capitalize().replace('_', ' ')}",
            input_message_content=InputTextMessageContent(
                # message_text=f"<b>Job Title</b>: {job['title']}\n<b>Company</b>: {job_poster}\n<b>Location</b>: {job['city']}",
                message_text=job_detail_message(job),
                parse_mode="HTML",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    # [InlineKeyboardButton(text="Apply", url=result["apply_link"])]
                    [InlineKeyboardButton(text="Apply", callback_data=f"apply_inline_btn:{job['job_id']}")]
                ]
            )
        )
        query_result.append(result_article)
    await update.inline_query.answer(query_result)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    #this implementation makes the bot quit inline context and return to regular chat
    if query.data.startswith("apply_inline_btn") or query.data.startswith("apply_btn") :
        await query.answer()
        _, job_id = query.data.split(":")
        context.user_data["application_for_job"] = job_id
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"Let's continue your application in our private chat. Please click the button below to begin.\n\nTo complete your application, please provide:\n• Your full name\n• Your CV in PDF format\n• A cover letter highlighting your experience, skills, and suitability for the role\n\n➡️ Note: The employer may contact you via Telegram for further communication after you submit your application.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Start Application", callback_data="start_application")
            ]])
        )

    elif query.data == "start_application":
        await query.answer()
        print("executing")
        if "form_data" in context.user_data:
            del context.user_data["form_data"]
            await context.bot.send_message(chat_id=query.from_user.id, text="What is your Name? Send Full Name, or use /cancel to cancel application process", reply_markup=ReplyKeyboardRemove())
        else:
            await context.bot.send_message(chat_id=query.from_user.id, text="What is your Name? Send Full Name(which includes your First Name and Last Name), or use /cancel to cancel application process", reply_markup=ReplyKeyboardRemove())
        return FULL_NAME


    if query.data.startswith("unsave_btn"):
        _, saved_job_id = query.data.split(":")
        context.user_data["selected_for_unsave"] = saved_job_id
        yes_no_keyboard = [
            [
                InlineKeyboardButton(text="✅ Yes", callback_data=f"yes_btn"),
                InlineKeyboardButton(text="❌ No", callback_data="no_btn")
            ]
        ]
        await update.callback_query.edit_message_text(
            text="Are you sure you want to unsave this job?",
            reply_markup=InlineKeyboardMarkup(yes_no_keyboard)
        )
        context.user_data["previous_message"] = {"previous_text": update.callback_query.message.text, "previous_reply_markup": update.callback_query.message.reply_markup}

    if query.data.startswith("yes_btn"):
        saved_job_id = context.user_data["selected_for_unsave"]
        user_id = context.user_data["current_user"]["user_id"]
        response = api.unsave_job(saved_job_id, user_id)
        if response["status"] == "success":
            await query.answer(text="Your saved jobs has been removed")
            del context.user_data["selected_for_unsave"]
            await update.callback_query.delete_message()
        else:
            await query.answer(text="Your saved jobs has not been removed, try again")

    if query.data == "no_btn":
        await update.callback_query.edit_message_text(
            text=context.user_data["previous_message"]["previous_text"],
            reply_markup=context.user_data["previous_message"]["previous_reply_markup"] 
        )
        del context.user_data["previous_message"]

    if query.data == "save_form":
        # await update.callback_query.message.edit_text(text="form saved successfully")
        print("id: ", context.user_data["application_for_job"])
        job_application_data = {
            "job_id": context.user_data["application_for_job"],
            "user_id": context.user_data["current_user"]["user_id"],
            "cover_letter": context.user_data["form_data"]["cover_letter"],
            "cv_document_url": context.user_data["form_data"]["cv"],
            "contact": f"https://t.me/{update.callback_query.from_user.username}",
        }
        response = api.apply_to_job(job_application_data)
        if response["message"] == "success":
            await update.callback_query.delete_message()
            await update.callback_query.message.reply_text(text="Application submitted successfully")
            del context.user_data["form_data"]
        elif response["message"] == "already applied":
            await update.callback_query.answer(text="You have already applied for the job")
        else:
            await update.callback_query.answer(text="form not saved, try again")
            
    if query.data == "cancel_form":
        await update.callback_query.delete_message()
        del context.user_data["form_data"]


#################--FORM--#####################
async def ask_cv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # print(context.user_data)
    user = context.user_data["current_user"]
    if not user["full_name"]:
        response = api.update_user(user["user_id"], {"full_name": str(update.message.text)})
        if response["status"] == "success":
            context.user_data["current_user"]["full_name"] = update.message.text
    context.user_data["form_data"] = {}
    context.user_data["form_data"].update({"full_name": update.message.text})
    await update.message.reply_text(text="Submit your CV document, the document must be in .pdf format, or use /cancel to cancel application process", reply_markup=ReplyKeyboardRemove())
    return CV

async def ask_cover_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # print(context.user_data["form_data"])
    # print(update.message.document)
    file_id = update.message.document.file_id
    file = await context.bot.get_file(file_id)
    file_url = file.file_path
    # print(file_url)
    # context.user_data["form_data"].update({"cv": update.message.document}) #do an s3 upload as well
    context.user_data["form_data"].update({"cv": file_url}) #do an s3 upload as well
    await update.message.reply_text(text="Write your cover letter, it should be maximum 1000 character", reply_markup=ReplyKeyboardRemove())
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
        [InlineKeyboardButton("Submit Application", callback_data="save_form")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_form")]
    ]
    form_data = (
        f"<b>Full Name</b>: {context.user_data['form_data']['full_name']}\n"
        f"<b>Cover Letter</b>: \n\t{context.user_data['form_data']['cover_letter']}"
    )
    doc_url = context.user_data['form_data']['cv']
    async with aiohttp.ClientSession() as session:
        async with session.get(doc_url) as response:
            if response.status == 200:
                file_content = await response.read()
                file_obj = BytesIO(file_content)
                file_obj.name = f"{context.user_data['form_data']['full_name'].replace(' ', '_').lower()}_cv.pdf"  # Set a default name for the file
                await update.message.reply_document(
                    document=file_obj,
                    caption=form_data,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("Failed to retrieve the document.")
    # await update.message.reply_document(document=doc , caption=form_data, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
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
