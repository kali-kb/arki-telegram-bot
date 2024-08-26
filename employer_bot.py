from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, WebAppInfo
from telegram.constants import ChatAction
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
import pprint
from os import getenv
from functools import wraps
from io import BytesIO
import aiohttp
import random
import json
import api


data = None
applicants=None
# with open('jobs.json', 'r') as f:
#     data = json.load(f)

# with open('applicants.json', 'r') as f:
#     applicants = json.load(f)

load_dotenv()

token = getenv('EMPLOYER_BOT_TOKEN')
app = ApplicationBuilder().token(token).build()

employer_registered = False
chosen_language = "English"
messages_per_page = 5
# Suggested code may be subject to a license. Learn more: ~LicenseLog:1655545878.

# print(data)


def send_action(action):
    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return await func(update, context,  *args, **kwargs)
        return command_func
    
    return decorator

def applicant_message_builder(applicant):
    message = (
        f"<b>Applicant Name</b>: {applicant['user']['full_name']}\n"
        # f"<b>Location</b>: {applicant['location']}\n"
        # f"<b>Profession</b>: {applicant['profession']}\n"
        # f"<b>Experience</b>: {applicant['experience']}\n"
        f"<b>Cover Letter</b>: \n \t <i>{applicant['cover_letter']}</i>\n"
    )
    return message

def jobdetail_message_builder(job):
    # message = data[0]
    message = (
        # f"<b>Company</b>: {job['user']['company']['company_name'] if job['user']['role'] == 'company'}\n"
        f"<b>Job Title</b>: {job['title']}\n"
        f"<b>Job Type</b>: {job['employment_type'].capitalize()} {job['job_site'].capitalize()}\n"
        f"<b>Vacancies</b>: {job['vacancies']}\n"
        f"<b>Job Location</b>: {job['city']}\n"
        # f"<b>Job Sector</b>: {job['job_sector']}\n"
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
    settings_list = [[InlineKeyboardButton("Choose Language", callback_data="handle_choose_language")]]
    settings = InlineKeyboardMarkup(settings_list)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚙️ Settings",
        reply_markup=settings
    )

@send_action(ChatAction.TYPING)
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.data.startswith("delete_job_btn"):
        job_id = query.data.split(":")[1]
        context.user_data["job_id"] = job_id
        confirmation_buttons = [
            [
                InlineKeyboardButton("Yes", callback_data="confirmed_delete_job_btn"),
                InlineKeyboardButton("No", callback_data="cancelled_delete_job_btn")
            ]
        ]
        await context.bot.edit_message_text(chat_id=query.message.chat_id,message_id=query.message.message_id, text="Are you sure you want to delete the job?", reply_markup=InlineKeyboardMarkup(confirmation_buttons))
        context.user_data["previous_message"] = {"previous_text": update.callback_query.message.text, "previous_reply_markup": update.callback_query.message.reply_markup}

        # await context.bot.send_message(chat_id=query.message.chat_id, text="Job Deleted Successfully")
        # await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    elif query.data == "confirmed_delete_job_btn":
        user_id = 1 
        job_id = context.user_data.get("job_id")
        response = api.delete_job(user_id, job_id)
        if response["status"] == "success":
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
            await query.answer(text="Job is deleted successfully")
            del context.user_data["job_id"]
        else:
            await query.answer(text="Something went wrong, please try again later")
    

    elif query.data == "cancelled_delete_job_btn":
        await context.bot.edit_message_text(chat_id=query.message.chat_id,message_id=query.message.message_id, text=context.user_data["previous_message"]["previous_text"], reply_markup=context.user_data["previous_message"]["previous_reply_markup"])
    
    elif query.data.startswith("list_applicants"):
        print("executed")
        job_id = query.data.split(":")[1]
        from_btn = query.data.split(":")[2]
        if from_btn == "initial_list_btn" and "ended_at" in context.user_data:
            del context.user_data["ended_at"]
            del context.user_data["applicants_list"]
        # job = query.message.text
        user_id = 1
        applicants = None
        seen = None
        if "ended_at" not in context.user_data:
            seen = 0
            job = api.get_job(job_id)
            job = job['job_data']
            applicants = api.list_applicants(user_id, job_id)
            context.user_data["applicants_list"] = applicants
            print(job)
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"Applicants For Job\n-------------------\n{jobdetail_message_builder(job)}", parse_mode="HTML")
            context.user_data["fetched_jobs"] = True
        else:
            seen = context.user_data['ended_at']
            applicants = context.user_data["applicants_list"]
        seen_per_session = 0
        for applicant in applicants[seen:]:
            pprint.pp(applicant)
            print("seen: ", seen)
            if seen_per_session < messages_per_page:
                async with aiohttp.ClientSession() as session:
                    async with session.get(applicant['cv_document_url']) as response:
                        if response.status == 200:
                            file_content = await response.read()
                            file_obj = BytesIO(file_content)
                            file_obj.name = f"{applicant['user']['full_name'].replace(' ', '_').lower()}_cv.pdf"
                            await context.bot.send_document(
                                chat_id=query.message.chat_id,
                                document=file_obj,
                                caption=applicant_message_builder(applicant),
                                parse_mode="HTML",
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("Remove", callback_data=f"remove_applicant:{job_id}:{applicant['job_application_id']}"), InlineKeyboardButton("Contact", url=f"{applicant['contact']}")]
                                    # [],
                                ])
                            )
                            seen_per_session += 1
                            seen += 1
                        else:
                            await context.bot.send_message(chat_id=query.message.chat_id, text="Failed to retrieve the document.")
            else:
                context.user_data["ended_at"] = seen
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"shown {seen} out of {len(applicants)} applicants",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Show More", callback_data=f"list_applicants:{job_id}:show_more_btn")],
                    ])
                )
                break

    elif query.data.startswith("remove_applicant"):
        user_id = 1
        job_id = query.data.split(":")[1]
        applicant_id = query.data.split(":")[2]
        response = api.remove_applicant(user_id, job_id, applicant_id)
        if response['status'] == 'success':
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
            await query.answer(text="Successfully Removed Applicant")
        else:
            await query.answer(text="Failed to remove applicant, try again")

        # await context.bot.send_message(chat_id=query.message.chat_id, text=f"Applicant {applicant['user']['full_name']} removed successfully")

    elif query.data == "cancel_language_selection":
        #this is temporary it must return back to the previous oprtions of the settings
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)



    elif query.data == "handle_choose_language":
        languages = ["English", "Amharic"]
        await query.answer()
        # languages_list = [[InlineKeyboardButton(f"{language} {'(currently selected)' if chosen_language == language else ''}", callback_data=f"set_language_{language}")] for language in languages]
        languages_list = [
            [InlineKeyboardButton("English", callback_data="0")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_language_selection")]
        ]
        await context.bot.edit_message_text(
            text="Choose a language:",
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=InlineKeyboardMarkup(languages_list)
        )

async def reply_keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "Post a Job":
        # Handle post job request
        if employer_registered:
            miniapp_form_btn = [
                [InlineKeyboardButton(text="Open Job Post Form", web_app=WebAppInfo(url="https://300d-34-34-139-5.ngrok-free.app/job-post-form"))]
            ]
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
                        web_app=WebAppInfo(url="https://300d-34-34-139-5.ngrok-free.app/sign-up")
                    )
                )
            )
           
    elif update.message.text == "Posted Jobs":
        # user_id = context.user_data.get("user_id")
        if "ended_at" in context.user_data:
            del context.user_data["ended_at"]


        user_id = 1
        jobs = api.list_jobs(user_id)
        print(jobs)
        if jobs:
            for job in jobs:
                message = jobdetail_message_builder(job)
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(text="Delete Job", callback_data=f"delete_job_btn:{job['job_id']}"),
                            InlineKeyboardButton(text=f"Applicants {job['job_applications_count']}", callback_data=f"list_applicants:{job['job_id']}:initial_list_btn")
                        ]
                    ])
                )
        else:
            await context.bot.send_message("Something went wrong")

    elif update.message.text == "Guides":
        # Handle guides request
        await update.message.reply_text(text="Not yet implemented")



    elif update.message.text == "Give FeedBack":
        context.user_data['waiting_for_feedback'] = True
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="we will appreciate your feedback, it helps us improve the platform, tell us what you think about it and what needs to improve"
        )

    elif 'waiting_for_feedback' in context.user_data:
        # Handle the feedback message
        feedback = update.message.text
        user_id = 1
        response = api.create_feedback({"user_id": user_id, "feedback_text": feedback})
        if response:
            print(f"Received feedback from {update.effective_user.username}: {feedback}")  # Store or process the feedback as needed
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Thank you for your feedback! We'll use it to make our platform even better."
            )
            del context.user_data['waiting_for_feedback']


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.effective_message.web_app_data.data
    await update.effective_message.reply_text(f"Received data: {data}")
    result = {"status": "success"}
    await context.bot.answer_web_app_query(
        web_app_query_id=update.effective_message.web_app_data.id,
        result=result,
    )


messsage_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), reply_keyboard_handler)
# app.add_handler(MessageHandler(filters.ALL, log_all_updates))
app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
app.add_handler(messsage_handler)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("settings", settings))
app.add_handler(CallbackQueryHandler(callback_query_handler))
print("bot running...")

app.run_polling()
