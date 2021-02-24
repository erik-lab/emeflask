from flask import Flask, render_template, request, jsonify, redirect
import eme

app = Flask(__name__)
# defining a route

@app.route("/", methods=['GET', 'POST', 'PUT']) # decorator
def index():
    # returning string
    varlist = eme.get_session_vars()
    # {'name' : session.name, 'dbstatus' : session.dbstatus, 'account' : session.account}
    return render_template('index.html', varlist=varlist)

# serving form web page
@app.route("/form")
def form():
    return render_template('form.html')

# START SAMPLE

# background process happening without any refreshing
@app.route('/connect/', methods=['GET', 'POST', 'PUT'])
def connect(acct="NONE"):
    return eme.connect_btn()

#  END SAMPLE


# handling form data
@app.route('/form-handler', methods=['POST'])
def handle_data():
    # since we sent the data using POST, we'll use request.form
    print('Name: ', request.form['name'])
    # we can also request.values
    print('Gender: ', request.form['gender'])
    return "Request received successfully!"

def main():
    app.run(debug = True)



if __name__ == '__main__':
    main()
