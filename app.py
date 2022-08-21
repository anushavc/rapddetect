from flask import Flask, render_template, request, url_for, redirect, session
import pymongo
import bcrypt
import os
import cv2
import os
import cv2
import urllib
import glob
from camera import VideoCamera
import numpy as np
from werkzeug.utils import secure_filename
from urllib.request import Request, urlopen
from flask import Flask, render_template, Response, request, redirect, flash, url_for


app = Flask(__name__)
app.secret_key = "testing"
client = pymongo.MongoClient("mongodb+srv://anusha:anusha@cluster0.pvpfxmy.mongodb.net/?retryWrites=true&w=majority")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

UPLOAD_FOLDER = 'static/uploads/'
DOWNLOAD_FOLDER='static/return/'
VIDEO_FOLDER='static/videos/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

#app configurations
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['VIDEO_FOLDER'] = VIDEO_FOLDER

db = client.get_database('total_records')
records = db.register
images=client.get_database('images')

def gen(camera):
    "" "Helps in Passing frames from Web Camera to server"""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


def allowed_file(filename):
    """ Checks the file format when file is uploaded"""
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS)

#register
@app.route("/", methods=['post', 'get'])
def index():
    message = ''
    if "email" in session:
        return redirect(url_for("logged_in"))
    if request.method == "POST":
        user = request.form.get("fullname")
        email = request.form.get("email")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        user_found = records.find_one({"name": user})
        email_found = records.find_one({"email": email})
        if user_found:
            message = 'There already is a user by that name'
            return render_template('index.html', message=message)
        if email_found:
            message = 'This email already exists in database'
            return render_template('index.html', message=message)
        if password1 != password2:
            message = 'Passwords should match!'
            return render_template('index.html', message=message)
        else:
            hashed = bcrypt.hashpw(password2.encode('utf-8'), bcrypt.gensalt())
            user_input = {'name': user, 'email': email, 'password': hashed}
            records.insert_one(user_input)
            user_data = records.find_one({"email": email})
            new_email = user_data['email']
            return render_template('logged_in.html', email=new_email)
    return render_template('index.html')


#login
@app.route("/login", methods=["POST", "GET"])
def login():
    message = 'Please login to your account'
    if "email" in session:
        return redirect(url_for("logged_in"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        email_found = records.find_one({"email": email})
        if email_found:
            email_val = email_found['email']
            passwordcheck = email_found['password']
            if bcrypt.checkpw(password.encode('utf-8'), passwordcheck):
                session["email"] = email_val
                return redirect(url_for('logged_in'))
            else:
                if "email" in session:
                    return redirect(url_for("logged_in"))
                message = 'Wrong password'
                return render_template('login.html', message=message)
        else:
            message = 'Email not found'
            return render_template('login.html', message=message)
    return render_template('login.html', message=message)

@app.route('/video_feed')
def video_feed():
    """ A route that returns a streamed response needs to return a Response object
    that is initialized with the generator function."""
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

import time
#logged in method
@app.route('/logged_in')
def logged_in():
    if "email" in session:
        email = session["email"]
        return render_template('logged_in.html', email=email)
    else:
        return redirect(url_for("login"))

#logging out method
@app.route("/logout", methods=["POST", "GET"])
def logout():
    if "email" in session:
        session.pop("email", None)
        return render_template("signout.html")
    else:
        return render_template('index.html')

#capturing the video

import gridfs
fs = gridfs.GridFS(images)


import time
@app.route('/takeimage', methods=['POST'])
def takeimage():
    #the email id of the logged in session
    print(session["email"])
    video = cv2.VideoCapture(0)
    if (video.isOpened() == False): 
        print("Error reading video file")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(VIDEO_FOLDER+session["email"]+'filename.avi',fourcc, 20.0, (640,480))
    start_time = time.time()
    #5 seconds duration
    capture_duration = 4
    while( int(time.time() - start_time) < capture_duration ):
        ret, frame = video.read()
        if ret==True:
            frame = cv2.flip(frame,1)
            out.write(frame)
            cv2.imshow('frame',frame)
        else:
            break
    video.release()
    out.release()
    cv2.destroyAllWindows() 
    print("The video was successfully saved")
    vidcap = cv2.VideoCapture(VIDEO_FOLDER+session["email"]+'filename.avi')
    count = 0
    success = True
    fps = int(vidcap.get(cv2.CAP_PROP_FPS))
    #add images to the database
    #imageids
    imageid=[]
    while success:
        success,image = vidcap.read()
        print('read a new frame:',success)
        if count%(1*fps) == 0 :
            cv2.imwrite(UPLOAD_FOLDER+'/frame%d.jpg'%count,image)
            file = UPLOAD_FOLDER+'/frame%d.jpg'%count
            with open(file, 'rb') as f:
                contents = f.read()
            id=fs.put(contents, filename="file"+session["email"])
            imageid.append(id)
        count+=1
    filelist = glob.glob(os.path.join(DOWNLOAD_FOLDER, "*"))
    for f in filelist:
        os.remove(f)
    #calling the images from the database
    for i in imageid:
        outputdata =fs.get(i).read() 
        outfilename = DOWNLOAD_FOLDER+'%s.jpg'%str(i)
        output= open(outfilename,"wb")
        output.write(outputdata)
    #fetching the images from return directory
    basepath =DOWNLOAD_FOLDER
    dir = os.walk(basepath)
    file_list = []
    for path, subdirs, files in dir:
        for file in files:
            temp = os.path.join(path + '/', file)
            file_list.append(temp)
    return render_template('hello1.html',hists=file_list)



#end of code to run it
if __name__ == "__main__":
  app.run(debug=True)