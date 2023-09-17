import logging
import time

import requests
import base64
import json
import warnings
import os

from typing import Dict

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter, Retry


def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8'))

class ChangeRequest:
  def __init__(self, changeRequestNumber, changeRequestURL, assignmentGroup, assignee, shortDescription, scheduledTime, state):
    self.changeRequestNumber = changeRequestNumber
    self.changeRequestURL = changeRequestURL
    self.assignmentGroup = assignmentGroup
    self.assignee = assignee
    self.shortDescription = shortDescription
    self.scheduledTime = scheduledTime
    self.state = state
class AccessToken:
    """
    retrieve a freshly minted access token given the client key and client secret information
    """
    TOKEN_URL = ""

    GRANT_CLIENT_CRED = 'client_credentials'
    GRANT_PASSWORD = ''

    def __init__(self,
                 consumerKey='',
                 consumerSecret='',
                 grantType=GRANT_CLIENT_CRED,
                 username='',
                 password='',
                 apiTokenUrl=TOKEN_URL):
        self.consumerKey = consumerKey
        self.consumerSecret = consumerSecret
        self.username = username
        self.password = password
        self.grantType = grantType
        self.apiTokenUrl = apiTokenUrl

    def __encodedCred(self):
        return stringToBase64(self.consumerKey + ":" + self.consumerSecret).decode('utf-8')

    def __buildRequest(self, url):

        headerDict = {'Content-Type': 'application/x-www-form-urlencoded',
                      'Authorization': 'Basic ' + self.__encodedCred()
                      }

        data = ""
        if (self.grantType == AccessToken.GRANT_CLIENT_CRED):
            data = "grant_type=client_credentials"
        else:
            data = "grant_type=password&username={}&password={}".format(self.username,
                                                                        self.password)

        #        print("AccessToken:[{}]".format(url))
        request = requests.Request(method='POST',
                                   url=url,
                                   data=data,
                                   headers=headerDict)
        return request.prepare()

    def getAccessToken(self, timeout=4.0):
        session = requests.Session()
        session.verify = False
        request = self.__buildRequest(self.apiTokenUrl)
        response = session.send(request, timeout=timeout)

        response.raise_for_status()

        responseJSON = json.loads(response.text)
        return responseJSON['access_token']

getToken = AccessToken()
headerDict = {'Accept': 'application/json',
              'Content-Type': 'application/x-www-form-urlencoded',
              'Authorization': 'Bearer ' + getToken.getAccessToken(),
              'x-sn-credential': ''
             }
assignmentGroupList = {'GROUP1': [], 
                        'GROUP2': [], 
                        'GROUP3': [], 
                        'GROUP4': [], 
                        'GROUP5': [], 
                        'GROUP6': [], 
                        'GROUP7': [], 
                        'GROUP8': []
                    }
for assignmentGroup in assignmentGroupList.keys():
    url1 = 'query?filter=assignment_group.name=' + assignmentGroup + '^type=Normal^state<-1'
    request = requests.Request(method='GET',
                            url=url1,
                            headers=headerDict)
    request = request.prepare()
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 401, 403, 500, 502, 503 ])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.verify = False
    response = session.send(request, timeout=4.0)
    response.raise_for_status()
    changeRequests = json.loads(response.text)
    if changeRequests['results'] != []:
        for changeRequest in changeRequests['results']:
            changeRequestNumber = changeRequest['number']
            changeRequestURL = '?sysparm_query=number=' + changeRequestNumber
            assignee = changeRequest['assigned_to_id']
            shortDescription = changeRequest['short_description']
            scheduledTime = changeRequest['planned_start_date']
            state = changeRequest['state']
            scheduledDateTime = datetime.strptime(scheduledTime, '%Y-%m-%d %H:%M:%S')
            currentTimePlusTwoHr = datetime.utcnow()+ timedelta(hours=2)
            currentTimePlusOneHr = datetime.utcnow()+ timedelta(hours=1)
            if currentTimePlusTwoHr >= scheduledDateTime >= currentTimePlusOneHr:
                assignmentGroupList[assignmentGroup].append(ChangeRequest(changeRequestNumber, changeRequestURL, assignmentGroup, assignee, shortDescription, scheduledTime, state))
                

for assignmentGroup in assignmentGroupList.keys():
    if assignmentGroupList[assignmentGroup] != []:
        mailBody = ("<br>"
                    "<p><span style='font-family:sans-serif;'>Below change request(s) will be implemented in 2 hours:</span></p>"
                    "<table border='1'>"
                    "<thead>"
                    "<tr>"
                    "<th><span style='font-family:sans-serif;'>Number</span></th>"
                    "<th><span style='font-family:sans-serif;'>State</span></th>"
                    "<th><span style='font-family:sans-serif;'>Assignee</span></th>"
                    "<th><span style='font-family:sans-serif;'>Short Description</span></th>"
                    "<th><span style='font-family:sans-serif;'>Plan Date (UTC+0)</span></th>"
                    "</tr>"
                    "</thead>"
                    "<tbody>")
        recipients = []
        for changeRequest in assignmentGroupList[assignmentGroup]:
            approved = True
            mailBody = mailBody + ("<tr>"
                                    "<td><span style='font-family:sans-serif;'><a href='" + changeRequest.changeRequestURL + "'>" + changeRequest.changeRequestNumber + "</a></span></td>"
                                    )
            if changeRequest.state == 'Scheduled':
                mailBody = mailBody + ("<td><span style='font-family:sans-serif;'>" + changeRequest.state + "</span></td>")
            else :
                mailBody = mailBody + ("<td><span style='font-family:sans-serif;'><font color='red'><b>" + changeRequest.state + "</b></span></td>")
                approved = False
            mailBody = mailBody + ("<td><span style='font-family:sans-serif;'>" + changeRequest.assignee + "</span></td>"
                                    "<td><span style='font-family:sans-serif;'>" + changeRequest.shortDescription + "</span></td>"
                                    "<td><span style='font-family:sans-serif;'><font color='red'>" + changeRequest.scheduledTime+ "</font></span></td>"
                                    "</tr>")
                                    
            recipients.append(changeRequest.assignee + "@")
        mailBody = mailBody + ("</tbody>"
                                    "</table><br>")
        if approved == False:
            mailBody = mailBody + ("<br>"
                                    "<p><span style='font-family:sans-serif;'>For any change request that is not yet approved please reach below people to get it approved depending on the site</span></p>")
        mailBody = mailBody + ("<br>"
                                "<br>"
                                "<br>"
                                "<br>"
                                "<p><span style='font-family:cursive;'><font color='grey'; size='2'>"
                                "</font></span></p>")
                                   
        content = MIMEMultipart()
        content["subject"] = "(Reminder) Change request(s) will be implemented in 2 hours"
        content["from"] = ""
        content["to"] = ", ".join(recipients)
        content["cc"] = assignmentGroup + "@"
        content.attach(MIMEText(mailBody, "html"))

        with smtplib.SMTP(host="") as smtp:
            try:
                smtp.ehlo()
                smtp.starttls()
                smtp.send_message(content)
            except Exception as e:
                print("Error message: ", e)
