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
    - posting_date: date the job was posted (string)
    
    optional fields: description, industry, education_required, skills_required, etc.
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