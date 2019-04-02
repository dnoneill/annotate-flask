from flask import Flask, jsonify
from flask import request, render_template
from flask_cors import CORS
import json, os, glob, requests
import base64
from settings import *
from bs4 import BeautifulSoup
import yaml

app = Flask(__name__)
CORS(app)

annotations = []
@app.route('/annotations/', methods=['POST'])
def create_anno():
    data_object = json.loads(request.data)
    print(data_object['key'])
    key = data_object['key'].lower()
    print(key)
    annotation = data_object['json']
    origin_url = data_object['originurl']
    if github_repo == "":
        filecounter = [name for name in os.listdir(filepath) if id in name]
    else:
        existing_github = requests.get(github_url+"{}".format(filepath), headers={'Authorization': 'token {}'.format(github_token)}).json()
        filecounter = [filedata for filedata in existing_github if id in filedata['name'] ]
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
            with open(list_name, 'w') as outfile:
                outfile.write("---\nlayout: null\n---\n")
                outfile.write(json.dumps(formated_annotation))
        else:
            full_url = github_url + "/{}".format(list_name)
            sha = ''
            #if len(filecounter) - 1 > len(annotation):
            #    for file in filecounter:
            #        data = {'sha': file['sha'], 'message':'delete'}
            #        response = requests.delete(file['url'], headers={'Authorization': 'token {}'.format(github_token)}, data=json.dumps(data))
            existing = requests.get(full_url, headers={'Authorization': 'token {}'.format(github_token)}).json()
            if 'sha' in existing.keys():
                sha = existing['sha']
            message = "write {}".format(list_name)
            anno_text = "---\nlayout: null\n---\n" + json.dumps(formated_annotation)
            data = {"message":message, "content": base64.b64encode(anno_text)}
            if sha != '':
                data['sha'] = sha
            if 'content' in existing.keys():
                existing_anno = json.loads(base64.b64decode(existing['content']).replace("---\nlayout: null\n---\n", ""))
                if (formated_annotation != existing_anno):
                    response = requests.put(full_url, data=json.dumps(data),  headers={'Authorization': 'token {}'.format(github_token), 'charset': 'utf-8'})
            else:
                response = requests.put(full_url, data=json.dumps(data),  headers={'Authorization': 'token {}'.format(github_token), 'charset': 'utf-8'})
        index = 1
        for anno in annotation:
            imagescr = '<iiif-annotation annotationurl="{}/{}-{}.json" styling="image_only:true"></iiif-annotation>'.format(origin_url, file_path.replace("_", ""), index)
            annodata_data = {'tags': [], 'layout': 'searchview', 'listname': list_name.split("/")[-1], 'content': [],
                'imagescr': imagescr}
            annodata_filename = "{}-{}.md".format(id.replace(".json", "").replace(":", ""), index)
            textdata = anno['resource'] if 'resource' in anno.keys() else [anno['body']]
            for resource in textdata:
                chars = BeautifulSoup(resource['chars'], 'html.parser').get_text() if 'chars' in resource.keys() else ''
                if chars and 'tag' in resource['@type'].lower():
                    annodata_data['tags'].append(chars.encode("utf-8"))
                elif chars:
                    annodata_data['content'].append(chars.encode("utf-8"))
                else:
                    annodata_data['content'].append(resource['value'])
            content = '\n'.join(annodata_data.pop('content'))
            if github_repo == "":
                with open(os.path.join("_annotation_data", annodata_filename), "w") as outfile:
                    outfile.write("---\n")
                    outfile.write(yaml.dump(annodata_data))
                    outfile.write("---\n")
                    outfile.write(content)
                with open("{}-{}.json".format(file_path, index), 'w') as outfile:
                    outfile.write("---\nlayout: null\n---\n")
                    outfile.write(json.dumps(anno))
            else:
                full_url = github_url + "/{}-{}.json".format(file_path, index)
                filename= "{}-{}.md".format(id.replace(".json", "").replace(":", ""), index)
                annotationdata_url = github_url + "/{}".format(os.path.join("_annotation_data", annodata_filename))
                existing = requests.get(full_url, headers={'Authorization': 'token {}'.format(github_token)}).json()
                existing_annodata = requests.get(annotationdata_url, headers={'Authorization': 'token {}'.format(github_token)}).json()
                sha = ''
                anno_sha = ''
                if 'sha' in existing.keys():
                    sha = existing['sha']
                if 'sha' in existing_annodata.keys():
                    anno_sha = existing_annodata['sha']
                message = "write {}-{}.json".format(file_path, index)
                full_anno = "---\nlayout: null\n---\n" + json.dumps(anno)
                annodata_message = "write {}".format(os.path.join("_annotation_data", filename))
                data = {"message":message, "content": base64.b64encode(full_anno)}
                annodata_yaml = "---\n{}---\n{}".format(yaml.dump(annodata_data), content)
                annodata_data = {"message":annodata_message, "content": base64.b64encode(annodata_yaml)}
                if sha != '':
                    data['sha'] = sha
                if anno_sha != '':
                    annodata_data['sha'] = anno_sha
                if 'content' in existing_annodata.keys():
                    if base64.b64decode(existing_annodata['content']) != annodata_yaml:
                        response = requests.put(annotationdata_url, data=json.dumps(annodata_data),  headers={'Authorization': 'token {}'.format(github_token), 'charset': 'utf-8'})
                else:
                    response = requests.put(annotationdata_url, data=json.dumps(annodata_data),  headers={'Authorization': 'token {}'.format(github_token), 'charset': 'utf-8'})
                if 'content' in existing.keys():
                    existing_anno = json.loads(base64.b64decode(existing['content']).replace("---\nlayout: null\n---\n", ""))
                    if (anno != existing_anno):
                        response = requests.put(full_url, data=json.dumps(data),  headers={'Authorization': 'token {}'.format(github_token), 'charset': 'utf-8'})
                else:
                    response = requests.put(full_url, data=json.dumps(data),  headers={'Authorization': 'token {}'.format(github_token), 'charset': 'utf-8'})
            index += 1
        return jsonify(annotation), 201
    else:
        for file in filecounter:
            if github_repo == "":
                os.remove(os.path.join(filepath, file))
            #else:
            #    data = {'sha': file['sha'], 'message':'delete'}
            #    response = requests.delete(file['url'], headers={'Authorization': 'token {}'.format(github_token)}, data=json.dumps(data))
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
        try:
            delete_path = os.path.join(filepath, id) + ".json"
            os.remove(delete_path)
        except:
            print('already removed')
        search_path = os.path.join('_annotation_data', id) + ".md"
        os.remove(search_path)
        if request_data['deletelist']:
            list_path = os.path.join(filepath, listid)
            os.remove(list_path)
        return "File Removed", 201


if __name__ == "__main__":
    app.run()
