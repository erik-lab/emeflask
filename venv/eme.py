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
# from oauth2client import client
# from oauth2client import file
# from oauth2client import tools
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from operator import itemgetter, attrgetter
from monkeylearn import MonkeyLearn
from docx import Document
from neo4j import GraphDatabase
import os
import sys
from flask import Response
import base64
import nltk
from nltk.corpus import stopwords
from datetime import datetime, timezone
import dateutil.parser

# import pandas


# GLOBALS for eme Module for now - specific to Google API access
# If modifying these scopes, delete the file drive.pickle.
DriveSCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
               'https://www.googleapis.com/auth/drive.readonly',
               'https://www.googleapis.com/auth/documents.readonly']
GmailSCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
DISCOVERY_DOC = 'https://docs.googleapis.com/$discovery/rest?version=v1'
DOCUMENT_ID = '1ht6PMhI5JIcaQLqgsMBQhwOIIlHYr455'  # used for debugging and testing
STOPWORDS = stopwords.words('english')


def get_saved_credentials(acct, source):
    '''Read in any saved OAuth data/tokens
    '''
    fileData = {}
    filename = 'token-' + acct + '-' + source + '.json'
    try:
        with open(filename, 'r') as file:
            fileData: dict = json.load(file)
    except FileNotFoundError:
        return None
    if fileData and 'refresh_token' in fileData and 'client_id' in fileData and 'client_secret' in fileData:
        c = Credentials(**fileData)
        tokenread = "match (a:Account {{name: '{0}'}})-[:owns]-(s:Source {{name: '{1}' }}) return s.creds as cred"
        with emedb.driver.session() as db:
            r = db.read_transaction(lambda tx: list(tx.run(tokenread.format(acct, source))))
        if len(r) == 0:
            raise Exception(f"Unable to find a token for {acct}, {source}")
        else:
            cred = r[0]['cred']
            creddict: dict = json.loads(cred)
            r = Credentials(**creddict)
        return r        # return c from file
    return None


def store_creds(credentials, acct, source):
    if not isinstance(credentials, Credentials):
        return
    fileData = {'refresh_token': credentials.refresh_token,
                'token': credentials.token,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'token_uri': credentials.token_uri}
    filename = filename = 'token-' + acct + '-' + source + '.json'
    with open(filename, 'w') as file:
        json.dump(fileData, file)
    c = Credentials(**fileData)     # cred to be returned from the file
    # credjson = c.to_json()
    token_string = json.dumps(fileData)
    tokensave = "match (a:Account {{name: '{0}'}}) \
                 merge (a)-[:owns]-(s:Source {{name: '{1}'}}) \
                 set s.creds = '{2}' return s"
    try:
        res = emedb.run(tokensave.format(acct, source, token_string))
    except:
        raise

    print(f'Credentials serialized to {filename} and the database.')
    return


def get_credentials_via_oauth(acct, source, filename='client_secret.json', scopes=None, saveData=True) -> Credentials:
    '''Use data in the given filename to get oauth data'
    '''
    print(f"Get_credential_via_oauth.  Acct: {acct}, source: {source}")
    iaflow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(filename, scopes)
    iaflow.run_local_server()
    if saveData:
        store_creds(iaflow.credentials, acct, source)
    return iaflow.credentials


def get_service(credentials, service='drive', version='v3'):
    return build(service, version, credentials=credentials)


#  TODO My versions - keep till the database conversion is compelete then drop
def save_creds_to_db (acct, source, creds):
    credjson = creds.to_json()
    token_string = json.dumps(credjson, indent=2)
    tokensave = "match (a:Account {{name: '{0}'}}) \
                 merge (a)-[:owns]-(s:Source {{name: '{1}'}}) \
                 set s.creds = '{2}' return s"
    res = emedb.run(tokensave.format(acct, source, token_string))

    return res


#  TODO My versions - keep till the database conversion is compelete then drop
def read_creds_from_db(acct, source):
    tokenread = "match (a:Account {{name: '{0}'}})-[:owns]-(s:Source {{name: '{1}' }}) return s.creds as cred"
    with emedb.driver.session() as db:
        r = db.read_transaction(lambda tx: list(tx.run(tokenread.format(acct, source))))
    if len(r) == 0:
        print("Unable to find a token")
        return 0
    else:
        cred = r[0]['cred']
        # cred = json.loads(cred_record['cred'])
        print(f"returned Cred, {cred}")
        reconstituted = Credentials(cred)

    return reconstituted

#  TODO My versions - keep till the database conversion is compelete then drop
def get_credentials(acct, source):
    """ TODO Get valid user credentials from database for a specific source.

    If nothing has been stored, or if the stored credentials are invalid,
    the Google-Auth flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    print(f"in Get Credentials {acct}, {source}")

    # os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'D:\\edahl\\Documents\\flask2\\venv\\Credentials.json'

    creds = None
    tokenfile = 'token-' + acct + '-' + source + '.json'
    if os.path.exists(tokenfile):
        creds = Credentials.from_authorized_user_file(tokenfile, DriveSCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'Credentials.json', DriveSCOPES)
            creds = flow.run_local_server(port=0)
        # Save the token for the next run
        with open(tokenfile, 'w') as token:
            token.write(creds.to_json())

    save_creds_to_db(acct, source, creds)
    recreds = read_creds_from_db(acct, source)
    creds = recreds

    return creds

    # Old stull but has procedure for saving and restoring from DB
    # store = file.Storage('token.json')
    # credentials = store.get()

    # TODO Testing - add token to the database & get it back out
    # creds = credentials.to_json()
    # token_string = json.dumps(creds, indent=2)
    # tokensave = "merge (:Test {{name: 'test', cred: {0} }})"
    # res = emedb.run(tokensave.format(token_string))
    # tokenread = "match (t:Test) where t.name = 'test' return t.cred as cred"
    # with emedb.driver.session() as db:
    #     r = db.read_transaction(lambda tx: list(tx.run(tokenread)))
    # if len(r) == 0:
    #     print("Unable to find a token")
    # else:
    #     cred = r[0]['cred']
    #     # cred = json.loads(cred_record['cred'])
    #     print(f"returned Cred, {cred}")
    # reconstituted = client.OAuth2Credentials.from_json(cred)
    #
    # # print(r)
    #
    # if not credentials or credentials.invalid:
    #     flow = client.flow_from_clientsecrets('credentials.json', DriveSCOPES)
    #     credentials = tools.run_flow(flow, store)
    # return credentials


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
        self.accounts = []  # populate with Account objects
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
        self.object_list = []
        self.scanned_folders = []
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
    def __init__(self, obj_source, obj_acct, obj_type, obj_id, obj_name, obj_mod, mimetype=None, parents=[],
                 owner=None, share_to_me='no', share_from_me='no'):
        self.source = obj_source
        self.type = obj_type
        self.id = obj_id
        self.obj_source_id = None  # this is used for the gmail message id
        self.name = obj_name
        self.modified = obj_mod  # TODO read up on how to create indexes on date properties
        self.account = obj_acct
        self.owner = owner
        self.shared_to_me = share_to_me
        self.shared_from_me = share_from_me
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
            res = dbsession.read_transaction(lambda tx: list(tx.run(objfind.format(self.id))))

        interest = False
        if len(res) == 0:
            interest = True
        else:
            # print("record -> %s %s %s %s %s" % (res[0]['o.name'], res[0]['o.last_modified'],
            #                                     res[0]['s.name'],
            #                                     res[0]['ot.name'], res[0]['a.name']))  # Should only be 1 res
            if self.name != res[0]['o.name']:
                interest = True
                # print(f"The names are different {self.name}, {res[0]['o.name']}")
            elif self.modified != res[0]['o.last_modified']:
                interest = True
                # print(f"The Dates are different {self.modified}, {res[0]['o.last_modified']}")
            elif self.source != res[0]['s.name']:
                interest = True
                # print(f"The sources are different {self.source}, {res[0]['s.name']}")
            elif self.account != res[0]['a.name']:
                interest = True
                # print(f"The account are different {self.account}, {res[0]['a.name']}")
            elif self.type != res[0]['ot.name']:
                interest = True
                # print(f"The types are different {self.type}, {res[0]['ot.name']}")
        print(f"Checking Interest: {self.name} - {interest}")
        return interest

    def save(self):
        print(f"Saving Object: {self.name}")

        # first step is to ensure the document and contextual objects are in place
        objmerge = "merge (:Object {{id: '{0}', name: '{1}', last_modified: '{2}', \
                   obj_source_id: '{3}', mimeType: '{4}', shared_to_me: '{5}',shared_from_me: '{6}'}})"
        # acctmerge = "merge (:Account {{name: '{0}'}})"        # Can assume they exist already
        # sourcemerge = "match (a:Account {{name: '{0}}'} \
        #                merge (a)-[:owns]-(s:Source {{name: '{1}'}})"
        typemerge = "merge (:ObjectType {{name: '{0}'}})"
        parentmerge = "merge (:Parent {{name: '{0}'}})"
        emedb.run(objmerge.format(self.id, self.name.lower(), self.modified, self.obj_source_id, self.mimeType,
                                  self.shared_to_me, self.shared_from_me))
        # emedb.run(sourcemerge.format(self.source, self.account))
        # emedb.run(acctmerge.format(self.account))
        emedb.run(typemerge.format(self.type))
        for parent in self.parents:
            emedb.run(parentmerge.format(parent))

        # Next step is to add the relationships to contextual objects
        relacct = "MATCH (o:Object),(a:Account) WHERE o.id ='{0}' AND a.name = '{1}' merge (o)-[:belongs_to]->(a)"
        relsource = "MATCH (o:Object),(s:Source) WHERE o.id = '{0}' AND s.name = '{1}' merge (o)-[:is_from]->(s)"
        relparent = "MATCH (o:Object),(p:Parent) WHERE o.id ='{0}' AND p.name = '{1}' merge (o)-[:is_in]->(p)"
        relobjtype = "MATCH (o:Object),(ot:ObjectType) WHERE o.id = '{0}' AND ot.name = '{1}' merge (o)-[:is_a]->(ot)"
        relparent_source = "MATCH (p:Parent) WHERE p.name = '{0}' \
                          MATCH (s:Source) WHERE s.name = '{1}' \
                          MERGE (p)-[:is_from]->(s)"
        relparent_acct = "MATCH (p:Parent) WHERE p.name = '{0}' " \
                         "MATCH (a:Account) WHERE a.name = '{1}' " \
                         "MERGE (p)-[:belongs_to]->(a)"
        relacct_source = "MATCH (a:Account) WHERE a.name = '{0}' " \
                         "MATCH (s:Source) WHERE s.name = '{1}' " \
                         "MERGE (a)-[:owns]->(s)"
        emedb.run(relsource.format(self.id, self.source))
        emedb.run(relobjtype.format(self.id, self.type))
        emedb.run(relacct.format(self.id, self.account))
        emedb.run(relacct_source.format(self.account, self.source))
        for parent in self.parents:
            emedb.run(relparent.format(self.id, parent))
            emedb.run(relparent_acct.format(parent, self.account))
            emedb.run(relparent_source.format(parent, self.source))

        # Next step is to add any new tags to the database and their relationship to the object
        # TODO - strip out meaningless words??
        tagmerge = "merge (:Tag {{name: '{0}'}})"
        tagrel = "MATCH (o:Object),(t:Tag) WHERE o.id = '{0}' AND t.name = '{1}' merge (o)-[:has_tag]->(t)"
        for tag in self.source_tags:
            if tag:  # skip empty values
                emedb.run(tagmerge.format(tag))
                emedb.run(tagrel.format(self.id, tag))
        for tag in self.content_tags:
            if tag:  # skip empty values
                emedb.run(tagmerge.format(tag))
                emedb.run(tagrel.format(self.id, tag))
        for tag in self.user_tags:
            if tag:  # skip empty values
                emedb.run(tagmerge.format(tag))
                emedb.run(tagrel.format(self.id, tag))
        # TODO probably should wrap the above in a try/except block


class EmeGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run(self, cmd):
        with self.driver.session() as dbsession:
            db_result = dbsession.run(cmd)
            for rec in db_result:
                print("DB_result Record :%s" % rec)
        return db_result

    def confirm_required_objects(self):
        # TODO figure out where owner and accounts come from
        with self.driver.session() as dbsession:
            dbsession.run("merge (n:EME_Owner {name: 'Erik Dahl', startDate: '01/30/2021'})")
            dbsession.run("merge (a:Account {name: 'Account #1', startDate: '01/31/2021'}) ")
            rel = "MATCH (o:EME_Owner),(a:Account) " \
                  "WHERE o.name='Erik Dahl' AND a.name = 'Account #1' " \
                  "merge (o)-[:owns]->(a)"
            dbsession.run(rel)
        # TODO - figure out how to determine if there was an error - shouldn't be one, but...


def minder_init():
    """
    Perform any setup step for opening the finder Page
    e.g. Initiate Session, setup database etc

    :return:
    """
    return True


def minder_go_obj(taglist):
    """
    User clicked Go button -
    input tags parsed and passed from page
    add other context tags
    find objects with matching tags
    Return list of objects
    save object list reference to Session global

    :return: Return object_list
    """
    print(f"In minder_go_obj  Tags: {taglist}")
    if False:
        result = json.dumps([
            {"acct": {"name": "Account #1"}, "source": {"name": "Gmail Doc"}, "parent": {"name": "UNREAD"},
             "doc": {"type": "node", "id": "156", "labels": ["Object"],
                     "properties": {"name": "Photo #1 Feb 28, 12 29 58 PM.jpg", "mimeType": "image/jpeg",
                                    "id": "ANGjdJ_i7KPA8U6L5aGDLbHo9xsBW-3pZYSKpLRucLLrgvhZBN5AMA9-ogdlawWg47CpN5BMDXsoSghN35L7hQm9LVp_3Nai7ZgZLLipIfIslvMNAblee1d952ervADvmaXGsq1-yDMrkz7kt6pKlJ4tYZg62VV8t-NNIpBcDsnVFm6uftdNBdju_Kxai2WwdNPMleLuyikrspR91iuyud7_3GWBOttjuAPS342XYJVI2HlSmBkMh5F__M1Yk1wTzmWr7bFgmbonITjfcFTp_swAI_cMgYD6JwLg08qPi5Z8ZhsYktueY7f_fTd1TlX0giUCYfDlp0fgXFzd7PNH2g-WVE78IgYD_cEE8wIyH1h1ghXc74P0wAUeuqLTVdqrfEmhqjDi4O3ZynZ3DXSR",
                                    "last_modified": "Mon, 22 Mar 2021 04:14:37 -0700",
                                    "obj_source_id": "17859a4d3ea6ddd4"}}},
            {"acct": {"name": "Account #1"}, "source": {"name": "Gmail Doc"}, "parent": {"name": "test Folder"},
             "doc": {"type": "node", "id": "173", "labels": ["Object"],
                     "properties": {"name": "Photo #2 Feb 28, 12 29 58 PM.jpg", "mimeType": "image/jpeg",
                                    "id": "ANGjdJ-PPSbB0rBrP59zkmhLRZRozFyaltK6Zy1gH8hjXiYKe6CpGPtN8A-hrFHODliSJC8OqMgXLZ1RRKpev3sMqCmzFkF1IDus2F6ZBDt_uqi5w3JaNOaeFOZu-LxZKLR683lmajNI33n2ZEWYTiJamZeKpKt3NFR0ouVJS8hHBSulnr2CmhnDktB8fOO9TWxW55JUbGSk4CancrBlb-sJSOpQ5Dkmv63F1mbydxXgpi44The5rMaIHXbtl3k1wfVg7xgvMt81UD68wV7l2aOXE9qTj8e7D-EUnFxJSKgawk_N8D2a71B5-DXS8kbY9Nq83ktfMEXRzyAZIDRvu9-uFVbENwidK4S0cdcjqzzAevvyXB1VhhoPJRL-H3Nv_DzVx_i0YDtuVf-HegRD",
                                    "last_modified": "Sun, 7 Mar 2021 17:28:10 +0000",
                                    "obj_source_id": "1780dbb70a624ae7"}}},
            {"acct": {"name": "Account #1"}, "source": {"name": "Gmail Doc"}, "parent": {"name": "test Folder"},
             "doc": {"type": "node", "id": "173", "labels": ["Object"],
                     "properties": {"name": "Photo #3 Feb 28, 12 29 58 PM.jpg", "mimeType": "image/jpeg",
                                    "id": "ANGjdJ-PPSbB0rBrP59zkmhLRZRozFyaltK6Zy1gH8hjXiYKe6CpGPtN8A-hrFHODliSJC8OqMgXLZ1RRKpev3sMqCmzFkF1IDus2F6ZBDt_uqi5w3JaNOaeFOZu-LxZKLR683lmajNI33n2ZEWYTiJamZeKpKt3NFR0ouVJS8hHBSulnr2CmhnDktB8fOO9TWxW55JUbGSk4CancrBlb-sJSOpQ5Dkmv63F1mbydxXgpi44The5rMaIHXbtl3k1wfVg7xgvMt81UD68wV7l2aOXE9qTj8e7D-EUnFxJSKgawk_N8D2a71B5-DXS8kbY9Nq83ktfMEXRzyAZIDRvu9-uFVbENwidK4S0cdcjqzzAevvyXB1VhhoPJRL-H3Nv_DzVx_i0YDtuVf-HegRD",
                                    "last_modified": "Sun, 7 Mar 2021 17:28:10 +0000",
                                    "obj_source_id": "1780dbb70a624ae7"}}},
            {"acct": {"name": "Account #1"}, "source": {"name": "Gmail Doc"}, "parent": {"name": "test Folder"},
             "doc": {"type": "node", "id": "173", "labels": ["Object"],
                     "properties": {"name": "Photo #4 Feb 28, 12 29 58 PM.jpg", "mimeType": "image/jpeg",
                                    "id": "ANGjdJ-PPSbB0rBrP59zkmhLRZRozFyaltK6Zy1gH8hjXiYKe6CpGPtN8A-hrFHODliSJC8OqMgXLZ1RRKpev3sMqCmzFkF1IDus2F6ZBDt_uqi5w3JaNOaeFOZu-LxZKLR683lmajNI33n2ZEWYTiJamZeKpKt3NFR0ouVJS8hHBSulnr2CmhnDktB8fOO9TWxW55JUbGSk4CancrBlb-sJSOpQ5Dkmv63F1mbydxXgpi44The5rMaIHXbtl3k1wfVg7xgvMt81UD68wV7l2aOXE9qTj8e7D-EUnFxJSKgawk_N8D2a71B5-DXS8kbY9Nq83ktfMEXRzyAZIDRvu9-uFVbENwidK4S0cdcjqzzAevvyXB1VhhoPJRL-H3Nv_DzVx_i0YDtuVf-HegRD",
                                    "last_modified": "Sun, 7 Mar 2021 17:28:10 +0000",
                                    "obj_source_id": "1780dbb70a624ae7"}}}
        ], indent=4)
        docs = result
    else:
        inlist = "["

        for i in range(len(taglist)):
            if i > 0:
                inlist += ","
            inlist += '"' + taglist[i].lower() + '"'
        inlist += "]"
        inlist = inlist.replace("'", "")
        objfind =  "match (t:Tag)--(o:Object)--(ot:ObjectType) \
                    where t.name IN " + \
                    inlist + \
                    " with t, o, ot \
                    match(o)--(s:Source) \
                    return o.name as object, o.id as key, ot.name as type, s.name as source, count(t) as tag_freq  \
                    ORDER BY tag_freq desc"

        print(f"Q: {objfind}")

        try:
            with emedb.driver.session() as db:
                result = db.read_transaction(lambda tx: list(tx.run(objfind)))
        except:
            print("Error reading Object list in procedure minder_go_obj")
            raise

        # print(f"Result: {result}")
        objs = []
        for record in result:
            objs.append(dict(record))
            # print("dict(record) %s" % dict(record))

        return_data = [{'objs': objs}]      # pack objects into element 0 of the results

        # Now get the tags associated with the documents found
        tagfind = "match (o1:Object)--(t1:Tag) \
                   where t1.name in " + \
                   inlist + \
                  "match (o2:Object)--(t2:Tag) \
                   where t2.name in " + \
                   inlist + \
                  "with o1, o2 \
                   match (o1)--(t:Tag)--(o2) \
                   where o1.id < o2.id \
                   return o1.name as fname, o1.id as from, o2.name as tname, o2.id as to, count(t) as strength \
                   order by strength desc"

        # tagfind =  "match (t:Tag)--(o:Object)--(t2:Tag) \
        #             where t.name IN " + \
        #             inlist + \
        #            "return t2.name as name, count(o) as tag_freq \
        #             ORDER BY tag_freq desc"
        #
        try:
            with emedb.driver.session() as db:
                result = db.read_transaction(lambda tx: list(tx.run(tagfind)))
        except:
            print("Error reading tag list in procedure minder_go_obj")
            raise

        # print(f"Result: {result}")
        rels = []
        for record in result:
            rels.append(dict(record))
            # print("dict(record) %s" % dict(record))

        return_data.append({'rels': rels})       # tags as element 2
        # print(f"return_data: {return_data}")

    return Response(json.dumps(return_data), mimetype="application/json")


def minder_go_tags():
    """
    Step 2 after user clicks Go button -
    The list of matched objects is in the session object
    Pull the tags for all documents and compute frequency of unique tags

    :return: Return tag_list ordered by freq desc
    """
    print(f"In minder_go_tags ")
    if True:
        result = json.dumps([
            {'obj': [{'o': 1}, {'o': 2}, {'o': 5}, {'o': 4}]},
            {'tag': [{'t': 9}, {'t': 8}, {'t': 7}, {'t': 6}]}
        ], indent=4)
        objs = result
    else:
        inlist = "["

        taglist = ['erik', 'dahl']

        for i in range(len(taglist)):
            if i > 0:
                inlist += ","
            inlist += '"' + taglist[i].lower() + '"'
        inlist += "]"
        inlist = inlist.replace("'", "")
        objfind =  "match (t:Tag)--(o:Object)--(ot:ObjectType) \
                    where t.name IN " + \
                    inlist + \
                    " with t, o, ot \
                    match(o)--(s:Source) \
                    return o.name as object, ot.name as type, s.name as source, count(t) as tag_freq  \
                    ORDER BY tag_freq desc"

        print(f"Q: {objfind}")

        try:
            with emedb.driver.session() as db:
                result = db.read_transaction(lambda tx: list(tx.run(objfind)))
        except:
            print("Error reading Object list in procedure minder_go_obj")
            raise

        # print(f"Result: {result}")
        objs = []
        for record in result:
            objs.append(dict(record))
            # print("dict(record) %s" % dict(record))

        session.object_list = objs      # save objects in the session

    return Response(objs, mimetype="application/json")
    # return Response(json.dumps(objs), mimetype="application/json")



def finder(options):
    """finder - call from UI to populate the list of files using a specific view type

    :param: viewtype: enum type of view to use
    :return: json list of documents to be rendered
    """
    print(f"in eme.finder as {options}")

    if False:
        result = json.dumps([
            {"acct": {"name": "Account #1"}, "source": {"name": "Gmail Doc"}, "parent": {"name": "UNREAD"},
             "doc": {"type": "node", "id": "156", "labels": ["Object"],
                     "properties": {"name": "Photo #1 Feb 28, 12 29 58 PM.jpg", "mimeType": "image/jpeg",
                                    "id": "ANGjdJ_i7KPA8U6L5aGDLbHo9xsBW-3pZYSKpLRucLLrgvhZBN5AMA9-ogdlawWg47CpN5BMDXsoSghN35L7hQm9LVp_3Nai7ZgZLLipIfIslvMNAblee1d952ervADvmaXGsq1-yDMrkz7kt6pKlJ4tYZg62VV8t-NNIpBcDsnVFm6uftdNBdju_Kxai2WwdNPMleLuyikrspR91iuyud7_3GWBOttjuAPS342XYJVI2HlSmBkMh5F__M1Yk1wTzmWr7bFgmbonITjfcFTp_swAI_cMgYD6JwLg08qPi5Z8ZhsYktueY7f_fTd1TlX0giUCYfDlp0fgXFzd7PNH2g-WVE78IgYD_cEE8wIyH1h1ghXc74P0wAUeuqLTVdqrfEmhqjDi4O3ZynZ3DXSR",
                                    "last_modified": "Mon, 22 Mar 2021 04:14:37 -0700",
                                    "obj_source_id": "17859a4d3ea6ddd4"}}},
            {"acct": {"name": "Account #1"}, "source": {"name": "Gmail Doc"}, "parent": {"name": "test Folder"},
             "doc": {"type": "node", "id": "173", "labels": ["Object"],
                     "properties": {"name": "Photo #2 Feb 28, 12 29 58 PM.jpg", "mimeType": "image/jpeg",
                                    "id": "ANGjdJ-PPSbB0rBrP59zkmhLRZRozFyaltK6Zy1gH8hjXiYKe6CpGPtN8A-hrFHODliSJC8OqMgXLZ1RRKpev3sMqCmzFkF1IDus2F6ZBDt_uqi5w3JaNOaeFOZu-LxZKLR683lmajNI33n2ZEWYTiJamZeKpKt3NFR0ouVJS8hHBSulnr2CmhnDktB8fOO9TWxW55JUbGSk4CancrBlb-sJSOpQ5Dkmv63F1mbydxXgpi44The5rMaIHXbtl3k1wfVg7xgvMt81UD68wV7l2aOXE9qTj8e7D-EUnFxJSKgawk_N8D2a71B5-DXS8kbY9Nq83ktfMEXRzyAZIDRvu9-uFVbENwidK4S0cdcjqzzAevvyXB1VhhoPJRL-H3Nv_DzVx_i0YDtuVf-HegRD",
                                    "last_modified": "Sun, 7 Mar 2021 17:28:10 +0000",
                                    "obj_source_id": "1780dbb70a624ae7"}}},
            {"acct": {"name": "Account #1"}, "source": {"name": "Gmail Doc"}, "parent": {"name": "test Folder"},
             "doc": {"type": "node", "id": "173", "labels": ["Object"],
                     "properties": {"name": "Photo #3 Feb 28, 12 29 58 PM.jpg", "mimeType": "image/jpeg",
                                    "id": "ANGjdJ-PPSbB0rBrP59zkmhLRZRozFyaltK6Zy1gH8hjXiYKe6CpGPtN8A-hrFHODliSJC8OqMgXLZ1RRKpev3sMqCmzFkF1IDus2F6ZBDt_uqi5w3JaNOaeFOZu-LxZKLR683lmajNI33n2ZEWYTiJamZeKpKt3NFR0ouVJS8hHBSulnr2CmhnDktB8fOO9TWxW55JUbGSk4CancrBlb-sJSOpQ5Dkmv63F1mbydxXgpi44The5rMaIHXbtl3k1wfVg7xgvMt81UD68wV7l2aOXE9qTj8e7D-EUnFxJSKgawk_N8D2a71B5-DXS8kbY9Nq83ktfMEXRzyAZIDRvu9-uFVbENwidK4S0cdcjqzzAevvyXB1VhhoPJRL-H3Nv_DzVx_i0YDtuVf-HegRD",
                                    "last_modified": "Sun, 7 Mar 2021 17:28:10 +0000",
                                    "obj_source_id": "1780dbb70a624ae7"}}},
            {"acct": {"name": "Account #1"}, "source": {"name": "Gmail Doc"}, "parent": {"name": "test Folder"},
             "doc": {"type": "node", "id": "173", "labels": ["Object"],
                     "properties": {"name": "Photo #4 Feb 28, 12 29 58 PM.jpg", "mimeType": "image/jpeg",
                                    "id": "ANGjdJ-PPSbB0rBrP59zkmhLRZRozFyaltK6Zy1gH8hjXiYKe6CpGPtN8A-hrFHODliSJC8OqMgXLZ1RRKpev3sMqCmzFkF1IDus2F6ZBDt_uqi5w3JaNOaeFOZu-LxZKLR683lmajNI33n2ZEWYTiJamZeKpKt3NFR0ouVJS8hHBSulnr2CmhnDktB8fOO9TWxW55JUbGSk4CancrBlb-sJSOpQ5Dkmv63F1mbydxXgpi44The5rMaIHXbtl3k1wfVg7xgvMt81UD68wV7l2aOXE9qTj8e7D-EUnFxJSKgawk_N8D2a71B5-DXS8kbY9Nq83ktfMEXRzyAZIDRvu9-uFVbENwidK4S0cdcjqzzAevvyXB1VhhoPJRL-H3Nv_DzVx_i0YDtuVf-HegRD",
                                    "last_modified": "Sun, 7 Mar 2021 17:28:10 +0000",
                                    "obj_source_id": "1780dbb70a624ae7"}}}
        ], indent=4)
    else:
        # docfind = "call apoc.export.json.query(' \
        #             MATCH (a:Account)--(s:Source)--(p:Parent)--(o:Object) \
        #             with a as acct, s as source, p as parent, collect(o) as doc \
        #             RETURN acct {.name}, source {.name}, parent {.name}, doc {.*} \
        #             ORDER BY acct {.name}, source {.name}, parent {.name}, doc {.name}', \
        #             null, {stream: true, jsonFormat: 'JSON_LINES'})"

        # docfind = "MATCH (a:Account)--(s:Source)--(p:Parent)--(o:Object) \
        #             with a as acct, s as source, p as parent, collect(o) as doc \
        #             RETURN acct {.name}, source {.name}, parent {.name}, doc {.*} \
        #             ORDER BY acct {.name}, source {.name}, parent {.name}, doc {.name} "
        #
        docfind = 'MATCH (a:Account)--(s:Source)--(p:Parent)--(o:Object) \
                    RETURN o.id as id, a.name as account, s.name as source, p.name as parent, o.name as name, \
                    datetime(o.last_modified).epochMillis as mills, \
                    apoc.date.format(datetime(o.last_modified).epochMillis, "ms", "yyyy/MM/dd hh:mm") as modified, \
                    o.mimeType as mimeType, o.shared_to_me as shared_to, o.shared_from_me as shared_from \
                    ORDER BY account, source,  parent, name'

        try:
            # result = emedb.run(docfind)
            with emedb.driver.session() as db:
                result = db.read_transaction(lambda tx: list(tx.run(docfind)))
        except:
            print("Error reading Object list in procedure Finder")
            raise

        # print(f"Result: {result}")
        docs = []
        for record in result:
            docs.append(dict(record))
            # print("dict(record) %s" % dict(record))

    return Response(json.dumps(docs), mimetype="application/json")


def get_gmail_parents(service, ids):
    # for each of the IDs, get the label name and append name to the return list
    plist = []

    for pid in ids:
        try:
            res = session.gmail_service.users().labels().get(userId='me', id=pid).execute()
            plist.append(res['name'].lower())
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
            plist.append(parent['name'].lower())
        except:
            plist.append("No Parent")

    return plist


def tag_source(thisdoc):
    print("in tag_source")

    tlist = []
    lowerdoc = thisdoc.name.lower()
    tlist.extend(re.split("[; ,._\-\%]", lowerdoc))
    tlist.append(thisdoc.modified)
    tlist.append(thisdoc.owner.lower())
    for tag in thisdoc.parents:
        tlist.append(tag.lower())
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
        thelist.append(keyword['parsed_value'].lower())
    return thelist


def scan_gmail_doc(service, thisdoc):
    """ tag scanning for a GMail document

    :service:  the gmail service to use
    :thisdoc: the eme object to work on
    :return: boolean if document is interesting and was scanned
    """
    print(f"Email Scan Doc called: {thisdoc.name}")
    global session

    # print(f"thisdoc is interesting: {thisdoc.interesting()}")
    if thisdoc.interesting():
        thisdoc.source_tags = tag_source(thisdoc)

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
        getKeywords = False  # TODO getKeywords is a flag to skip reading keywords due to API quotas
        if txt and getKeywords:
            thisdoc.content_tags = tag_content(txt)
            # print("Content Taglist are: %s" % thisdoc.content_tags)
        else:
            # TODO Debugging - remove
            maxtags = 50
            txt = txt.replace("'", "")
            tags = txt.split(None, maxtags)
            ltags = [item.lower() for item in tags]
            if len(ltags) > maxtags:
                thisdoc.content_tags = ltags[0:-1]
            else:
                thisdoc.content_tags = ltags[0:]

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
        subject = sender = msgdate = isodate = recipient = ''

        # Look for Subject and Sender Email in the headers
        for d in headers:
            if d['name'] == 'Subject':
                subject = d['value']        # TODO Add sender and subject to source tags
            if d['name'] == 'From':
                sender = d['value']
            if d['name'] == 'Date':
                msgdate = d['value']
                dt = dateutil.parser.parse(msgdate)
                isodate = dt.isoformat()

            if d['name'] == 'To':
                recipient = d['value']

        msg_parts = payload.get('parts')  # fetching the message parts
        for part in msg_parts:
            if 'attachmentId' in part['body']:
                thisdoc = Eme_Object('Gmail Doc', 'Account #1', 'doc', msg['id'] + "|||" + part['partId'],
                                     part['filename'].lower(), isodate, part['mimeType'],
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

    if motivation() == 'getdocs':  # TODO figure out the motivation driver
        interesting += scan_gmail_attachments(session.gmail_service)
        res = json.dumps({'return_code': 'Motivated', 'scan_count': interesting}, indent=4)
    else:
        res = json.dumps({'return_code': 'Not motivated', 'scan_count': '0'}, indent=4)

    print(res)

    return res


def retrieve_Gdrive_files(service, parent='root', filefilter=None, shared=False):
    """Retrieve a list of File resources.

    Args:
      service: Drive API service instance.
    Returns:
      List of File resources.
      :param service:
      :param parent:
      :param filefilter:
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
        param['q'] = f"trashed = false and '{parent}' in parents and name contains '{filefilter}'"
        param['includeItemsFromAllDrives'] = 'false'
        param['supportsAllDrives'] = 'true'
        param['orderBy'] = 'folder,name'
        param['spaces'] = 'drive'

    xfiles = res = {}
    while True:
        if page_token:
            param['pageToken'] = page_token
        try:
            res = service.files()
            try:
                xfiles = res.list(**param).execute()
            except:
                print("Error with retrieve_gdrive_files - res.list(**param) xfiles: %s" % xfiles)
        except:
            print(f"Error with retrieve_gdrive_files (service.files()) res = {res}")

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

    :param folder_id:
    :param recurse:
    :return: int: count of the number of interesting docs scanned
    """
    interesting = 0
    global session
    if folder_id not in session.scanned_folders:
        print(f"Scan_folder ID: {folder_id}")
        session.scanned_folders.append(folder_id)
        f = retrieve_Gdrive_files(session.drive_service, parent=folder_id, filefilter="", shared=session.shared_view)

        for item in f:
            if '.folder' in item['mimeType']:
                if recurse:
                    if folder_id != item['id']:  # avoid opening the same folder
                        interest = scan_drive_folder(item['id'], recurse)
                        interesting += interest
                continue
            else:
                dt = dateutil.parser.parse(item['modifiedTime'])
                isodate = dt.isoformat()
                shar_to = shar_from = "none"
                shar_doc = item.get('ownedByMe', False)
                if shar_doc:
                    shar_to = 'no'
                    # It's my document then, am I sharing it?
                    shar_out = item.get('shared', False)
                    if shar_out:
                        shar_from = 'yes'
                    else:
                        shar_from = 'no'
                else:
                    shar_to = 'yes'
                    shar_from = 'no'



                thisdoc = Eme_Object('Google Drive', 'Account #1', 'doc', item['id'], item['name'], isodate,
                                     item['mimeType'], item.get('parents', ['its empty']),
                                     item['owners'][0].get('displayName', 'none'),
                                     shar_to, shar_from)
                # item['mimeType'], item['parents'], item['owners'][0].get('displayName', 'none'))
                thisdoc.parents = get_gdrive_parents(session.drive_service, thisdoc.parent_ids)
                if scan_drive_doc(thisdoc):
                    interesting += 1
                # print(f"ID; {item['id']}, \t {item['name']}")
    else:
        # we have seen this folder already - do nothing
        pass
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
        getKeywords = False  # TODO getKeywords is a flag to skip reading keywords due to API quotas
        if txt and getKeywords:
            thisdoc.content_tags = tag_content(txt)
            # print("Content Taglist are: %s" % thisdoc.content_tags)
        else:
            # TODO Debugging - remove
            maxtags = 50
            txt = txt.replace("'", "")
            tags = txt.split(None, maxtags)
            ltags = [item.lower() for item in tags]
            ltags = list(set(ltags) - set(STOPWORDS))
            if len(tags) > maxtags:
                thisdoc.content_tags = ltags[0:-1]
            else:
                thisdoc.content_tags = ltags[0:]

        # TODO Add in ability to include user tags - may need rules on when to apply them
        thisdoc.save()
        return True
    else:
        return False


def gdrive_scanner():
    """Scan all documents request from the UI

    :return: int - count of documents scanned
    """

    global session
    if motivation() == 'getdocs':
        session.resetpath()
        session.shared_view = False
        session.scanned_folders = []
        interesting = 0
        interesting += scan_drive_folder(session.path_id[0], recurse=True)
        session.resetpath()
        session.shared_view = True
        session.scanned_folders = []
        interesting += scan_drive_folder(session.path_id[0], recurse=True)

        result = json.dumps({'return_code': 'Motivated', 'scan_count': interesting}, indent=4)
    else:
        result = json.dumps({'return_code': 'Not motivated', 'scan_count': '0'}, indent=4)
    return result


def get_session_vars():
    # TODO Refactor and move to the Session Object as a method
    global session
    return {'name': session.name, 'dbstatus': session.dbstatus, 'account': session.account}


def connect_btn():
    print("in connect_btn")
    global session

    # Connect to 3 services - GDrive, Gdocs, Gmail
    # and also returns Account owner information
    # TODO refactor this into separate connect modules then loop through all of the accounts in the database

    session.setacct('Account #1')  # TODO get this from the database

    # GDrive Service
    accountID = session.account  # TODO get this from the database
    sourceName = 'Google Drive'  # TODO get this from the database

    creds = get_saved_credentials(accountID, sourceName)
    if not creds:
        creds = get_credentials_via_oauth(accountID, sourceName, filename='Credentials.json', scopes=DriveSCOPES)

    drive = get_service(creds, 'drive', 'v3')
    session.setcreds(creds)     # TODO - confirm I dont need this and drop
    session.setdrive(drive)

    gdocs = get_service(creds, 'docs', 'v1')
    session.setdoc(gdocs)

    sourceName = 'Gmail Doc'  # TODO get this from the database

    creds = get_saved_credentials(accountID, sourceName)
    if not creds:
        creds = get_credentials_via_oauth(accountID, sourceName, filename='Credentials.json', scopes=GmailSCOPES)

    gmaildocs = get_service(creds, 'gmail', 'v1')
    session.setgmail(gmaildocs)

    # try:
    #     service = build('drive', 'v3', credentials=session.creds)
    # except:
    #     print(f"Failed to setup the Drive Service ({error}) - Session.creds = {session.creds}")
    # # http = session.creds.authorize(Http())
    #
    # # GDocs Service
    # docs_service = discovery.build(
    #     'docs', 'v1', http=http, discoveryServiceUrl=DISCOVERY_DOC)
    # session.setdoc(docs_service)

    # GMail Service
    # creds = None
    # The file gmail.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    # pkl = None
    # if os.path.exists('gmail.pickle'):
    #     with open('gmail.pickle', 'rb') as token:
    #         pkl = pickle.load(token)
    # # If there are no (valid) credentials available, let the user log in.
    # if not pkl or not pkl.valid:
    #     if pkl and pkl.expired and pkl.refresh_token:
    #         pkl.refresh(Request())
    #     else:
    #         flow = InstalledAppFlow.from_client_secrets_file(
    #             'gmailCredentials.json', GmailSCOPES)
    #         pkl = flow.run_local_server(port=0)
    #     # Save the pickle for the next run
    #     with open('gmail.pickle', 'wb') as token:
    #         pickle.dump(pkl, token)
    #
    # gmail_service = build('gmail', 'v1', credentials=pkl)
    # Call the Gmail API to get labels

    # results = gmaildocs.users().labels().list(userId='me').execute()
    # labels = results.get('labels', [])
    # print(f"labels: {json.dumps(labels, indent=4)}")

    # Account Owner Information
    varlist = get_session_vars()

    return json.dumps(varlist, indent=4)
    # jsonify(status=session.dbstatus, account=session.account, name=session.name)
    # render_template('docTagger.html', varlist=VARLIST)


def doc_reader(shared=False):
    # read the list of documents from the current directory settings
    filelist = [{'id': '1', 'name': 'file #1', 'type': 'third file'},
                {'id': '2', 'name': 'file #2', 'type': 'type 3'}]  # debugging
    filelist = []  # debugging
    print(f"in doc_reader {shared}")  # TODO doc_reader remove this
    global session
    session.resetpath()  # set back to root (shared will have to test for this)

    if shared:
        session.set_shared_view(True)
        try:
            files = retrieve_Gdrive_files(session.drive_service, parent=session.path_id[0], filefilter="", shared=shared)
        except:
            print("Doc_Reader retrieve error - for shared Docs - ending")
            return
    else:
        session.set_shared_view(False)
        thisdir = session.path_id[len(session.path_id) - 1]  # TODO doc_reader will always be at root
        files = retrieve_Gdrive_files(session.drive_service, parent=thisdir, filefilter="", shared=shared)
    if files:
        print("File Count: %s" % len(files))  # TODO doc_reader remove this

    if files:
        testDocCount = 30  # TODO - take this out
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
        if len(result) == 0:
            tags = [{'tag': 'No Tags'}]
        else:
            for record in result:
                tags.append(dict(record))
                # print("dict(record) %s" % dict(record))
    else:
        tags = [{'tag': 'No ID'}]

    print(f"in eme.tag_reader {objid}")
    # print(f"taglist is: {taglist}")

    # return json.dumps(result, indent=4)
    return Response(json.dumps(tags), mimetype="application/json")



# #######  GLOBAL DATABASE CONNECTION
try:
    emedb = EmeGraph("bolt://localhost:7687", "eme", "eme")  # TODO put the database creds in encrypted file
    print("************** Connected to the eMe database")
    emedb.confirm_required_objects()

except:
    sys.exit("************** Error connecting to the eMe database")

# ##  SETUP SESSION OBJECT
nameq = "match(o:EME_Owner) return o.name as name"
with emedb.driver.session() as db:
    result = db.read_transaction(lambda tx: list(tx.run(nameq)))

oname = None
for record in result:
    oname = dict(record)['name']
session = Eme_Session(oname, 'Not Connected', 'Connected', None)
