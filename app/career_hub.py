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
        'message': 'Hello world!!!!!!!'
    }
    resp = jsonify(message)
    # Returning the object
    return resp

# localhost:5000/api/v1/customers
@app.route("/api/v1/customers", methods=['GET'])
def fetch_customers():
    '''
       Function to fetch all customers matching a query
    '''
    try:
        # Call the function from utils to get the query params
        query_params = utils.parse_query_params(request.query_string)
            
        # Check if records were found in DB
        # {}
        # db.collection.countDocuments({})
        if collection.count_documents(query_params) > 0:
            # fetch customers by query parameters
            records_fetched = collection.find(query_params)

            # Prepare the response
            return dumps(records_fetched)
        else:
            return 'No records are found', 404

    except Exception as e:
        # Error while trying to fetch the resource
        # Add message for debugging purpose
        return e, 500

# localhost:5000/api/v1/get_customer_by_id/5ca4bbcea2dd94ee58162a6f
@app.route('/api/v1/get_customer_by_id/<document_id>', methods=['GET'])
def get_by_id(document_id):
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(document_id)
        
        # Query the document
        result = collection.find_one({"_id": obj_id})
        
        # If document not found
        if not result:
            return jsonify({"message": "Document not found"}), 404
        
        # Convert ObjectId to string for JSON serialization
        result['_id'] = str(result['_id'])
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/v1/customers", methods=['POST'])
def create_customers():
    '''
       Function to create new customer(s)
    '''
    try:
        # Create new users
        try:
            body = ast.literal_eval(json.dumps(request.get_json()))
        except:
            # Bad request as request body is not available
            # Add message for debugging purpose
            return "", 400

        record_created = collection.insert_many(body)

        if record_created:
            inserted_id = record_created.inserted_ids
            # Prepare the response
            if isinstance(inserted_id, list):
                # Return list of Id of the newly created item

                ids = []
                for _id in inserted_id:
                    ids.append(str(_id))

                return jsonify(ids), 201
            else:
                # Return Id of the newly created item
                return jsonify(str(inserted_id)), 201
    except Exception as e:
        # Error while trying to create customers
        # Add message for debugging purpose
        print(e)
        return 'Server error', 500


# `app.route()` can send arguments to the function: customers_id
# Note: arguments are string type by default, so convert your args as needed
@app.route("/api/v1/customers/<customer_username>", methods=['POST'])
def update_user(customer_username):
    '''
       Function to update the user.
    '''
    try:
        # Get the value which needs to be updated
        try:
            body = ast.literal_eval(json.dumps(request.get_json()))
            print(body)
        except Exception as e:
            # Bad request as the request body is not available
            # Add message for debugging purpose
            return '', 400

        # Updating the user
        records_updated = collection.update_one({'username': customer_username}, body)

        # Check if resource is updated
        if records_updated.modified_count > 0:
            # Prepare the response as resource is updated successfully
            return records_updated.raw_result, 200
        else:
            # Bad request as the resource is not available to update
            # Add message for debugging purpose
            return 'No modification was made to customer', 304
    except Exception as e:
        # Error while trying to update the resource
        # Add message for debugging purpose
        print(e)
        return 'Server error', 500


@app.route("/api/v1/customers/<customer_username>", methods=['DELETE'])
def remove_user(customer_username):
    """
       Function to remove the user.
       """
    try:
        # Delete the user
        delete_user = collection.delete_one({"username": customer_username})

        print(delete_user.raw_result)
        if delete_user.deleted_count > 0 :
            # Prepare the response
            return 'Customer removed', 204
        else:
            # Resource not found
            return 'Customer not found', 404
    except Exception as e:
        # Error while trying to delete the resource
        # Add message for debugging purpose
        print(e)
        return "", 500
    
@app.route('/customers_by_birthdate', methods=['GET'])
def get_customers_by_birthdate():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    active_status = request.args.get('active', type=bool)

    if not start_date or not end_date:
        return jsonify({"error": "Both start_date and end_date parameters are required"}), 400

    # Convert string dates to datetime objects
    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    customers = collection.find({
        "birthdate": {
            "$gte": start_date,
            "$lte": end_date
        },
        "active": active_status
    })

    # Convert ObjectId to string for each document
    results = []
    for document in customers:
        document["_id"] = str(document["_id"])
        results.append(document)

    return jsonify(list(results))

# localhost:5000/insert_customer
@app.route('/insert_customer', methods=['POST'])
def insert_customer():
    data = request.json

    # Ensure necessary fields are provided
    if not data or 'birthdate' not in data:
        return jsonify({"error": "birthdate field is required"}), 400

    try:
        # Convert birthdate string to datetime object
        birthdate = datetime.strptime(data['birthdate'], "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # Replace the birthdate string with the datetime object
    data['birthdate'] = birthdate

    # Insert into MongoDB
    inserted_id = collection.insert_one(data).inserted_id

    return jsonify({"message": "Insert successful", "inserted_id": str(inserted_id)}), 201

# Recipe
# step 1: create your endpoint name/path + method
# step 2: define your view function for the endpoint
# step 3: do some basic processing/clean up on your user request object
# step 4: do pymongo calls to interact with your mongodb 


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