from flask import Flask, render_template, request
import eme

app = Flask(__name__)
# defining a route


@app.route("/", methods=['GET', 'POST', 'PUT'])  # decorator
def index():
    varlist = eme.get_session_vars()
    return render_template('index.html', varlist=varlist)


@app.route("/docs", methods=['GET', 'POST', 'PUT'])  # decorator
def docs():
    # returning string
    varlist = eme.get_session_vars()
    # {'name' : session.name, 'dbstatus' : session.dbstatus, 'account' : session.account}
    return render_template('docTagger.html', varlist=varlist)


# Connect Button Handler
# background process happening without any refreshing
@app.route('/connect/', methods=['GET', 'POST', 'PUT'])
def connect_handler(acct="NONE"):
    return eme.connect_btn()


# Scan document Button Handler
@app.route('/scandocs/', methods=['GET', 'POST', 'PUT'])
def scandoc_handler(acct="NONE"):
    return eme.gdrive_scanner()


# Scan email Button Handler
@app.route('/scanemail/', methods=['GET', 'POST', 'PUT'])
def scanemail_handler(acct="NONE"):
    return eme.gmail_scanner()


# doc list reader Handler
# background process happening without any refreshing
@app.route('/docreader/', methods=['GET', 'POST', 'PUT'])
def doc_read_handler():
    return eme.doc_reader(shared=False)


# doc list reader Handler for shared docs
# background process happening without any refreshing
@app.route('/sharedreader/', methods=['GET'])
def shared_read_handler():
    return eme.doc_reader(shared=True)


# Tag list reader for docs
# background process happening without any refreshing
@app.route('/tagreader/', methods=['GET'])
def tag_read_handler(docid='missing'):
    docid = request.args.get('docid', type=str)
    print(f"doc id: {docid}")
    return eme.tag_reader(docid)


# Doc Finder Interface
@app.route('/finder/', methods=['GET'])
def finder_handler():
    print(f"Finder handler")
    varlist = eme.get_session_vars()
    return render_template('docFinder.html', varlist=varlist)


# Doc Finder Interface
@app.route('/finder/view/', methods=['GET'])
def finder_view_handler():
    print(f"Finder view handler")
    varlist = eme.get_session_vars()
    viewtype = request.args.get('viewtype', type=str)
    result = eme.finder(viewtype)
    return result


# Minder Interface
@app.route('/minder/', methods=['GET'])
def minder_handler():
    print(f"Minder handler")
    eme.minder_init()
    varlist = eme.get_session_vars()
    return render_template('minder.html', varlist=varlist)


@app.route('/minder/go/obj', methods=['GET'])
def minder_go_obj_handler():
    print(f"Minder Go object handler")
    taglen = request.args.get('len', type=int)
    taglist = []
    for i in range(taglen):
        taglist.append(request.args.get('t'+str(i), type=str))
    result = eme.minder_go_obj(taglist)
    print(f"taglist: {taglist}")
    print(f"obj result: {result}")
    return result


@app.route('/minder/go/tags', methods=['GET'])
def minder_go_thought_handler():
    print(f"Minder Go tag handler")
    taglist = request.args.get('viewtype', type=str)
    result = eme.minder_go_tags()
    print(f"tag result: {result}")
    return result


def main():
    app.run(debug=True)


if __name__ == '__main__':
    main()
