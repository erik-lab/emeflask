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
# import lxml
from docx import Document
from neo4j import GraphDatabase
import os

print("CWD 1: %s" % os.getcwd())