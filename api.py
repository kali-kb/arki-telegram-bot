from os import getenv
from dotenv import load_dotenv
import requests


load_dotenv()


backend_url = getenv('BACKEND_URL')


def get_user(telegram_id):
    query_string = f"?by_telegram=true&tg_id={telegram_id}"
    url = f"{backend_url}/users{query_string}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {"status":"success", "user": data}
    elif response.status_code == 404:
        return {"status":"error", "message": "user not found"}

# print(get_user(111111))
# http://172.21.180.76:3000/users/3/jobs/11
def get_job(job_id):
    response = requests.get(f"{backend_url}/jobs/{job_id}")
    if response.status_code == 200:
        data = response.json()
        return {"status":"success", "job_data": data}
    elif response.status_code == 404:
        return {"status":"error", "message": "job not found"}


def update_user(user_id, payload):
    response = requests.put(f"{backend_url}/users/{user_id}", json=payload)
    if response.status_code == 200:
        data = response.json()
        return {"status": "success", "updated_user": data}
    elif response.status_code == 404:
        return {"status": "error", "message": "user not found"}

# payload = {"full_name": "John Doe"}
# print(update_user(2, payload))


def create_user(payload):
    response = requests.post(f"{backend_url}/users", json=payload)
    if response.status_code == 201:
        data = response.json()
        return data

user_obj = {
  "telegram_user_id": "111001",
  "role": "job_seeker",
}

# print(create_user(user_obj))

def save_job(job_id, user_id):
    payload = {
        "job_id": job_id,
    }
    response = requests.post(f"{backend_url}/users/{user_id}/saved_jobs", json=payload)
    print(response.json())
    if response.status_code == 201:
        data = response.json()
        return {"status": "success", "saved_job": data}
    elif response.status_code == 422 and response.json()['error'] == "You have already saved this job":
        return {"status": "error", "message": "Job already saved"}



def list_saved_job(user_id):
    response = requests.get(f"{backend_url}/users/{user_id}/saved_jobs")
    if response.status_code == 200:
        data = response.json()
        return data

# print(list_saved_job(9))

def unsave_job(saved_job_id, user_id):
    response = requests.delete(f"{backend_url}/users/{user_id}/saved_jobs/{saved_job_id}")
    if response.status_code == 204:
        return {"status": "success"}
    else:
        return {"status": "error"}




def search_jobs(query):
    response = requests.get(f"{backend_url}/jobs?q={query}")
    if response.status_code == 200:
        data = response.json()
        return data
# print(search_jobs("dev"))

#http://172.25.130.73:3000/users/4/job_applications

def apply_to_job(payload):
    user_id = payload["user_id"]
    payload = {
        "job_id": payload["job_id"],
        "cv_document_url": payload["cv_document_url"],
        "cover_letter": payload["cover_letter"],
        "contact": payload["contact"]
    }
    response = requests.post(f"{backend_url}/users/{user_id}/job_applications", json=payload)
    if response.status_code == 201:
        return {"message": "success"}
    elif response.status_code == 422 and response.json()["error"] == "You have already applied for this job":
        return {"message": "already applied"}
    else:
        return {"message": "error"}

# print(apply_to_job(13, 7, "https://www.google.com", "I am a good candidate"))

# http://172.25.130.73:3000/users/4/job_applications
def my_job_applications(user_id):
    response = requests.get(f"{backend_url}/users/{user_id}/job_applications")
    if response.status_code == 200:
        data = response.json()
        return data

# print(my_job_applications(7))

# print(jobs_applied_to())



################ Employer Bot ##################

def create_job(user_id, payload):
    response = requests.post(f"{backend_url}/users/{user_id}/jobs", json=payload)
    if response.status_code == 201:
        data = response.json()
        return data


# payload = {
#   "telegram_user_id": "101010",
#   "role": "company",
#   "company": {
#     "company_name": "Some Company",
#     "city": "addis",
#     "industry": "none",
#     "tin_no": "0001001"
#   }
# }
# {
# job_payload = { 
#   "title": "Social Media Marketer",
#   "job_site": "On-Site",
#   "city": "Addis Ababa",
#   "description": "We are looking for a talented Digital Marketer to join our remote team.",
#   "experience_required": "Junior Level",
#   "education_level": "Bachelors Degree",
#   "employment_type": "Contract",
#   "vacancies": 2,
#   "deadline": "2024-12-31T23:59:59"
# }
# user_id = 1
# print(create_job(user_id, job_payload))



def list_jobs(user_id):
    response = requests.get(f"{backend_url}/users/{user_id}/jobs")
    if response.status_code == 200:
        data = response.json()
        return data


def delete_job(user_id, job_id):
    response = requests.delete(f"{backend_url}/users/{user_id}/jobs/{job_id}")
    if response.status_code == 204:
        return {"status": "success"}
    else:
        return {"status": "error"}


def list_applicants(user_id, job_id):
    response = requests.get(f"{backend_url}/users/{user_id}/jobs/{job_id}/job_applications")
    if response.status_code == 200:
        data = response.json()
        return data

#/users/6/jobs/15/job_applications/18
def remove_applicant(user_id, job_id, job_application_id):
    response = requests.delete(f"{backend_url}/users/{user_id}/jobs/{job_id}/job_applications/{job_application_id}")
    if response.status_code == 204:
        return {"status": "success"}
    else:
        return {"status": "error"}

