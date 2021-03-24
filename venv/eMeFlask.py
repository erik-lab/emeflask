from flask import Flask, render_template, request, g, jsonify, redirect
import eme

app = Flask(__name__)
# defining a route

@app.route("/", methods=['GET', 'POST', 'PUT']) # decorator
def index():
    varlist = eme.get_session_vars()
    return render_template('index.html', varlist=varlist)


@app.route("/docs", methods=['GET', 'POST', 'PUT']) # decorator
def docs():
    # returning string
    varlist = eme.get_session_vars()
    # {'name' : session.name, 'dbstatus' : session.dbstatus, 'account' : session.account}
    return render_template('docTagger.html', varlist=varlist)

# serving form web page
# TODO Get rid of this endpoint
@app.route("/form")
def form():
    return render_template('form.html')


# Connect Button Handler
# background process happening without any refreshing
@app.route('/connect/', methods=['GET', 'POST', 'PUT'])
def connect_handler(acct="NONE"):
    return eme.connect_btn()


# doc list reader Handler
# background process happening without any refreshing
@app.route('/docreader/', methods=['GET', 'POST', 'PUT'])
def doc_read_handler():
    return eme.doc_reader(shared=False)

# doc list reader Handler for shared docs
# background process happening without any refreshing
@app.route('/sharedreader/', methods=['GET', 'POST', 'PUT'])
def shared_read_handler():
    return eme.doc_reader(shared=True)

# Tag list reader for docs
# background process happening without any refreshing
@app.route('/tagreader/', methods=['GET'])
def tag_read_handler(docid='missing'):
    docid = request.args.get('docid', type=str) # 'fubar',
    print(f"doc id: {docid}")
    return eme.tag_reader(docid)


# Play with EventBrite
@app.route('/event/', methods=['GET'])
def event_handler():
    print(f"Event handler")
    return eme.tag_reader(docid)




def main():
    app.run(debug = True)



if __name__ == '__main__':
    main()
