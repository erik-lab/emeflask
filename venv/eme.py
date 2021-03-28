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
from flask import Response
import base64
# import pandas


# GLOBALS for eme Module for now - specific to Google API access
# If modifying these scopes, delete the file drive.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.readonly',
          'https://www.googleapis.com/auth/documents.readonly',
          'https://www.googleapis.com/auth/gmail.readonly']
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
    account += 1    # debugging

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        credentials = tools.run_flow(flow, store)
    return credentials


def download_gdrive_file(service, file_id, mimetype, filename):
    if "google-apps" in mimetype:
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


def download_gmail_attachments(service, msg_id):
    try:
        message = service.users().messages().get(userId='me', id=msg_id).execute()

        for part in message['payload']['parts']:
            if part['filename']:
                if 'data' in part['body']:
                    data = part['body']['data']
                else:
                    att_id = part['body']['attachmentId']
                    att = service.users().messages().attachments().get(userId='me', messageId=msg_id,
                                                                       id=att_id).execute()
                    data = att['data']
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                path = 'temp/' + part['filename']

                with open(path, 'wb') as f:
                    f.write(file_data)

    except errors.HttpError as error:
        print(f"An error occurred: {error}")


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
    #  What is the system motivated to do next?
    # TODO - figure out motivation logic/process
    return 'getdocs'


class Account:
    def __init__(self, name, account_id, service, path_nm, path_id):
        self.name = name
        self.account_id = account_id
        self.service = service
        self.path_nm = path_nm
        self.path_id = path_id


class Eme_Session:
    def __init__(self, name='', account='', dbstatus='Not Connected', creds=None):
        self.accounts = []      # populate with Account objects
        self.name = name
        self.account = account
        self.dbstatus = dbstatus
        self.creds = creds
        self.drive_service = None
        self.doc_service = None
        self.gmail_service = None
        self.path_nm = ['/']
        self.path_id = ['root']
        self.shared_view = False
        # TODO convert account details to a list of account objects

    def add_account(self, name, account_id, service, path_nm='', path_id=''):
        acct = Account(name, account_id, service, path_nm, path_id)
        self.accounts.append(acct)

    def setname(self, name):
        self.name = name

    def setacct(self, account):
        self.account = account

    def setdb(self, dbstatus):
        self.dbstatus = dbstatus

    def setcreds(self, creds):
        self.creds = creds

    def setdrive(self, drive_service):
        self.drive_service = drive_service

    def setdoc(self, doc_service):
        self.doc_service = doc_service

    def setgmail(self, gmail_service):
        self.gmail_service = gmail_service

    def resetpath(self):
        self.path_nm = ['/']
        self.path_id = ['root']

    def add_path(self, folder_id, folder_name):
        self.path_nm.append(folder_name)
        self.path_id.append(folder_id)

    def set_shared_view(self, shared_view):
        self.shared_view = shared_view

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


class Eme_Object:
    def __init__(self, obj_source, obj_acct, obj_type, obj_id, obj_name, obj_mod, mimetype=None, parents=[], owner=None):
        self.source = obj_source
        self.type = obj_type
        self.id = obj_id
        self.obj_source_id = None   # this is used for the gmail message id
        self.name = obj_name
        self.modified = obj_mod     # TODO read up on how to create indexes on date properties
        self.account = obj_acct
        self.owner = owner
        self.mimeType = mimetype
        self.parents = []
        self.parent_ids = parents
        self.source_tags = []
        self.content_tags = []
        self.user_tags = []


    def set_parents(self, ids, names):
        self.parents = names
        self.parent_ids = ids

    def interesting(self):
        # TODO interesting test needs to return a strength, not boolean
        # look for the object ID and return name and last modified date, owner and shared with
        objfind = "match (o:Object)-[:is_from]->(s:Source)" \
                  "match (o)-[:belongs_to]-(a:Account) " \
                  "match (o)-[:is_a]-(ot:ObjectType) " \
                  "WHERE o.id = '{0}'" \
                  "return o.name, o.last_modified, s.name, a.name, ot.name"

        with emedb.driver.session() as dbsession:
            result = dbsession.read_transaction(lambda tx: list(tx.run(objfind.format(self.id))))

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
        objmerge = "merge (:Object {{id: '{0}', name: '{1}', last_modified: '{2}'}})"
        sourcemerge = "merge (:Source {{name: '{0}'}})"
        typemerge = "merge (:ObjectType {{name: '{0}'}})"
        acctmerge = "merge (:Account {{name: '{0}'}})"
        parentmerge = "merge (:Parent {{name: '{0}'}})"
        emedb.run(objmerge.format(self.id, self.name, self.modified))
        emedb.run(sourcemerge.format(self.source))
        emedb.run(typemerge.format(self.type))
        emedb.run(acctmerge.format(self.account))
        for parent in self.parents:
            emedb.run(parentmerge.format(parent))

        # Next step is to add the relationships to contextual objects
        relobjtype = "MATCH (o:Object),(ot:ObjectType) WHERE o.id = '{0}' AND ot.name = '{1}' merge (o)-[:is_a]->(ot)"
        relsource = "MATCH (o:Object),(s:Source) WHERE o.id = '{0}' AND s.name = '{1}' merge (o)-[:is_from]->(s)"
        relacct = "MATCH (o:Object),(a:Account) WHERE o.id ='{0}' AND a.name = '{1}' merge (o)-[:belongs_to]->(a)"
        relparent = "MATCH (o:Object),(p:Parent) WHERE o.id ='{0}' AND p.name = '{1}' merge (o)-[:is_in]->(p)"
        relparent_acct = "MATCH (p:Parent),(s:Source) WHERE p.name = '{0}' AND s.name = '{1}' \
                            merge (p)-[:is_from]->(s)"
        relparent_source = "MATCH (p:Parent),(a:Account) WHERE p.name = '{0}' AND a.name = '{1}' \
                            merge (p)-[:belongs_to]->(a)"
        emedb.run(relsource.format(self.id, self.source))
        emedb.run(relobjtype.format(self.id, self.type))
        emedb.run(relacct.format(self.id, self.account))
        for parent in self.parents:
            emedb.run(relparent.format(self.id, parent))
            emedb.run(relparent_acct.format(parent, self.account))
            emedb.run(relparent_source.format(parent, self.source))

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
        with self.driver.session() as dbsession:
            db_result = dbsession.run(cmd)
            for record in db_result:
                print("DB_result Record :%s" % record)
        return db_result

    def confirm_required_objects(self):
        with self.driver.session() as dbsession:
            dbsession.run("merge (n:EME_Owner {name: 'Erik Dahl', startDate: '01/30/2021'})")
            dbsession.run("merge (a:Account {name: 'Account #1', startDate: '01/31/2021', creds: ''}) ")
            rel = "MATCH (o:EME_Owner),(a:Account) " \
                  "WHERE o.name='Erik Dahl' AND a.name = 'Account #1' " \
                  "merge (o)-[:owns]->(a)"
            dbsession.run(rel)
        # TODO - figure out how to determine if there was an error - shouldn't be one, but...


def get_gmail_parents(service, ids):
    # for each of the IDs, get the label name and append name to the return list
    plist = []

    for pid in ids:
        try:
            res = session.gmail_service.users().labels().get(userId='me', id=pid).execute()
            plist.append(res['name'])
        except:
            plist.append("No Labels")
            raise

    return plist


def get_gdrive_parents(service, ids):
    # for each of the IDs, get the document info and append name to the return list

    plist = []
    for pid in ids:
        try:
            parent = service.files().get(fileId=pid).execute()
            plist.append(parent['name'])
        except:
            plist.append("No Parent")

    return plist


def tag_source(thisdoc):
    print("in tag_source")

    tlist = []
    tlist.extend(re.split("[; ,._\-\%]", thisdoc.name))
    tlist.append(thisdoc.modified)
    tlist.append(thisdoc.owner)
    for tag in thisdoc.parents:
        tlist.append(tag)
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


def scan_gmail_doc(service, thisdoc):
    """ tag scanning for a GMail document

    :service:  the gmail service to use
    :thisdoc: the eme object to work on
    :return: boolean if document is interesting
    """
    print(f"Email Scan Doc called: {thisdoc.name}")
    global session

    if thisdoc.interesting():
        thisdoc.source_tags = tag_source(thisdoc)
        # print("Source Tags are: %s" % thisdoc.source_tags)

        txt = ''  # initialize the doc text holder
        # TODO add more generic logic for any doc type
        ext = thisdoc.name.split(".")[-1]
        if ext == 'csv':
            # handle a CSV file
            pass

        elif ext == "txt":
            # print('do a txt file')
            download_gmail_attachments(service, thisdoc.obj_source_id)
            tf = open('temp/' + thisdoc.name, 'r')
            txt = tf.read()
            tf.close()

        elif ext == 'docx':
            # print('do a docx')
            download_gmail_attachments(service, thisdoc.obj_source_id)
            txt = read_docx_text('temp/' + thisdoc.name)

        elif 'google-apps.document' in thisdoc.mimeType:
            print("Got a Google Docs Document!")

        elif 'google-apps.spreadsheet' in thisdoc.mimeType:
            # todo add google sheet logic is same for docs and presentations?
            print("Got a Google Sheets Document!")
            pass

        else:
            print(f"Other Doc Type: {thisdoc.mimeType}")

        # at this point we have the text from the document
        # now extract keywords from doc name and content and
        # append all to a keyword list
        getKeywords = False         # TODO getKeywords is a flag to skip reading keywords due to API quotas
        if txt and getKeywords:
            thisdoc.content_tags = tag_content(txt)
            # print("Content Taglist are: %s" % thisdoc.content_tags)

        # TODO Add in ability to include user tags - may need rules on when to apply them
        thisdoc.save()
        return True
    else:
        return False


def scan_gmail_attachments(service):
    """ look through all messages with attachments and process documents

    get email list for folder
    for each file
        if contains an attachment
            for each attachment
                scan_document
    :param service: Gmail Service to use
    :return: int: count of the number of interesting docs scanned
    """
    global session
    print(f"scan gmail attachments called")

    msgs = service.users().messages().list(userId='me', q='has:attachment').execute().get('messages', [])
    interesting = 0
    for msg in msgs:
        msgDetail = service.users().messages().get(userId='me', id=msg['id']).execute()  # Get the message
        labels = msgDetail['labelIds']
        payload = msgDetail['payload']
        headers = payload['headers']
        subject = sender = msgdate = recipient = ''

        # Look for Subject and Sender Email in the headers
        for d in headers:
            if d['name'] == 'Subject':
                subject = d['value']
            if d['name'] == 'From':
                sender = d['value']
            if d['name'] == 'Date':
                msgdate = d['value']
            if d['name'] == 'To':
                recipient = d['value']

        msg_parts = payload.get('parts')  # fetching the message parts
        for part in msg_parts:
            if 'attachmentId' in part['body']:
                thisdoc = Eme_Object('Gmail Doc', 'Account #1', 'doc', part['body']['attachmentId'],
                                     part['filename'], msgdate, part['mimeType'],
                                     labels, recipient)
                thisdoc.parents = get_gmail_parents(service, thisdoc.parent_ids)
                thisdoc.obj_source_id = msg['id']

                # Get the attachment and call scan_gmail_doc
                if scan_gmail_doc(service, thisdoc):
                    interesting += 1
    return interesting


def gmail_scanner():
    """ scan selected email folders for messages with attachments and scan the attachments

    :return: int:  count of interesting documents scanned
    """
    print("In Gmail Scan")
    interesting = 0

    if motivation() == 'getdocs':   # TODO figure out the motivation driver
        interesting += scan_gmail_attachments(session.gmail_service)
        result = json.dumps({'return_code': 'Motivated', 'scan_count': interesting}, indent=4)
    else:
        result = json.dumps({'return_code': 'Not motivated', 'scan_count': '0'}, indent=4)

    print(result)

    return result


def retrieve_Gdrive_files(service, parent='root', filter=None, shared=False):
    """Retrieve a list of File resources.

    Args:
      service: Drive API service instance.
    Returns:
      List of File resources.
      :param service:
      :param parent:
      :param filter:
      :param shared:

    """
    print("in retrieve_all_files")
    result = []
    page_token = None
    param = {'corpora': 'user', 'fields': '*'}

    if shared:
        if parent == 'root':
            param['q'] = f"trashed = false and sharedWithMe"
        else:
            param['q'] = f"trashed = false and '{parent}' in parents"
        param['includeItemsFromAllDrives'] = 'true'
        param['supportsAllDrives'] = 'true'
        param['orderBy'] = 'folder,name'
        param['spaces'] = 'drive'
    else:
        param['q'] = f"trashed = false and '{parent}' in parents"
        param['includeItemsFromAllDrives'] = 'false'
        param['supportsAllDrives'] = 'true'
        param['orderBy'] = 'folder,name'
        param['spaces'] = 'drive'

    while True:
        if page_token:
            param['pageToken'] = page_token
        try:
            res = service.files()
            try:
                xfiles = res.list(**param).execute()
            except:
                print("Error with retrieve_gdrive_files - service.files() resource: %s" % res)
                raise
        except:
            print("Error with retrieve_gdrive_files res.list() ")
            raise

        result.extend(xfiles['files'])
        page_token = xfiles.get('nextPageToken')
        if not page_token:
            break

    return result


def scan_drive_folder(folder_id, recurse=False):
    """ Scan all docs in a folder and optionally recurse to child folders

    get file list
    for each file
        if child folder and recurse
            scan_folder (child)
        else
            scan_file(file_id)

    TODO - need to implement folder history to avoid looping
    :param folder_id:
    :param recurse:
    :return: int: count of the number of interesting docs scanned
    """
    global session
    print(f"Scan_folder called: {folder_id}")
    f = retrieve_Gdrive_files(session.drive_service, parent=folder_id, shared=session.shared_view)

    interesting = 0
    for item in f:
        if '.folder' in item['mimeType']:
            if recurse:
                if folder_id != item['id']:            # avoid opening the same folder
                    interest = scan_drive_folder(item['id'], recurse)
                    interesting += interest
            continue
        else:
            thisdoc = Eme_Object('Google Docs', 'Account #1', 'doc', item['id'], item['name'], item['modifiedTime'],
                                 item['mimeType'], item.get('parents', ['its empty']), item['owners'][0].get('displayName', 'none'))
                                 # item['mimeType'], item['parents'], item['owners'][0].get('displayName', 'none'))
            thisdoc.parents = get_gdrive_parents(session.drive_service, thisdoc.parent_ids)
            if scan_drive_doc(thisdoc):
                interesting += 1
            # print(f"ID; {item['id']}, \t {item['name']}")
    return interesting


def scan_drive_doc(thisdoc):
    """ tag scanning for a document
    :return: boolean if document is interesting
    """
    print(f"Scan Doc called: {thisdoc.name}")
    global session

    if thisdoc.interesting():
        print('%s: \t %s' % (thisdoc.id, thisdoc.name))
        thisdoc.source_tags = tag_source(thisdoc)
        # print("Source Tags are: %s" % thisdoc.source_tags)

        txt = ''  # initialize the doc text holder
        # TODO add more generic logic for any doc type
        ext = thisdoc.name.split(".")[-1]
        if ext == 'csv':
            # handle a CSV file
            pass

        elif ext == "txt":
            # print('do a txt file')
            download_gdrive_file(session.drive_service, thisdoc.id, thisdoc.mimeType, 'temp/temp.txt')
            tf = open('temp/temp.txt', 'r')
            txt = tf.read()
            tf.close()

        elif ext == 'docx':
            # print('do a docx')
            download_gdrive_file(session.drive_service, thisdoc.id, thisdoc.mimeType, 'temp/' + thisdoc.name)
            txt = read_docx_text('temp/' + thisdoc.name)

        elif 'google-apps.document' in thisdoc.mimeType:
            # print('Do a google Doc')
            doc = session.doc_service.documents().get(documentId=thisdoc.id).execute()
            doc_content = doc['body']['content']
            txt = read_structural_elements(doc_content)
            print("Did Google Doc")

        elif 'google-apps.spreadsheet' in thisdoc.mimeType:
            # todo add google sheet logic is same for docs and presentations?
            # print('Do google Sheet')
            pass

        else:
            print('unknown Doc Type')

        # at this point we have the text from the document
        # now extract keywords from doc name and content and
        # append all to a keyword list
        getKeywords = False         # TODO getKeywords is a flag to skip reading keywords due to API quotas
        if txt and getKeywords:
            thisdoc.content_tags = tag_content(txt)
            # print("Content Taglist are: %s" % thisdoc.content_tags)

        # TODO Add in ability to include user tags - may need rules on when to apply them
        thisdoc.save()
        return True
    else:
        return False


def gdrive_scanner():
    """Scan all documents request from the UI

    :return: int - count of documents scanned
    """
    if motivation() == 'getdocs':
        session.resetpath()
        session.shared_view = False
        interesting = 0
        interesting += scan_drive_folder(session.path_id[0], recurse=True)
        session.shared_view = True
        interesting += scan_drive_folder(session.path_id[0], recurse=True)

        result = json.dumps({'return_code': 'Motivated', 'scan_count': interesting}, indent=4)
    else:
        result = json.dumps({'return_code': 'Not motivated', 'scan_count': '0'}, indent=4)
    return result


def get_session_vars():
    # TODO modify to pull values from the database
    global session
    return {'name': session.name, 'dbstatus': session.dbstatus, 'account': session.account}


def connect_btn():
    print("in connect_btn")
    global session

    # Connect to 3 services - GDrive, Gdocs, Gmail
    # and also returns Account owner information
    # TODO refactor this into selarate connect modules

    # GDrive Service
    accountID = 1       # TODO get this from the database
    session.setcreds(get_credentials(accountID))
    service = build('drive', 'v3', credentials=session.creds)
    http = session.creds.authorize(Http())
    session.setdrive(service)

    # GDocs Service
    docs_service = discovery.build(
        'docs', 'v1', http=http, discoveryServiceUrl=DISCOVERY_DOC)
    session.setdoc(docs_service)

    # GMail Service
    # creds = None
    # The file gmail.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    pkl = None
    if os.path.exists('gmail.pickle'):
        with open('gmail.pickle', 'rb') as token:
            pkl = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not pkl or not pkl.valid:
        if pkl and pkl.expired and pkl.refresh_token:
            pkl.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'gmailCredentials.json', SCOPES)
            pkl = flow.run_local_server(port=0)
        # Save the pickle for the next run
        with open('gmail.pickle', 'wb') as token:
            pickle.dump(pkl, token)

    gmail_service = build('gmail', 'v1', credentials=pkl)
    # Call the Gmail API
    results = gmail_service.users().labels().list(userId='me').execute()
    session.setgmail(gmail_service)
    labels = results.get('labels', [])
    # print(f"labels: {json.dumps(labels, indent=4)}")

    # Account Owner Information
    session.setname('Erik')                 # TODO get this from the database
    session.setacct('edahl9000@gmail.com')  # TODO get this from the database
    varlist = get_session_vars()

    return json.dumps(varlist, indent=4)
    # jsonify(status=session.dbstatus, account=session.account, name=session.name)
    # render_template('docTagger.html', varlist=VARLIST)


def doc_reader(shared=False):
    # read the list of documents from the current directory settings
    filelist = [{'id': '1', 'name': 'file #1', 'type': 'third file'},
                {'id': '2', 'name': 'file #2', 'type': 'type 3'}]       # debugging
    filelist = []   # debugging
    print("in doc_reader")      # TODO doc_reader remove this
    global session
    session.resetpath()         # set back to root (shared will have to test for this)

    if shared:
        session.set_shared_view(True)
        try:
            files = retrieve_Gdrive_files(session.drive_service, parent=session.path_id[0], shared=shared)
        except:
            print("Doc_Reader retrieve error - for shared Docs - ending")
            return
    else:
        session.set_shared_view(False)
        try:
            dir = session.path_id[len(session.path_id)-1]       # TODO doc_reader will always be at root
            files = retrieve_Gdrive_files(session.drive_service, parent=dir, shared=shared)
        except:
            print("Doc_Reader retrieve error - for My Docs - ending")
            return
    if files:
        print("File Count: %s" % len(files))    # TODO doc_reader remove this

    if files:
        testDocCount = 30                       # TODO - take this out
        for item in files:
            if testDocCount == 0:
                break
            testDocCount -= 1
            filelist.append({'id': item['id'], 'name': item['name'], 'mimeType': item['mimeType'],
                            'parents': item.get('parents', ['No Parent'])})
        # print(f"filelist: {json.dumps(filelist, indent=2)}")      # TODO Remove this

    return json.dumps(filelist, indent=4)


def tag_reader(objid=str):
    if objid:
        # look for the object ID and return name and last modified date, owner and shared with

        objfind = f"MATCH (t:Tag)--(o:Object) where o.id = {objid} \
                    WITH t \
                    OPTIONAL MATCH (t)--(b:Object) \
                    WITH t, count(b) as freq \
                    RETURN t.name as tag, freq \
                    ORDER BY freq desc, tag asc"

        with emedb.driver.session() as db:
            result = db.read_transaction(lambda tx: list(tx.run(objfind)))
        # print(f"Result: {result}")
        tags = []
        for record in result:
            tags.append(dict(record))
            # print("dict(record) %s" % dict(record))

        if len(result) == 0:
            tags = [{'tag': 'No Tags'}]
    else:
        tags = [{'tag': 'No ID'}]

    print(f"in eme.doc_reader {objid}")
    # print(f"taglist is: {taglist}")

    # return json.dumps(result, indent=4)
    return Response(json.dumps(tags), mimetype="application/json")


# #######  GLOBAL DATABASE CONNECTION
try:
    emedb = eme_graph("bolt://localhost:7687", "eme", "eme")  # TODO put the database creds in encrypted file
    print("************** Connected to the eMe database")
    emedb.confirm_required_objects()

    # ##  SETUP SESSION OBJECT
    session = Eme_Session('', 'Not Connected', 'Connected', None)
except:
    sys.exit("************** Error connecting to the eMe database")
