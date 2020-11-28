import os
import simplejson
import traceback
import pandas as pd
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from flask_bootstrap import Bootstrap
from werkzeug import secure_filename
import sys
from lib.upload_file import uploadfile
from lib.analyse import get_competences

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['UPLOAD_FOLDER'] = os.path.dirname(sys.argv[0])+'/data/'
app.config['THUMBNAIL_FOLDER'] = os.path.dirname(sys.argv[0])+'/data/thumbnail/'
app.config['OUTPUT_FOLDER'] = os.path.dirname(sys.argv[0])+'/output/'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['txt', 'pdf','html','doc', 'docx'])
IGNORED_FILES = set(['.gitignore'])
bootstrap = Bootstrap(app)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_file_name(filename):
    """
    If file was exist already, rename it and return a new name
    """
    i = 1
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i += 1
    return filename

@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        files = request.files['file']
        if files:
            filename = secure_filename(files.filename)
            filename = gen_file_name(filename)
            mime_type = files.content_type
            if not allowed_file(files.filename):
                result = uploadfile(name=filename, type=mime_type, size=0, not_allowed_msg="File type not allowed")
            else:
                # save file to disk
                uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                files.save(uploaded_file_path)
                # get file size after saving
                size = os.path.getsize(uploaded_file_path)
                # return json for js call back
                result = uploadfile(name=filename, type=mime_type, size=size)
            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        # get all file in ./data directory
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'],f)) and f not in IGNORED_FILES ]
        file_display = []
        for f in files:
            size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], f))
            file_saved = uploadfile(name=f, size=size)
            file_display.append(file_saved.get_file())

        return simplejson.dumps({"files": file_display})

    return redirect(url_for('index'))


@app.route("/delete/<string:filename>", methods=['DELETE'])
def delete(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            if os.path.exists(file_thumb_path):
                os.remove(file_thumb_path)
            return simplejson.dumps({filename: 'True'})
        except:
            return simplejson.dumps({filename: 'False'})


# serve static files
@app.route("/thumbnail/<string:filename>", methods=['GET'])
def get_thumbnail(filename):
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename=filename)


@app.route("/data/<string:filename>", methods=['GET'])
def get_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename=filename)

@app.route("/view/<string:filename>", methods=['GET'])
def get_predictions(filename):
    if not filename in os.listdir(app.config['UPLOAD_FOLDER']):
        return render_template('404.html')
    try : 
        competences , lo = get_competences(filename)
        mission ,  competences_list = list(lo.keys())[0] ,list(lo.values())[0] 
        competences_list = list(set(competences_list))
        competences.to_csv(app.config['OUTPUT_FOLDER'] +  '.'.join([filename.split('.')[0],'csv']))
        return render_template('fileDetails.html',filename=filename,competences = competences_list , mission = mission )
    except:
        return render_template('404.html')

@app.route("/as_csv/<string:filename>",methods=['GET'])
def download_csv(filename) : 
    return send_from_directory(os.path.join(app.config['OUTPUT_FOLDER']), filename=filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
