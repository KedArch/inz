#!/usr/bin/env python3
import sys
import json
import requests

api_endpoint = "http://127.0.0.1:9000/api/"
auth = ('admin', 'admin')
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Accept-Encoding': 'gzip, deflate',
    'X-Requested-By': 'cli',
}

with open('content_pack.json', 'r') as content_pack_file:
    json_data_upload_content_pack = json.loads(content_pack_file.read())

json_data_install_content_pack = {
    'parameters': {},
    'comment': 'Opening 5G Core log input',
}

response = requests.get(
    api_endpoint+'system/content_packs',
    headers=headers,
    auth=auth,
    )

is_uploaded = False
for i in response.json()['content_packs']:
    if i['id'] == json_data_upload_content_pack['id']:
        is_uploaded = True
if not is_uploaded:
    response = requests.post(
        api_endpoint+'system/content_packs',
        headers=headers,
        json=json_data_upload_content_pack,
        auth=auth,
    )
    if response.status_code != 201:
        print('Error occured when uploading content_pack', json_data_upload_content_pack['name'])
        print(response.status_code, response.reason)
        sys.exit(0)
    else:
        print('Successfully uploaded content pack', json_data_upload_content_pack['name'])
else:
    print('Content pack', json_data_upload_content_pack['name'], 'is already uploaded')

if json_data_upload_content_pack['id'] in response.json()['content_packs_metadata']:
    print('Content pack', json_data_upload_content_pack['name'], 'already installed')
else:
    response = requests.post(
        api_endpoint+'system/content_packs/bdcf3632-8426-48bd-bedc-7607865953b9/1/installations',
        headers=headers,
        json=json_data_install_content_pack,
        auth=auth,
    )
    if response.status_code != 200:
        print('Error occured when installing content_pack', json_data_upload_content_pack['name'])
        print(response.status_code, response.reason)
        sys.exit(0)
    else:
        print('Successfully installed content pack', json_data_upload_content_pack['name'])
