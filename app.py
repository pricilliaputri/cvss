from flask import Flask, jsonify, request, flash, session
import jwt
import datetime
import mysql.connector
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import io
import os
import traceback
import json
import re
import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import timedelta, datetime
from functools import wraps
from tensorflow import keras
from PIL import Image
from io import BytesIO
# from google.cloud import storage


app = Flask(__name__)


# Load custom model
model = tf.keras.models.load_model(('modelVgg19.h5'), compile=False, custom_objects={'KerasLayer': hub.KerasLayer})

# Load custom model
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "keyys.json"


# Koneksi ke Google Cloud Storage
# storage_client = storage.Client()
# bucket_name = 'bucket-skinny'
# bucket = storage_client.get_bucket(bucket_name)


app.config['SECRET_KEY'] = 'WeArEcViSsIoNs'


CORS(app)

app.config['SESSION_PERMANENT'] = True
app.config['MYSQL_HOST'] = '34.41.67.101'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123'
app.config['MYSQL_DB'] = 'cvis'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

def check_mysql_connection():
    try:
        conn = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )
        return conn
    except mysql.connector.Error as err:
        print("Error connecting to MySQL:", err)
        return None

db_conn = None
while db_conn is None:
    db_conn = check_mysql_connection()
    if db_conn is None:
        print("Waiting for MySQL connection...")
        time.sleep(1)

print("Connected to MySQL!")

# Baca data dari file class.json
# global class_names

# with open('kelas.json', 'r') as json_file:
#     class_names = json.load(json_file)

class_names = {'0':'Katarak','1':'Normal'}


@app.route('/', methods=['GET'])
def index():
    return "Hello"


@app.route('/register', methods=['POST'])
def register():
    if 'username' not in session:
        try:
            _name = request.form['name']
            _username = request.form['username']
            _password = request.form['password']

            if _username and _password:
                _name = re.sub(r'"', '', _name)
                _username = re.sub(r'"', '', _username)
                _password = re.sub(r'"', '', _password)

                cursor = db_conn.cursor()

                sql = "SELECT * FROM user WHERE username=%s"
                sql_values = (_username,)

                cursor.execute(sql, sql_values)
                row = cursor.fetchone()
                if row:
                    resp = jsonify({'Error': True, 'message': 'you already have an account'})

                    return resp
                else:
                    passhash = generate_password_hash(_password)
                    sql = "INSERT INTO user (name, username, password) VALUES (%s, %s, %s)"
                    sql_values = (_name, _username, passhash)
                    cursor.execute(sql, sql_values)
                    db_conn.commit()
                    token = jwt.encode({
                            'user': _username,
                            'expiration': str(datetime.utcnow() + timedelta(days=365))
                    },
                    app.config['SECRET_KEY'])

                    sql = "INSERT INTO token (username, token) VALUES (%s, %s) ON DUPLICATE KEY UPDATE token=%s"
                    sql_values = (_username, token, token)
                    cursor.execute(sql, sql_values)
                    db_conn.commit()
                    cursor.close()

                    return jsonify({'Error': False, 'message': 'You are registered successfully','token': token})

            else:
                resp = jsonify({'Error': True, 'message': 'invalid credentials'})

                return resp
        except:
            resp = jsonify({'Error': True, 'message': 'please fill the form correctly'})

            return resp
    else:
        resp = jsonify({'Error': True, 'message': 'already logged in'})

        return resp


@app.route('/login', methods=['POST'])
def login():
    if 'username' in session and session['username'] is not None:
        resp = jsonify({'Error': True, 'message': 'already logged in'})
        return resp
    else:
        try:
            _username = request.form['username']
            _password = request.form['password']

            if _username and _password:
                _username = re.sub(r'"', '', _username)
                _password = re.sub(r'"', '', _password)


                db_conn = None
                while db_conn is None:
                    db_conn = check_mysql_connection()
                    if db_conn is None:
                        print("Waiting for MySQL connection...")
                        time.sleep(1)
                cursor = db_conn.cursor()
                sql = "SELECT token FROM token WHERE username=%s"
                sql_where = (_username,)

                cursor.execute(sql, sql_where)
                row = cursor.fetchone()
                token = row[0]


                sql = "SELECT * FROM user WHERE username=%s"
                sql_values = (_username,)

                cursor.execute(sql, sql_values)
                row = cursor.fetchone()
                if row is not None:
                    name = row[0]
                    username = row[1]
                    password = row[2]
                    if check_password_hash(password, _password):
                        session['username'] = username
                        cursor.close()
                        return jsonify({'Error': False, 'message': 'You are logged in successfully', 'Your Username': username,'Your Name': name,'token': token})

                    else:
                        resp = jsonify({'Error': True, 'message': 'invalid password'})

                        return resp
                else:
                    resp = jsonify({'Error': True, 'message': 'username is not found'})

                    return resp
            else:
                resp = jsonify({'Error': True, 'message': 'please fill the form correctly'})
                return resp
        except Exception as e:
            resp = jsonify({'Error': True, 'message': 'invalid credentials'})
            # resp.status_code = 400
            print(f"Error: {e}")
            traceback.print_exc()
            return resp



@app.route('/logout', methods=['POST'])
def logout():
    username = request.form['username']
    # Kode untuk melakukan pengecekan ke database
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user WHERE username = %s", (username,))
    result = cursor.fetchone()[0]
    cursor.close()

    if result > 0 and 'username' in session:
        session.clear()

        # Tambahkan pesan ke session
        session['logout_message'] = 'Anda telah berhasil logout.'
        return jsonify({'error': False, 'message': 'Logout Sukses'}),200
    else:
        return jsonify({'error': True, 'message': 'Logout Gagal, login terlebih dahulu'})


def load_and_preprocess_image(img_file):
    """
    Load an image file and preprocess it for VGG19 model.
    """
    img = Image.open(img_file)
    img = img.resize((224, 224))
    img_array = image.img_to_array(img)
    img_array_expanded_dims = np.expand_dims(img_array, axis=0)
    return preprocess_input(img_array_expanded_dims)

def predict_cataract(model, preprocessed_image):
    """
    Predict whether the image is normal or has cataract.
    """
    prediction = model.predict(preprocessed_image)
    if prediction[0][0] > 0.5:
        return "Katarak"
    else:
        return "Normal"

@app.route("/predict", methods=["POST"])
def predict_api():
    token = request.form['token']
    token = re.sub(r'"', '', token)
    cursor = db_conn.cursor()
    sql = "SELECT * FROM token WHERE token=%s"
    sql_where = (token,)

    cursor.execute(sql, sql_where)
    row = cursor.fetchone()
    if not row:
        value = {
            'Error': True,
            "message": 'Token tidak valid'
        }
        return jsonify(value)

    file = request.files['file']
    if 'file' not in request.files:
        value = {
            'Error': True,
            "message": 'Tidak ada file'
        }
        return jsonify(value)


    preprocessed_image = load_and_preprocess_image(file)

    result = predict_cataract(model, preprocessed_image)

    response = {
        'Error': False,
        'message': "Sukses",
        'Prediction': result
    }
    return jsonify(response)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        if file:
            img_path = os.path.join('uploads', file.filename)
            file.save(img_path)
            preprocessed_image = load_and_preprocess_image(img_path)
            result = predict_cataract(model, preprocessed_image)
            return result
    return '''
    <!doctype html>
    <title>Upload Image</title>
    <h1>Upload image to predict cataract</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

if __name__ == '__main__':
    app.run(debug=True, port=1212)
