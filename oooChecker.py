import os
import requests
import json
import base64
from flask import abort, Flask, jsonify, request
from rq import Queue
from worker import conn


app = Flask(__name__)

def IsRequestValid(request):
    isTokenValid = request.form['token'] == os.environ.get('VALID_TOKEN')
    isTeamIdValid = request.form['team_id'] == os.environ.get('TEAM_ID')

    return isTokenValid and isTeamIdValid

def GetChanellHistory(responseUrl, userId):
    oooHistoryString = ""
    BOT_TOKKEN = os.environ.get('BOT_TOKEN')
    OOO_CHANNEL_ID = os.environ.get('OOO_CHANNEL_ID')

    payload = {"token": BOT_TOKKEN, "channel": OOO_CHANNEL_ID}
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    
    while True:
        response = requests.get('https://slack.com/api/conversations.history', params=payload, headers=headers)
        allDict = json.loads(response.text)
        
        for messageItem in allDict["messages"]:
            if "user" in messageItem and messageItem["user"] == userId:
                if "thread_ts" in messageItem:
                    threadPayload = {"token": BOT_TOKKEN, "channel": OOO_CHANNEL_ID, "ts": messageItem["thread_ts"]}
                    threadResponse = requests.get('https://slack.com/api/conversations.replies', params=threadPayload, headers=headers)
                    threadDict = json.loads(threadResponse.text)

                    for threadItem in threadDict["messages"]:
                        if "user" in threadItem and threadItem["user"] == userId:
                            oooHistoryString = PrintItem(threadItem, oooHistoryString)

                else:
                    oooHistoryString = PrintItem(messageItem, oooHistoryString)
        
        if allDict["has_more"] == True:
            payload['cursor'] = allDict["response_metadata"]["next_cursor"]    
        else:
            break

    attachmentsDict = {}
    attachmentsDict['title'] = "Here comes your OoO history."
    attachmentsDict['text'] = oooHistoryString

    SendMessageToSlack(attachmentsDict, responseUrl)            
    
def PrintItem(messageItem, oooHistoryString):
    oooHistoryString += messageItem['text']
    oooHistoryString += "\n\n" 
    return oooHistoryString

def SendMessageToSlack(attachment, url):
    payload = {}
    payload['text'] = 'Get OoO History'
    payload['attachments'] = []
    payload['attachments'].append(attachment)
    payload['response_type'] = 'ephemeral'

    payloadResult = json.dumps(payload);
    headers = {'Content-type': 'application/json', 'charset': 'UTF-8'}

    result = requests.post(url, data=payloadResult, headers=headers)
    print(result.text)

def QueingJob():
    q = Queue(connection=conn)
    result = q.enqueue(GetChanellHistory, request.form['response_url'], request.form['user_id'])
    print(result)

@app.route('/', methods=['POST'])
def OOOMe():
    if not IsRequestValid(request):
        abort(400)

    # GetChanellHistory(request.form['response_url'], request.form['user_id'])
    QueingJob()

    return jsonify(response_type='ephemeral', text="Check %s's ooo history:fast_parrot:" % request.form['user_name'])   

# ooo channel id C4DRJAA0Y
