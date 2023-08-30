import os
import boto3
import json
from hashlib import md5
from datetime import datetime
from bs4 import BeautifulSoup

sandbox = True
if sandbox:
    endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
    preview_url = 'https://workersandbox.mturk.com/mturk/preview'
else:
    endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'
    preview_url = 'https://www.mturk.com/mturk/preview'


client = boto3.client('mturk', 'us-east-1', endpoint_url=endpoint_url)


hit_title = 'Tell us which image caption matches best.'
all_hits = client.list_hits()['HITs']
hits_to_delete = [h for h in all_hits if h['Title'] == hit_title]
for hit in hits_to_delete:
    client.update_expiration_for_hit(
        HITId=hit['HITId'],
        ExpireAt=datetime(2015, 1, 1)
    )
    try:
        client.delete_hit(
            HITId=hit['HITId']
        )
    except:
        continue


    
hit_link = 'http://coats.csail.mit.edu:8123/mturk_landing_page.html'


question_xml =  f"""<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
            <ExternalURL>{hit_link}</ExternalURL>
            <FrameHeight>0</FrameHeight>
            </ExternalQuestion>"""

TaskAttributes = {
        'MaxAssignments': 1,                 
        'LifetimeInSeconds': 10*24*60*60,           
        'AssignmentDurationInSeconds': 60*10, 
        'Reward': '0.25',                     
        'Title': hit_title,
        'Keywords': 'image, caption, text',
        'Description': 'Look at an image with two proposed captions and rate which one matches better.',
        'QualificationRequirements': [ # see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/mturk.html
        ]
    }

with open('compare_new.html', 'r') as f:
    html = str(BeautifulSoup(f.read(), 'html'))

with open('experiment_states.html', 'r') as f:
    exp_states = str(BeautifulSoup(f.read(), 'html'))

with open('experiment_screen.html', 'r') as f:
    exp_screen = str(BeautifulSoup(f.read(), 'html'))

with open('mturk_landing_page_new.html', 'r') as f:
    landing = str(BeautifulSoup(f.read(), 'html'))
    
link_id = "eeb92b12fd"
task_file = 'data/comparison_tasks.json'

with open(task_file, 'r') as f:
    task_file = json.load(f)
experiment_data = task_file[link_id]

# exp_screens = ''
# for i, d in enumerate(experiment_data):

#     image = d['image']
#     if not os.path.exists(os.path.join('images', image)):        
#         cls = image.split('/')[0]
#         os.makedirs(f'images/{cls}', exist_ok=True)
#         os.system(f'rsync -r /storage/dmayo2/datasets/objectnet/objectnet_released/objectnet-1.0/images/{image} images/{image}' )

#     exp_string = exp_screen.replace('${TASK_NUM}', str(i))
#     exp_string = exp_string.replace('${TOTAL_TASKS}', str(len(experiment_data)))
#     exp_string = exp_string.replace('${IMAGE_PATH}', os.path.join('images', image))
#     exp_string = exp_string.replace('${CAPTION_1_TEXT}', d['c1_text'])
#     exp_string = exp_string.replace('${CAPTION_2_TEXT}', d['c2_text'])

#     exp_screens += exp_string
#     exp_screens += '\n'

    
# # question_html = question_html.replace('{$TASK_FILE}', str(task_file))



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
  <form name='mturk_form' method='post' id='mturk_form' action='https://www.mturk.com/mturk/externalSubmit'>
  <input type='hidden' value='' name='assignmentId' id='assignmentId'/>
  <h1>What's up?</h1>
  <p><textarea name='comment' cols='80' rows='3'></textarea></p>
  <p><input type='submit' id='submitButton' value='Submit' /></p></form>
  <script language='Javascript'>turkSetAssignmentID();</script>
 </body>
</html>
]]>
  </HTMLContent>
  <FrameHeight>450</FrameHeight>
</HTMLQuestion>
"""



done_code = str(md5(link_id.encode('utf-8')))[0:4];
question_html = question_html.replace('${HIT_Link}', hit_link)
question_html = question_html.replace('${LINK}', link_id)
question_html = question_html.replace('${EXPERIMENT_DATA}', str(experiment_data))
question_html = question_html.replace('${DONE_CODE}', str(done_code))


#hit = client.create_hit(**TaskAttributes,Question=question_xml)
hit = client.create_hit(**TaskAttributes,Question=question_html)

hit_type_id = hit['HIT']['HITTypeId']
print("You can view the HITs here:")
print(preview_url + "?groupId={}".format(hit_type_id))
print(' ')



