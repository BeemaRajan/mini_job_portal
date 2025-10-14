## Convert data into json arrays based on data model -- using job view
# Here's my thought process on converting the data into a json file:
# I will first create a master list on which to collect all the data.
# Then, I will aggregate information by creating nested dictionaries for every row.

# libraries
import pandas as pd
import json

# load data from files
companies = pd.read_csv('./data/companies.csv')
education = pd.read_csv('./data/education.csv')
industries = pd.read_csv('./data/industries.csv')
jobs_detail = pd.read_csv('./data/jobs_detail.csv')
jobs = pd.read_csv('./data/jobs.csv')
skills = pd.read_csv('./data/skills.csv')

# helper function to convert the comma-separated string fields into lists
def parse_list_field(value):
    if pd.isna(value) or value == '':
        return []
    return [item.strip() for item in str(value).split(',')]

# create master list
json_list = []

# iterate through each job
for index, job_row in jobs.iterrows():
    
    # start with core job information
    job_doc = {
        "job_id": int(job_row['id']),
        "title": job_row['title'],
        "description": job_row['description'],
        "years_of_experience": job_row['years_of_experience'],
        "responsibilities": parse_list_field(job_row['responsibilities'])
    }
    
    # embed company information
    company_id = job_row['company_id']
    company_row = companies[companies['id'] == company_id].iloc[0]
    
    job_doc["company"] = {
        "name": company_row['company_name'],
        "size": company_row['company_size'],
        "type": company_row['company_type'],
        "headquarters": company_row['company_headquarters'],
        "website": company_row['company_website'],
        "description": company_row['company_description']
    }
    
    # embed industry information
    industry_id = company_row['industry_id']
    industry_match = industries[industries['id'] == industry_id]

    if not industry_match.empty:
        industry_row = industry_match.iloc[0]
        job_doc["industry"] = {
            "name": industry_row['industry_name'],
            "skills": parse_list_field(industry_row['industry_skills']),
            "top_companies": parse_list_field(industry_row['top_companies']),
            "trends": parse_list_field(industry_row['trends'])
        }
    else:
        # If industry not found, use a default or None
        job_doc["industry"] = {
            "name": "Unknown"
        }
    
    # embed education requirements
    education_id = job_row['education_id']
    edu_row = education[education['id'] == education_id].iloc[0]
    
    job_doc["education_required"] = {
        "level": edu_row['level'],
        "field": edu_row['field']
    }
    
    # embed skills
    skill_ids_str = str(job_row['skills_requirement'])

    # remove brackets
    skill_ids_str = skill_ids_str.strip('[]')

    # Split and convert to integers
    skill_ids = [int(sid.strip()) for sid in skill_ids_str.split(',') if sid.strip()]

    # look up skill names
    skill_names = []
    for skill_id in skill_ids:
        skill_row = skills[skills['id'] == skill_id]
        if not skill_row.empty:
            skill_names.append(skill_row.iloc[0]['skill'])

    job_doc["skills_required"] = skill_names
        
    # embed job details
    detail_row = jobs_detail[jobs_detail['job_id'] == job_row['id']].iloc[0]
    
    job_doc["employment_type"] = detail_row['employment_type']
    job_doc["average_salary"] = int(detail_row['average_salary'])
    job_doc["benefits"] = parse_list_field(detail_row['benefits'])
    job_doc["remote"] = bool(detail_row['remote'])
    job_doc["location"] = detail_row.get('location', '')  # Add if exists
    job_doc["job_posting_url"] = detail_row['job_posting_url']
    job_doc["posting_date"] = detail_row['posting_date']
    job_doc["closing_date"] = detail_row['closing_date']
    
    # derive experience level
    years_exp = job_row['years_of_experience']
    
    # extract the starting number from the range
    try:
        start_year = int(years_exp.split('-')[0])
        
        # categorize based on starting year of experience
        if start_year <= 2:
            experience_level = "Entry Level"
        elif start_year >= 6:
            experience_level = "Senior Level"
        else:
            experience_level = "Mid Level"
    except:
        # fallback if parsing fails
        experience_level = "Mid Level"
    
    job_doc["experience_level"] = experience_level
    
    # add to list
    json_list.append(job_doc)

# save to json file
output_file = './data/converted_data.json'

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(json_list, f, indent=2, ensure_ascii=False)
