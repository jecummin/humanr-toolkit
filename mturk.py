import os
import boto3
import json
from tqdm import tqdm
from hashlib import md5
from datetime import datetime
from bs4 import BeautifulSoup


def deploy_hits(links, reward, sandbox):
    sandbox = True
    
    global endpoint_url
    global preview_url
    
    if sandbox:
        endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
        preview_url = 'https://workersandbox.mturk.com/mturk/preview'
    else:
        endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'
        preview_url = 'https://www.mturk.com/mturk/preview'

    client = boto3.client('mturk', endpoint_url=endpoint_url)
    

    hit_title = 'Tell us which image caption matches best.'
    TaskAttributes = {
        'MaxAssignments': 1,                 
        'LifetimeInSeconds': 10*24*60*60,           
        'AssignmentDurationInSeconds': 60*10, 
        'Reward': str(reward),
        'Title': hit_title,
        'Keywords': 'image, caption, text',
        'Description': 'Look at an image with two proposed captions and rate which one matches better.',
        'QualificationRequirements': [ # see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/mturk.html
        ]
    }

    with open('mturk_landing_page.html', 'r') as f:
        landing = str(BeautifulSoup(f.read(), 'html'))
    


    environment = 'SANDBOX' if sandbox else 'PRODUCTION'
    print(f'Posting hits to {environment} environment')
    hit_ids = []
    for hit_link in tqdm(links):
        question_html = f"""
        <HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
        <HTMLContent><![CDATA[
        <!DOCTYPE html>
        <html>
        <head>
        <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'/>
        <script type='text/javascript' src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js'></script>
        </head>
        <body>

        {landing}
        
        </body>
        </html>
        ]]>
        </HTMLContent>
        <FrameHeight>450</FrameHeight>
        </HTMLQuestion>
        """
        question_html = question_html.replace('${HIT_Link}', hit_link)
        hit = client.create_hit(**TaskAttributes, Question=question_html)
        hit_ids.append(hit['HIT']['HITId'])

    hit_type_id = hit['HIT']['HITTypeId']
    print()
    print("You can view the HITs here:\n\t")
    print(preview_url + "?groupId={}".format(hit_type_id))

    return preview_url, hit_type_id, hit_ids



def check_hits(hit_ids):
    client = boto3.client('mturk', endpoint_url=endpoint_url)
    all_hits = client.list_hits()['HITs']
    completed = []
    for hit in all_hits:
        # count only HITs just posted for HUMANr
        if hit['HITId'] not in hit_ids:
            continue
        
        if hit['HITStatus'] in ['Reviewable', 'Reviewing']:
            completed.append(hit['HITId'])
    return completed

def expire_hits(hit_ids):
    client = boto3.client('mturk', endpoint_url=endpoint_url)
    all_hits = client.list_hits()['HITs']
    for hit in all_hits:
        # expire only HITs just posted for HUMANr
        if hit['HITId'] not in hit_ids:
            continue
        client.update_expiration_for_hit(
            HITId=hit['HITId'],
            ExpireAt=datetime(2015, 1, 1)
        )
    return 
