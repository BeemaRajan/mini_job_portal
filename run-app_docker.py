from app import app

if __name__ == '__main__':
    ''' 
        Running app in debug mode
        It will trace errors if produced and display them
        Each time a change is made in code, the changes will reflect instantaneously. 
    '''
    # To access the app from our host machine, we bind 0.0.0.0 to the host of the server.
    # otherwise, localhost:5000 is only accessible from within the Docker container
    app.run(debug=True, host='0.0.0.0')