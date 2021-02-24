from __future__ import print_function
import pickle
import os.path
import io
import json
import re
from apiclient import discovery
from apiclient import errors
from apiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client import client
from oauth2client import file
from oauth2client import tools
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from operator import itemgetter, attrgetter
from monkeylearn import MonkeyLearn
from docx import Document
from neo4j import GraphDatabase
import os
import sys
from flask import jsonify

# GLOBALS for eme Module for now - specific to Google API access
# If modifying these scopes, delete the file drive.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.readonly',
          'https://www.googleapis.com/auth/documents.readonly']
DISCOVERY_DOC = 'https://docs.googleapis.com/$discovery/rest?version=v1'
DOCUMENT_ID = '1ht6PMhI5JIcaQLqgsMBQhwOIIlHYr455'   # used for debugging and testing


def get_credentials(account):
    """ TODO Get valid user credentials from database.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth 2.0 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    print("in Get Credentials")
    store = file.Storage('token.json')
    credentials = store.get()
    account += 1

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        credentials = tools.run_flow(flow, store)
    return credentials


def retrieve_all_files(service):
    """Retrieve a list of File resources.

    Args:
      service: Drive API service instance.
    Returns:
      List of File resources.

      TODO - accept a directory name and shared flag as input
      TODO - modify to use the session service values
    """
    result = []
    page_token = None
    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            param['corpora'] = 'user'
            # param['driveId'] = 'root'
            # param["shared"] = False      # get API error when using this or "trashed"
            param['includeItemsFromAllDrives'] = 'true'
            param['supportsAllDrives'] = 'true'
            param['orderBy'] = 'name'
            param['spaces'] = 'drive'
            param['fields'] = '*'
            param['q'] = "trashed = false" + \
                         " and mimeType != 'application/vnd.google-apps.folder'"
            # " and 'root' in parents"
            files = service.files().list(**param).execute()

            result.extend(files['files'])
            page_token = files.get('nextPageToken')
            if not page_token:
                break
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            break
    return result


def download_file(service, file_id, mimeType, filename):
    if "google-apps" in mimeType:
        return
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(filename, 'wb')  # io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        # print("Download %d%%." % int(status.progress() * 100))
        print(".", end='')
    return  # use with io.BytesIO  fh.getvalue()


def read_docx_text(docname):
    # TODO expand the logic in Docx reader to include tables, headers, and lists
    thetext = ""

    fileExtension = docname.split(".")[-1]
    if fileExtension == "docx":
        document = Document(docname)
        for para in document.paragraphs:
            thetext = thetext + para.text
    return thetext


def read_paragraph_element(element):
    """Returns the text in the given ParagraphElement.

        Args:
            element: a ParagraphElement from a Google Doc.
    """
    text_run = element.get('textRun')
    if not text_run:
        return ''
    return text_run.get('content')


def read_structural_elements(elements):
    """Recurses through a list of Structural Elements to read a document's text where text may be
        in nested elements.

        Args:
            elements: a list of Structural Elements.
    """
    text = ''
    for value in elements:
        if 'paragraph' in value:
            elements = value.get('paragraph').get('elements')
            for elem in elements:
                text += read_paragraph_element(elem)
        elif 'table' in value:
            # The text in table cells are in nested Structural Elements and tables may be
            # nested.
            table = value.get('table')
            for row in table.get('tableRows'):
                cells = row.get('tableCells')
                for cell in cells:
                    text += read_structural_elements(cell.get('content'))
        elif 'tableOfContents' in value:
            # The text in the TOC is also in a Structural Element.
            toc = value.get('tableOfContents')
            text += read_structural_elements(toc.get('content'))
    return text


def motivation():
    return 'getdocs'


class eme_session:
    def __init__(self, name='', account='', dbstatus='Not Connected', creds = None):
        self.name = name
        self.account = account
        self.dbstatus = dbstatus
        self.creds = creds

    def setname(self, name):
        self.name = name

    def setacct(self, account):
        self.account = account

    def setdb(self, dbstatus):
        self.dbstatus = dbstatus

    def setcreds(self, creds):
        self.creds = creds

class eme_object:
    def __init__(self, obj_source, obj_acct, obj_type, obj_id, obj_name, obj_mod):
        self.source = obj_source
        self.type = obj_type
        self.id = obj_id
        self.name = obj_name
        self.modified = obj_mod     # TODO read up on how to create indexes on date properties
        self.account = obj_acct
        self.source_tags = []
        self.content_tags = []
        self.user_tags = []

    def interesting(self):
        # TODO interesting test needs to return a strength, not boolean
        # look for the object ID and return name and last modified date, owner and shared with
        objfind = "match (o:Object)-[:is_from]->(s:Source)" \
                  "match (o)-[:belongs_to]-(a:Account) " \
                  "match (o)-[:is_a]-(ot:ObjectType) " \
                  "WHERE o.id = '{0}'" \
                  "return o.name, o.last_modified, s.name, a.name, ot.name"

        with emedb.driver.session() as session:
            result = session.read_transaction(lambda tx: list(tx.run(objfind.format(self.id))))

        interest = False
        if len(result) == 0:
            interest = True
        else:
            # print("record -> %s %s %s %s %s" % (result[0]['o.name'], result[0]['o.last_modified'],
            #                                     result[0]['s.name'],
            #                                     result[0]['ot.name'], result[0]['a.name']))  # Should only be 1 result
            if self.name != result[0]['o.name']:
                interest = True
            elif self.modified != result[0]['o.last_modified']:
                interest = True
            elif self.source != result[0]['s.name']:
                interest = True
            elif self.account != result[0]['a.name']:
                interest = True
            elif self.type != result[0]['ot.name']:
                interest = True
        return interest

    def save(self):
        # first step is to ensure the document and contextual objects are in place
        objmerge= "merge (:Object {{id: '{0}', name: '{1}', last_modified: '{2}'}})"
        sourcemerge= "merge (:Source {{name: '{0}'}})"
        typemerge= "merge (:ObjectType {{name: '{0}'}})"
        acctmerge= "merge (:Account {{name: '{0}'}})"
        emedb.run(objmerge.format(self.id, self.name, self.modified))
        emedb.run(sourcemerge.format(self.source))
        emedb.run(typemerge.format(self.type))
        emedb.run(acctmerge.format(self.account))

        # Next step is to add the relationships to context objects
        relobjtype = "MATCH (o:Object),(ot:ObjectType) WHERE o.id = '{0}' AND ot.name = '{1}' merge (o)-[:is_a]->(ot)"
        relsource = "MATCH (o:Object),(s:Source) WHERE o.id = '{0}' AND s.name = '{1}' merge (o)-[:is_from]->(s)"
        relacct = "MATCH (o:Object),(a:Account) WHERE o.id ='{0}' AND a.name = '{1}' merge (o)-[:belongs_to]->(a)"
        emedb.run(relsource.format(self.id, self.source))
        emedb.run(relobjtype.format(self.id, self.type))
        emedb.run(relacct.format(self.id, self.account))

        # Next step is to add any new tags to the database and their relationship to the object
        # TODO - strip out meaningless words??
        tagmerge = "merge (:Tag {{name: '{0}'}})"
        tagrel = "MATCH (o:Object),(t:Tag) WHERE o.id = '{0}' AND t.name = '{1}' merge (o)-[:has_tag]->(t)"
        for tag in self.source_tags:
            if tag:             #  skip empty values
                emedb.run(tagmerge.format(tag))
                emedb.run(tagrel.format(self.id, tag))
        for tag in self.content_tags:
            if tag:             # skip empty values
                emedb.run(tagmerge.format(tag))
                emedb.run(tagrel.format(self.id, tag))
        for tag in self.user_tags:
            if tag:             # skip empty values
                emedb.run(tagmerge.format(tag))
                emedb.run(tagrel.format(self.id, tag))
        # TODO probably should wrap the above in a try/except block

class eme_graph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run(self, cmd):
        with self.driver.session() as session:
            db_result = session.run(cmd)
            for record in db_result:
                print("DB_result Record :%s" % record)

        return db_result

    def confirm_required_objects(self):
        with self.driver.session() as session:
            session.run("merge (n:EME_Owner {name: 'Erik Dahl', startDate: '01/30/2021'})")
            session.run("merge (a:Account {name: 'Account #1', startDate: '01/31/2021', creds: ''}) ")
            rel = "MATCH (o:EME_Owner),(a:Account) WHERE o.name='Erik Dahl' AND a.name = 'Account #1' merge (o)-[:owns]->(a)"
            session.run(rel)
        # TODO - figure out how to determine if there was an error - shouldn't be one, but...
        if False:
            raise ValueError("Owner or Account Objects are missing!")
            return -1
        else:
            return True


def tag_source(thedoc):
    tlist = []
    tlist.extend(re.split("[; ,._\-\%]", thedoc.get('name')))
    tlist.append(thedoc['modifiedTime'])
    tlist.append(thedoc['owners'][0].get('displayName', 'none'))
    # TODO get parent folder name
    # TODO get list of shared with people

    return tlist


def tag_content(text):
    ml = MonkeyLearn('ed48b60fefe026fce0c8220fbbfbdad812c5a7c0')
    model_id = 'ex_YCya9nrn'
    data = [text]
    result = ml.extractors.extract(model_id, data)
    # json_data = json.loads(result)
    json_data = result.body[0]
    # print("json_data['extractions'] %s" % json_data['extractions'])
    # print("%d Keywords" % len(json_data['extractions']))
    thelist = []
    # print("Thelist %s" % thelist)
    for keyword in json_data['extractions']:
        # print("=> %s" % keyword['parsed_value'])
        thelist.append(keyword['parsed_value'])
    return thelist


def doc_getter():
    """
    # TODO complete docGetter full logic
    # for each account:
    #   get_credentials(account)
    #   For each of accountDocs:
    #       If new doc:
    #           get_doc_source_tags(docid)
    #       if interestingDoc(docid):
    #           get_doc_content_tags(docid)
    #           save_doc(docid)
    #
    """
    # TODO get drive and doc services from session
    testDocCount = 1

    interesting_files = 0

    f = retrieve_all_files(service)
    for item in f:
        if testDocCount == 0:
            break
        testDocCount -= 1
        thisdoc = eme_object('Google Docs', 'Account #1', 'doc', item['id'], item['name'], item['modifiedTime'])
        if thisdoc.interesting():
            interesting_files += 1
            print('%s: \t %s' % (item['id'], item['name']))  # item['id']))
            thisdoc.source_tags = tag_source(item)
            # print("Source Tags are: %s" % thisdoc.source_tags)
            txt = ''  # initialize the doc text holder
            # TODO add more generic logic for any doc type
            fileExtension = item['name'].split(".")[-1]
            if fileExtension == 'csv':
                # handle a CSV file
                pass

            elif fileExtension == "txt":
                # print('do a txt file')
                download_file(service, item['id'], item['mimeType'], 'temp.txt')
                tf = open('temp.txt', 'r')
                txt = tf.read()
                tf.close()

            elif fileExtension == 'docx':
                # print('do a docx')
                download_file(service, item['id'], item['mimeType'], item['name'])
                txt = read_docx_text(item['name'])

            elif 'google-apps.document' in item['mimeType']:
                # print('Do a google Doc')
                doc = docs_service.documents().get(documentId=item['id']).execute()
                doc_content = doc.get('body').get('content')
                txt = read_structural_elements(doc_content)

            elif 'google-apps.spreadsheet' in item['mimeType']:  # todo add google sheet logic is same for docs and presentations?
                # print('Do google Sheet')
                pass

            elif '.folder' in item['mimeType']:
                pass
                # print("Folder: %s" % item['name'])

            else:
                print('unknown Doc Type')

            # at this point we have the text from the document
            # now extract keywords from doc name and content and
            # append all to a keyword list
            getKeywords = True         # TODO getKeywords is a flag to skip reading keywords due to quotas
            if txt and getKeywords:
                thisdoc.content_tags = tag_content(txt)
                # print("Content Taglist are: %s" % thisdoc.content_tags)

            # TODO Add in ability to include user tags - may need rules on when to apply them

            thisdoc.save()
    print("%d interesting document(s)" % interesting_files)


def ememain():
    # Startup - Open the database
    emedb.confirm_required_objects()

    if motivation() == 'getdocs':
        doc_getter()

    # Leaving - Shut down the database
    emedb.close()

# UI CONTROLS

def get_session_vars():
    global session
    return {'name' : session.name, 'dbstatus' : session.dbstatus, 'account' : session.account}

def connect_btn():
    print ("executing connect action")

    # TODO do your voodoo here
    # TODO add drive service and doc service to session
    global session
    accountID = 1
    session.setcreds(get_credentials(accountID))
    service = build('drive', 'v3', credentials=session.creds)
    http = session.creds.authorize(Http())
    docs_service = discovery.build(
        'docs', 'v1', http=http, discoveryServiceUrl=DISCOVERY_DOC)

    session.setname('Erik')                 # TODO get this from the database
    session.setacct('edahl9000@gmail.com')  # TODO get this from the database
    varlist = get_session_vars()
    return json.dumps(varlist, indent = 4)  # jsonify(status=session.dbstatus, account=session.account, name=session.name) # render_template('index.html', varlist=VARLIST)

###   GLOBAL DATABASE CONNECTION
try:
    emedb = eme_graph("bolt://localhost:7687", "eme", "eme")  # TODO put the database creds in the database
    print("************** Connected to the eMe database")

    ###  SETUP SESSION OBJECT
    session = eme_session('', 'No Account', 'Connected', None)
except:
    sys.exit("************** Error connecting to the eMe database")
