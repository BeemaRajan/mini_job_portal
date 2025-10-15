'''Module for serving API requests'''

from app import app
from bson.json_util import dumps, loads
from flask import request, jsonify
import json
import ast # helper library for parsing data from string
from importlib.machinery import SourceFileLoader
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

# 1. Connect to the client 
client = MongoClient(host="localhost", port=27017)

# Import the utils module
utils = SourceFileLoader('*', './app/utils.py').load_module()

# 2. Select the database
db = client.careerhub # db name: careerhub
# Select the collection
collection = db.jobs 

# route decorator that defines which routes should be navigated to this function
@app.route("/") # '/' for directing all default traffic to this function get_initial_response()
def get_initial_response():

    # Message to the user
    message = {
        'apiVersion': 'v1.0',
        'status': '200',
        'message': 'Welcome to the career hub!'
    }
    resp = jsonify(message)
    # Returning the object
    return resp

@app.route("/create/jobPost", methods=['POST'])
def create_job_post():
    '''
    Create a new job posting
    
    required fields:
    - title: job title (string)
    - company: company object with at least a name (object)
    - industry: industry object with at least a name (object)
    - posting_date: date the job was posted (string)
    
    optional fields: description, education_required, skills_required, etc.
    '''
    try:
        # get json data from request body
        body = request.get_json()
        
        # check if request body is provided
        if not body:
            return jsonify({
                "error": "Request body is required",
                "message": "Please provide job posting data in JSON format"
            }), 400
        
        # validate 'title' field
        if 'title' not in body or not body['title'] or body['title'].strip() == '':
            return jsonify({
                "error": "Validation failed",
                "message": "Field 'title' is required and cannot be empty"
            }), 400
        
        # validate 'company' field
        if 'company' not in body:
            return jsonify({
                "error": "Validation failed",
                "message": "Field 'company' is required"
            }), 400
        
        # if company is provided, ensure it has a 'name' field
        if isinstance(body['company'], dict):
            if 'name' not in body['company'] or not body['company']['name'] or body['company']['name'].strip() == '':
                return jsonify({
                    "error": "Validation failed",
                    "message": "Field 'company.name' is required and cannot be empty"
                }), 400
        else:
            return jsonify({
                "error": "Validation failed",
                "message": "Field 'company' must be an object with a 'name' field"
            }), 400
        
        # validate 'industry' field
        if 'industry' not in body:
            return jsonify({
                "error": "Validation failed",
                "message": "Field 'industry' is required"
            }), 400
        
        # if industry is provided, ensure it has a 'name' field
        if isinstance(body['industry'], dict):
            if 'name' not in body['industry'] or not body['industry']['name'] or body['industry']['name'].strip() == '':
                return jsonify({
                    "error": "Validation failed",
                    "message": "Field 'industry.name' is required and cannot be empty"
                }), 400
        else:
            return jsonify({
                "error": "Validation failed",
                "message": "Field 'industry' must be an object with a 'name' field"
            }), 400
        
        # validate 'posting_date' field
        if 'posting_date' not in body or not body['posting_date'] or str(body['posting_date']).strip() == '':
            return jsonify({
                "error": "Validation failed",
                "message": "Field 'posting_date' is required and cannot be empty"
            }), 400
        
        # insert into mongodb
        record_created = collection.insert_one(body)
        
        # success response
        if record_created.inserted_id:
            # get the inserted document to return the job_id if it exists
            inserted_doc = collection.find_one({"_id": record_created.inserted_id})
            
            response = {
                "message": "Job post created successfully",
                "inserted_id": str(record_created.inserted_id)
            }
            
            # if the document has a job_id field, include it
            if inserted_doc and 'job_id' in inserted_doc:
                response["job_id"] = inserted_doc['job_id']
            
            return jsonify(response), 201
        
    except Exception as e:
        # error while trying to create the job post
        print(f"Error creating job post: {e}")
        return jsonify({
            "error": "Server error",
            "message": "An error occurred while creating the job post"
        }), 500

# localhost:5000/view_jobs_by_id/1
@app.route('/view_jobs_by_id/<int:job_id>', methods=['GET'])
def view_jobs_by_id(job_id):
    '''
    Retrieve full details for a single job by its unique job_id
    '''
    try:
        # query the document by job_id field
        result = collection.find_one({"job_id": job_id})
        
        # if document not found
        if not result:
            return jsonify({
                "error": "Job not found",
                "message": f"No job found with job_id: {job_id}"
            }), 404
        
        # convert ObjectId to string for json serialization
        result['_id'] = str(result['_id'])
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({
            "error": "Bad request",
            "message": str(e)
        }), 400

# localhost:5000/jobs/industry/finance
@app.route('/jobs/industry/<industry_name>', methods=['GET'])
def get_jobs_by_industry(industry_name):
    '''
    Return jobs by industry name
    
    path parameter:
    - industry_name: name of the industry (case-insensitive)
    '''
    try:
        # query for industry.name since it is nested
        # using mongodb's collation feature for case-insensitive comparison
        jobs = collection.find({
            "industry.name": industry_name
        }).collation({'locale': 'en', 'strength': 2})
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No jobs found",
                "message": f"No jobs found for industry: {industry_name}"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "industry": industry_name,
            "count": len(jobs_list),
            "jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs_by_salary_range/salary?min_salary=80000&max_salary=120000
@app.route('/jobs_by_salary_range/salary', methods=['GET'])
def get_jobs_by_salary_range():
    '''
    Query jobs based on a salary range
    
    query parameters:
    - min_salary: minimum salary (integer)
    - max_salary: maximum salary (integer)
    '''
    try:
        # get query parameters from the url
        min_salary = request.args.get('min_salary')
        max_salary = request.args.get('max_salary')
        
        # validate that both parameters are provided
        if not min_salary or not max_salary:
            return jsonify({
                "error": "Bad request",
                "message": "Both min_salary and max_salary query parameters are required"
            }), 400
        
        # convert to integers
        try:
            min_salary = int(min_salary)
            max_salary = int(max_salary)
        except ValueError:
            return jsonify({
                "error": "Bad request",
                "message": "min_salary and max_salary must be valid integers"
            }), 400
        
        # validate that min is less than or equal to max
        if min_salary > max_salary:
            return jsonify({
                "error": "Bad request",
                "message": "min_salary cannot be greater than max_salary"
            }), 400
        
        # query jobs within the salary range using $gte and $lte
        jobs = collection.find({
            "average_salary": {
                "$gte": min_salary,
                "$lte": max_salary
            }
        })
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No jobs found",
                "message": f"No jobs found with salary between ${min_salary:,} and ${max_salary:,}"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "min_salary": min_salary,
            "max_salary": max_salary,
            "count": len(jobs_list),
            "jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/location/New York, USA
@app.route('/jobs/location/<path:location>', methods=['GET'])
def get_jobs_by_location(location):
    '''
    Return jobs available in a specific location
    
    path parameter:
    - location: job location (handles spaces and commas via URL encoding)
    '''
    try:
        # query jobs by location (case-insensitive using collation)
        # flask automatically decodes url-encoded characters
        jobs = collection.find({
            "company.headquarters": location
        }).collation({'locale': 'en', 'strength': 2})
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No jobs found",
                "message": f"No jobs found for location: {location}"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "location": location,
            "count": len(jobs_list),
            "jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/skill/Python
@app.route('/jobs/skill/<skill_name>', methods=['GET'])
def get_jobs_by_skill(skill_name):
    '''
    Return jobs that require a given skill
    
    path parameter:
    - skill_name: name of the required skill (case-insensitive)
    '''
    try:
        # query jobs where skills_required array contains the skill
        # collation makes it case-insensitive
        jobs = collection.find({
            "skills_required": skill_name
        }).collation({'locale': 'en', 'strength': 2})
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No jobs found",
                "message": f"No jobs found requiring skill: {skill_name}"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "skill": skill_name,
            "count": len(jobs_list),
            "jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/skills/Python&SQL&Excel
@app.route('/jobs/skills/<path:skill_names>', methods=['GET'])
def get_jobs_by_multiple_skills(skill_names):
    '''
    return jobs that require one or more given skills
    
    path parameter:
    - skill_names: one or more skill names separated by ampersand (&)
    '''
    try:
        # split skill names by ampersand delimiter
        skills_list = [skill.strip() for skill in skill_names.split('&')]
        
        # validate that at least one skill was provided
        if not skills_list or skills_list == ['']:
            return jsonify({
                "error": "Bad request",
                "message": "At least one skill must be provided"
            }), 400
        
        # build query using $and to ensure ALL skills are present
        # each condition checks if the skill exists in the array
        query = {
            "$and": [
                {"skills_required": skill} 
                for skill in skills_list
            ]
        }
        
        # query jobs where skills_required array contains all specified skills
        # collation makes the matching case-insensitive
        jobs = collection.find(query).collation({'locale': 'en', 'strength': 2})
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No jobs found",
                "message": f"No jobs found requiring all skills: {', '.join(skills_list)}"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "skills": skills_list,
            "count": len(jobs_list),
            "jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/company/Quantum Finance Group
@app.route('/jobs/company/<path:company_name>', methods=['GET'])
def get_jobs_by_company(company_name):
    '''
    Find jobs by employer (company) name
    
    path parameter:
    - company_name: name of the company (case-insensitive, exact match)
    '''
    try:
        # query jobs by company name (case-insensitive using collation)
        jobs = collection.find({
            "company.name": company_name
        }).collation({'locale': 'en', 'strength': 2})
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No jobs found",
                "message": f"No jobs found for company: {company_name}"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "company": company_name,
            "count": len(jobs_list),
            "jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/count/industry
@app.route('/jobs/count/industry', methods=['GET'])
def count_jobs_by_industry():
    '''
    Returns a count of jobs grouped by industry
    
    returns a list where each industry has an associated job count,
    sorted by count descending
    '''
    try:
        # use aggregation to group by industry and count
        pipeline = [
            {
                "$group": {
                    "_id": "$industry.name",  # group by industry name
                    "job_count": {"$sum": 1}  # count jobs in each group
                }
            },
            {
                "$sort": {"job_count": -1}  # sort by count descending (-1)
            },
            {
                "$project": {
                    "_id": 0,  # exclude the _id field
                    "industry": "$_id",  # rename _id to industry
                    "job_count": 1  # include job_count
                }
            }
        ]
        
        # execute the aggregation
        results = list(collection.aggregate(pipeline))
        
        # if no results
        if not results:
            return jsonify({
                "error": "No data found",
                "message": "No industries found in the database"
            }), 404
        
        return jsonify({
            "total_industries": len(results),
            "industries": results
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500


# localhost:5000/jobs/top/salary
@app.route('/jobs/top/salary', methods=['GET'])
def get_top_paying_jobs():
    '''
    Returns top 5 jobs by salary
    
    returns jobs sorted by average_salary in descending order
    uses job_id as a secondary sort for deterministic results when salaries ties
    '''
    try:
        # query all jobs, sort by salary descending, then by job_id for deterministic ties
        # limit to top 5 results
        jobs = collection.find().sort([
            ("average_salary", -1),  # primary sort: salary descending
            ("job_id", 1)             # secondary sort: job_id ascending (for ties)
        ]).limit(5)
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No data found",
                "message": "No jobs found in the database"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "count": len(jobs_list),
            "top_paying_jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500
    
# localhost:5000/jobs/companies
@app.route('/jobs/companies', methods=['GET'])
def get_all_companies():
    '''
    Returns a unique list of companies that currently have at least one open job
    '''
    try:
        # get distinct company names from all jobs
        companies = collection.distinct("company.name")
        
        # if no companies found
        if not companies:
            return jsonify({
                "error": "No data found",
                "message": "No companies found in the database"
            }), 404
        
        # sort companies alphabetically
        companies_sorted = sorted(companies)
        
        return jsonify({
            "count": len(companies_sorted),
            "companies": companies_sorted
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/degree/Masters
@app.route('/jobs/degree/<degree_name>', methods=['GET'])
def get_jobs_by_degree(degree_name):
    '''
    Find jobs that require a specific degree
    
    path parameter:
    - degree_name: required degree level (Diploma, Bachelors, Masters, PhD, Other)
    '''
    try:
        # query jobs by degree requirement (case-insensitive using collation)
        jobs = collection.find({
            "education_required.level": degree_name
        }).collation({'locale': 'en', 'strength': 2})
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No jobs found",
                "message": f"No jobs found requiring degree: {degree_name}"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "degree": degree_name,
            "count": len(jobs_list),
            "jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/experience?experience_level=Mid Level
@app.route('/jobs/experience', methods=['GET'])
def get_jobs_by_experience_level():
    '''
    Query jobs based on experience level
    
    query parameter:
    - experience_level: required experience level (e.g., "Entry Level", "Mid Level", "Senior Level")
    '''
    try:
        # get experience_level from query parameters
        experience_level = request.args.get('experience_level')
        
        # validate that experience_level parameter is provided
        if not experience_level:
            return jsonify({
                "error": "Bad request",
                "message": "experience_level query parameter is required"
            }), 400
        
        # query jobs by experience level (case-insensitive using collation)
        jobs = collection.find({
            "experience_level": experience_level
        }).collation({'locale': 'en', 'strength': 2})
        
        # convert cursor to list
        jobs_list = list(jobs)
        
        # if no jobs found
        if not jobs_list:
            return jsonify({
                "error": "No jobs found",
                "message": f"No jobs found for experience level: {experience_level}"
            }), 404
        
        # convert ObjectId to string for each job
        for job in jobs_list:
            job['_id'] = str(job['_id'])
        
        return jsonify({
            "experience_level": experience_level,
            "count": len(jobs_list),
            "jobs": jobs_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/update/1
@app.route('/jobs/update/<job_id>', methods=['POST'])
def update_job_posting(job_id):
    '''
    Partially update a job posting by its job_id
    
    path parameter:
    - job_id: unique job identifier (integer)
    
    request body: JSON object with fields to update
    '''
    try:
        # convert job_id to integer
        try:
            job_id_int = int(job_id)
        except ValueError:
            return jsonify({
                "error": "Bad request",
                "message": "job_id must be a valid integer"
            }), 400
        
        # get the update data from request body
        update_data = request.get_json()
        
        # check if request body is provided
        if not update_data:
            return jsonify({
                "error": "Bad request",
                "message": "Request body is required"
            }), 400
        
        # define allowed fields and their expected types
        allowed_fields = {
            "title": str,
            "description": str,
            "years_of_experience": str,
            "responsibilities": list,
            "company": dict,
            "industry": dict,
            "education_required": dict,
            "skills_required": list,
            "employment_type": str,
            "average_salary": int,
            "benefits": list,
            "remote": bool,
            "location": str,
            "job_posting_url": str,
            "posting_date": str,
            "closing_date": str,
            "experience_level": str
        }
        
        # remove job_id from update_data if present (cannot be changed)
        if "job_id" in update_data:
            update_data.pop("job_id")
        
        # also remove _id if present
        if "_id" in update_data:
            update_data.pop("_id")
        
        # validate that all fields are allowed
        unknown_fields = [field for field in update_data.keys() if field not in allowed_fields]
        if unknown_fields:
            return jsonify({
                "error": "Bad request",
                "message": f"Unknown fields: {', '.join(unknown_fields)}"
            }), 400
        
        # validate field types
        for field, value in update_data.items():
            expected_type = allowed_fields[field]
            if not isinstance(value, expected_type):
                return jsonify({
                    "error": "Bad request",
                    "message": f"Field '{field}' must be of type {expected_type.__name__}"
                }), 400
        
        # check if job exists
        existing_job = collection.find_one({"job_id": job_id_int})
        if not existing_job:
            return jsonify({
                "error": "Job not found",
                "message": f"No job found with job_id: {job_id}"
            }), 404
        
        # if no fields to update after validation
        if not update_data:
            return jsonify({
                "message": "No fields to update",
                "job_id": job_id_int
            }), 200
        
        # perform the update
        result = collection.update_one(
            {"job_id": job_id_int},
            {"$set": update_data}
        )
        
        # return success response
        return jsonify({
            "message": "Job post updated successfully",
            "job_id": job_id_int,
            "fields_updated": list(update_data.keys()),
            "modified_count": result.modified_count
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

# localhost:5000/jobs/delete/1
@app.route('/jobs/delete/<job_id>', methods=['DELETE'])
def delete_job_posting(job_id):
    '''
    Delete a job posting by its job_id
    
    path parameter:
    - job_id: unique job identifier (integer)
    '''
    try:
        # convert job_id to integer
        try:
            job_id_int = int(job_id)
        except ValueError:
            return jsonify({
                "error": "Bad request",
                "message": "job_id must be a valid integer"
            }), 400
        
        # check if job exists before attempting to delete
        existing_job = collection.find_one({"job_id": job_id_int})
        if not existing_job:
            return jsonify({
                "error": "Job not found",
                "message": f"No job found with job_id: {job_id}"
            }), 404
        
        # delete the job
        result = collection.delete_one({"job_id": job_id_int})
        
        # return success response
        return jsonify({
            "message": "Job post deleted successfully",
            "job_id": job_id_int,
            "deleted_count": result.deleted_count
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500

@app.errorhandler(404)
def page_not_found(e):
    '''Send message to the user if route is not defined.'''

    message = {
        "err":
            {
                "msg": "This route is currently not supported."
            }
    }

    resp = jsonify(message)
    # Sending 404 (not found) response
    resp.status_code = 404
    # Returning the object
    return resp