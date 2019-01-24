from flask import Flask, jsonify
from flask import request, render_template
from flask_cors import CORS
import json, os, glob, requests
import base64 
from settings import *

app = Flask(__name__)
CORS(app)

annotations = []
@app.route('/annotations/', methods=['POST'])
def create_anno():
    data_object = json.loads(request.data)
    key = data_object['key']
    annotation = data_object['json']
    origin_url = request.headers.get('Referer').strip()
    id = key.split("/")[-1].replace("_", "-").lower()
    
    if github_repo == "":
        filecounter = [name for name in os.listdir(filepath) if id in name]
    else:
        existing_github = requests.get(github_url+"{}".format(filepath), headers={'Authorization': 'token {}'.format(github_token)}).json()
        filecounter = [filedata for filedata in existing_github if id in filedata['name'] ]
    if len(annotation) > 0:
        formated_annotation = {"@context":"http://iiif.io/api/presentation/2/context.json",
        "@type": "sc:AnnotationList", "@id": "%s%s/%s-list.json"% (origin_url, filepath[1:], id) } 
        formated_annotation['resources'] = annotation
        file_path = os.path.join(filepath, id.replace(".json", "").replace(":", ""))
        list_name = "{}-list.json".format(file_path)
        if github_repo == "":
            if len(filecounter) - 1 > len(annotation):
                for file in filecounter:
                    os.remove(os.path.join(filepath, file))
            with open(list_name, 'w') as outfile:
                outfile.write("---\nlayout: null\n---\n")
                outfile.write(json.dumps(formated_annotation))
        else:
            full_url = github_url + "/{}".format(list_name)
            sha = ''
            if len(filecounter) - 1 > len(annotation):
                for file in filecounter:
                    data = {'sha': file['sha'], 'message':'delete'}
                    print(file['url'])
                    response = requests.delete(file['url'], headers={'Authorization': 'token {}'.format(github_token)}, data=json.dumps(data))
            existing = requests.get(full_url, headers={'Authorization': 'token {}'.format(github_token)}).json()
            if 'sha' in existing.keys():
                sha = existing['sha']
            message = "write {}".format(list_name)
            anno_text = "---\nlayout: null\n---\n" + json.dumps(formated_annotation)
            data = {"message":message, "content": base64.b64encode(anno_text)}
            if sha != '':
                data['sha'] = sha
            response = requests.put(full_url, data=json.dumps(data),  headers={'Authorization': 'token {}'.format(github_token)})
            print(response.request.headers)
        index = 1
        for anno in annotation:
            if github_repo == "":
                with open("{}-{}.json".format(file_path, index), 'w') as outfile:
                    outfile.write("---\nlayout: null\n---\n")
                    outfile.write(json.dumps(anno))
            else:
                full_url = github_url + "/{}-{}.json".format(file_path, index)
                existing = requests.get(full_url, headers={'Authorization': 'token {}'.format(github_token)}).json()
                sha = ''
                if 'sha' in existing.keys():
                    sha = existing['sha']
                message = "write {}".format(filepath)
                full_anno = "---\nlayout: null\n---\n" + json.dumps(anno)
                data = {"message":message, "content": base64.b64encode(full_anno)}
                if sha != '':
                    data['sha'] = sha
                response = requests.put(full_url, data=json.dumps(data),  headers={'Authorization': 'token {}'.format(github_token)})
                print(response.request.headers)
            index += 1
        return jsonify(annotation), 201
    else:
        for file in filecounter:
            if github_repo == "":
                os.remove(os.path.join(filepath, file))
            else:
                data = {'sha': file['sha'], 'message':'delete'}
                response = requests.delete(file['url'], headers={'Authorization': 'token {}'.format(github_token)}, data=json.dumps(data))
                print(response.request.headers)
        return jsonify("[]"), 201
    
@app.route('/annotations/', methods=['DELETE'])
def delete_anno():
    delete_path = os.path.join(filepath, request.data) + ".json"
    os.remove(delete_path)
    return "File Removed", 201


if __name__ == "__main__":
    app.run()
