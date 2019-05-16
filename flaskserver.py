from flask import Flask, jsonify
from flask import request, render_template
from flask_cors import CORS
import json, os, glob, requests
import base64
from settings import *
from bs4 import BeautifulSoup
import yaml
import re

app = Flask(__name__)
CORS(app)

annotations = []
@app.route('/annotations/', methods=['POST'])
def create_anno():
    data_object = json.loads(request.data)
    id = data_object['key'].lower()
    annotation = data_object['json']
    origin_url = data_object['originurl'].replace("http://0.0.0.0:5555", "")
    if github_repo == "":
        filecounter = [name for name in os.listdir(filepath) if bool(re.compile(r"^{}".format(id)).match(name))]
    if len(annotation) > 0:
        if 'w3.org' in annotation[0]['@context']:
            formated_annotation = {"@context":"http://www.w3.org/ns/anno.jsonld",
            "@type": "AnnotationPage", "id": "%s/%s/%s-list.json"% (origin_url, filepath[1:], id) }
        else:
            formated_annotation = {"@context":"http://iiif.io/api/presentation/2/context.json",
            "@type": "sc:AnnotationList", "@id": "%s/%s/%s-list.json"% (origin_url, filepath[1:], id) }
        formated_annotation['resources'] = annotation
        file_path = os.path.join(filepath, id.replace(".json", "").replace(":", ""))
        list_name = "{}-list.json".format(file_path)
        if github_repo == "":
            if len(filecounter) - 1 > len(annotation):
                for file in filecounter:
                    os.remove(os.path.join(filepath, file))
            writetofile(list_name, formated_annotation)
        else:
            writetogithub(list_name, formated_annotation)
        index = 1
        for anno in annotation:
            filename = "{}-{}.json".format(file_path, index)
            annodata_data = get_search(anno, filename)
            if github_repo == "":
                writetofile(filename, anno)
            else:
                writetogithub(filename, anno)
            index += 1
        return jsonify(annotation), 201
    else:
        if github_repo == "":
            for file in filecounter:
                os.remove(os.path.join(filepath, file))
        return jsonify("[]"), 201

@app.route('/annotations/', methods=['DELETE'])
def delete_anno():
    request_data = json.loads(request.data)
    id = request_data['id']
    listid = request_data['id'].rsplit('-',1)[0] + "-list.json"
    if request.data and github_repo:
        existing_github = requests.get(github_url+"/{}/{}.json".format(filepath, id), headers={'Authorization': 'token {}'.format(github_token)}).json()
        existing_search = requests.get(github_url+"/_annotation_data/{}.md".format(id), headers={'Authorization': 'token {}'.format(github_token)}).json()
        data = {'message': 'delete %s' % id, 'sha':existing_github['sha']}
        search_data = {'message': 'delete %s' % id, 'sha':existing_search['sha']}
        requests.delete(github_url+"/{}/{}.json".format(filepath, id), headers={'Authorization': 'token {}'.format(github_token)}, data=json.dumps(data))
        requests.delete(github_url+"/_annotation_data/{}.md".format(id), headers={'Authorization': 'token {}'.format(github_token)}, data=json.dumps(search_data))
        if request_data['deletelist']:
            existing_list = requests.get(github_url+"/{}/{}".format(filepath, listid), headers={'Authorization': 'token {}'.format(github_token)}).json()
            list_data = {'message': 'delete %s' % listid, 'sha':existing_list['sha']}
            requests.delete(github_url+"/{}/{}".format(filepath, listid), headers={'Authorization': 'token {}'.format(github_token)}, data=json.dumps(list_data))
        return "File Removed", 201
    else:
    #    delete_path = os.path.join(filepath, id) + ".json"
    #    exists = os.path.isfile(delete_path)
    #    if exists:
    #        os.remove(delete_path)
        search_path = os.path.join('_annotation_data', id) + ".md"
        exists = os.path.isfile(search_path)
        if exists:
            os.remove(search_path)
    #    if request_data['deletelist']:
    #        list_path = os.path.join(filepath, listid)
    #        os.remove(list_path)
        return "File Removed", 201

@app.route('/write_annotation/', methods=['POST'])
def write_annotation():
    print(request.data)
#    data = json.loads(request.data)
#    json_data = eval(data['json'])
#    if 'list' in json_data['@type'].lower() or 'page' in json_data['@type'].lower():
#        for index, anno in enumerate(json_data['resources'], start=1):
#            get_search(anno, data['filename'].replace('-list.json', '-{}.json'.format(index)))
#    else:
#        get_search(json_data, data['filename'])
#    if github_repo == "":
#        filename = os.path.join('_annotations', data['filename'])
#        writetofile(filename, data['json'])
#
    return request.data

def writetogithub(filename, annotation, yaml=False):
    full_url = github_url + "/{}".format(filename)
    sha = ''
    existing = requests.get(full_url, headers={'Authorization': 'token {}'.format(github_token)}).json()
    if 'sha' in existing.keys():
        sha = existing['sha']
    message = "write {}".format(filename)
    anno_text = annotation if yaml else "---\nlayout: null\n---\n" + json.dumps(annotation)
    data = {"message":message, "content": base64.b64encode(anno_text)}
    if sha != '':
        data['sha'] = sha
    if 'content' in existing.keys():
        existing_anno = json.loads(base64.b64decode(existing['content']).replace("---\nlayout: null\n---\n", ""))
        if (formated_annotation != existing_anno):
            response = requests.put(full_url, data=json.dumps(data),  headers={'Authorization': 'token {}'.format(github_token), 'charset': 'utf-8'})
    else:
        response = requests.put(full_url, data=json.dumps(data),  headers={'Authorization': 'token {}'.format(github_token), 'charset': 'utf-8'})

def writetofile(filename, annotation):
    with open(filename, 'w') as outfile:
        outfile.write("---\nlayout: null\n---\n")
        outfile.write(json.dumps(annotation))

def get_search(anno, filename):
    imagescr = '<iiif-annotation annotationurl="/{}" styling="image_only:true"></iiif-annotation>'.format(filename.replace("_", ""))
    listname = "{}-list.json".format(filename.split("/")[-1].rsplit('-', 1)[0])
    annodata_data = {'tags': [], 'layout': 'searchview', 'listname': listname, 'content': [], 'imagescr': imagescr}
    annodata_filename = os.path.join("_annotation_data", filename.split('/')[-1].replace('.json', '.md'))
    textdata = anno['resource'] if 'resource' in anno.keys() else anno['body']
    textdata = textdata if type(textdata) == list else [textdata]
    for resource in textdata:
        chars = BeautifulSoup(resource['chars'], 'html.parser').get_text() if 'chars' in resource.keys() else ''
        if chars and 'tag' in resource['@type'].lower():
            annodata_data['tags'].append(chars.encode("utf-8"))
        elif 'purpose' in resource.keys() and 'tag' in resource['purpose']:
            tags_data = chars if chars else resource['value']
            annodata_data['tags'].append(tags_data.encode("utf-8"))
        elif chars:
            annodata_data['content'].append(chars.encode("utf-8"))
        else:
            annodata_data['content'].append(resource['value'])
    content = '\n'.join(annodata_data.pop('content'))
    if github_repo == "":
        with open(annodata_filename, "w") as outfile:
            outfile.write("---\n")
            outfile.write(yaml.dump(annodata_data))
            outfile.write("---\n")
            outfile.write(content)
    else:
        annodata_yaml = "---\n{}---\n{}".format(yaml.dump(annodata_data), content)
        writetogithub(annodata_filename, annodata_yaml, True)

if __name__ == "__main__":
    app.run()
