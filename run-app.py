from app import app

if __name__ == '__main__':
    ''' 
        Running app in debug mode
        It will trace errors if produced and display them
        Each time a change is made in code, the changes will reflect instantaneously. 
    '''
    app.run(debug=True)