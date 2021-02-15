from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
# defining a route
@app.route("/employee/<id>")
def employee_details(id):
    return render_template('index.html', name = id)

@app.route("/") # decorator
def hello():
    # returning string
    return render_template('index.html', name = 'erik')

# serving form web page
@app.route("/form")
def form():
    return render_template('form.html')

#@app.route("/", methods=['GET', 'POST', 'PUT']) # decorator
def home(): # route handler function
    # returning a response
    return "Hello World!"


# handling form data
@app.route('/form-handler', methods=['POST'])
def handle_data():
    # since we sent the data using POST, we'll use request.form
    print('Name: ', request.form['name'])
    # we can also request.values
    print('Gender: ', request.form['gender'])
    return "Request received successfully!"

app.run(debug = True)
