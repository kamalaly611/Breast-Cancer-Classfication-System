from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response,jsonify
from flask_mysqldb import MySQL, MySQLdb
from flask_wtf import FlaskForm
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SubmitField, SelectField
from wtforms import Form, BooleanField, StringField, PasswordField, validators
from flask_wtf.file import FileField, FileRequired, DataRequired
#from wtforms.fields.html5 import EmailField, DateTimeLocalField
from wtforms.fields import EmailField, DateTimeLocalField
from passlib.hash import sha256_crypt
from functools import wraps
import os   #To Interact with OS
from tensorflow.keras import models
import uuid     #Generate urls
import smtplib   #For email handling
from flask_mail import Mail, Message
import string
import random
from PIL import Image
import numpy as np
from PIL import Image
import pdfkit
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from tensorflow.keras.preprocessing import image as i1
import cv2



# Set the path to wkhtmltopdf executable
path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

# Configure pdfkit with the specified path
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

# HTML content to be converted to PDF (replace this with your actual content)
html_content = """
<html>
  <body>
    <p>Your HTML content here</p>
  </body>
</html>
"""

# Save the HTML content to a local file
with open("local_page.html", "w", encoding="utf-8") as file:
    file.write(html_content)

# Convert the local HTML file to PDF
pdfkit.from_file("local_page.html", "out.pdf", configuration=config)

app = Flask(__name__)

# Config MYSQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'epca' 
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['INITIAL_FILE_UPLOADS'] = (r'D:\Project\env\static\img\uploads')
# app.config['INITIAL_FILE_UPLOADS'] = (r'env\static\img1')

# config gmail
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']= 587
app.config['MAIL_USE_TLS']= True
app.config['MAIL_USERNAME']= os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD']= os.environ.get('EMAIL_PASS')

mail=Mail(app)

# Loading model
model = models.load_model("D:\Project\env\static\models\VGG16_for_Breast.h5")

#initialize MySQL
mysql = MySQL(app)


# Index
#the route is mapped to the index function
@app.route("/")
def index():
    return render_template('home.html')

#the route is mapped to the about function
@app.route('/about')
def about():
    return render_template('about.html')

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])


def allowed_file(filename):
 return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

 #function to classify images
def predict_label(img_path):
    i = i1.load_img(img_path, target_size=(50,50))  # resize image to (50,50)
    i = i1.img_to_array(i)/255.0
    i = i.reshape(1, 50, 50, 3)  # reshape to (1,50,50,3)
    result = model.predict(i)
    a = round(result[0,0],2)*100
    b = round(result[0,1],2)*100
    probability = [a,b]
    app.logger.info(a)
    app.logger.info(b)
    app.logger.info(result)
    ind = np.argmax(result)
    classes = ['Maligent','Begin']
    return classes[ind],probability[ind]



# User Registration Form Class
class RegisterForm(Form):
    name = StringField('Full Name')
    speciality = StringField('Speciality')
    cnic = StringField('CNIC')
    username = StringField('Username')
    email = StringField('Email Address')
    password = PasswordField('Password')
    confirm = PasswordField('Confirm Password')


# Forgot Password Form Class
class ForgotForm(Form):
        email = EmailField('Email Address',[validators.DataRequired(),validators.Email()])


class PasswordResetForm(Form):
    password = PasswordField('Password',[validators.DataRequired(),validators.Length(min=6,max=50),
                                        validators.EqualTo('confirm',message='Password do not match')])

    confirm = PasswordField('Confirm Password',[validators.DataRequired()])



# user register
# by default all other routes  accept GET request but this route needs to accept POST request
#as we have to submit our form through it
@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        speciality = form.speciality.data
        cnic = form.cnic.data
        password = sha256_crypt.encrypt(str(form.password.data))


        # Create cursor
        cur = mysql.connection.cursor()

        result1 = cur.execute("SELECT username FROM user WHERE username=%s",[username])

        result2 = cur.execute("SELECT email FROM user WHERE email=%s",[email])

        result3 = cur.execute("SELECT cnic FROM user WHERE cnic=%s",[cnic])


        if result1 > 0:

            # only initialized flash message
            flash("Username already exists",'danger')

            return render_template('register.html',form=form)

        elif result2 > 0:

            # only initialized flash message
            flash("An account with this email already exists",'danger')

            return render_template('register.html',form=form)

        elif result3 > 0:

            # only initialized flash message
            flash("An account with this CNIC already exists",'danger')

            return render_template('register.html',form=form)

        else:
            # Execute query
            cur.execute("INSERT INTO user(name,cnic,speciality,email,username,password) VALUES(%s,%s,%s,%s,%s,%s)",(name,cnic,speciality,email,username,password))

            #Commit to DB
            mysql.connection.commit()

            #Close connection
            cur.close()

            # only initialized flash message
            flash("You're registration request has been sent",'success')

            return redirect(url_for('login'))

    return render_template('register.html',form=form)

# User Login
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by Username
        result = cur.execute("SELECT * from user WHERE username = %s ",[username])

        if result > 0:
            # Get stored hash
            # In Order to get the first username from the database
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate,password):

                if data['user_type'] == 1:
                    # Allow Login
                    session['logged_in'] = True
                    session['username'] = username
                    session['user_type'] = 1
                    session['id'] = data['id']
                    app.logger.info(session['id']) 
                    flash('You are now logged in','success')
                    return redirect(url_for('admin'))
                elif data['user_type'] == 0:
                    # Allow Login
                    session['logged_in'] = True
                    session['username'] = username
                    session['user_type'] = 0
                    session['id'] = data['id']

                    flash('You are now logged in','success')
                    return redirect(url_for('dashboard'))
                elif data['user_type'] == -1:
                    error = "Request hasn't been accepted yet"
                    return render_template('login.html',error=error)
            else:
                error = 'Invalid Login'
                return render_template('login.html',error=error)
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html',error=error)
    return render_template('login.html')


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash('Unauthorized, Please login','danger')
            return redirect(url_for('login'))
    return wrap

def redirect_url(default='index'):
    return request.args.get('next') or request.referrer or url_for(default)

# Check if user is physician
# def is_physician_in(f):
#     @wraps(f)
#     def wrap(*args,**kwargs):
#         if session['user_type'] == 0:
#             return f(*args,**kwargs)
#         else:
#             flash('Unauthorized Access','danger')
#             return redirect(redirect_url('admin'))
#     return wrap


# Check if user is admin
def is_admin_in(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if session['user_type'] == 1:
            return f(*args,**kwargs)
        elif session['user_type'] == 0:
            return f(*args,**kwargs)
        else:
            flash('Unauthorized Access','danger')
            return redirect(redirect_url('dashboard'))
    return wrap

def is_physician_in(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if session['user_type'] == 0:
            return f(*args,**kwargs)
        elif session['user_type'] == 1:
            return f(*args,**kwargs)
        else:
            flash('Unauthorized Access','danger')
            return redirect(redirect_url('admin'))
    return wrap

#Users Route for admin
@app.route('/user')
@is_logged_in
@is_admin_in
def user():
    #Create Cursor
    cur = mysql.connection.cursor()

    #Get User
    result = cur.execute("SELECT * FROM user WHERE user_type='0'")

    user = cur.fetchall()

    if result > 0:
        return render_template('users.html', user=user)

    else:
        msg = "No Users Found"
        return render_template('users.html' , msg=msg)

    #Close Connection
    cur.close()

# User Requests
@app.route('/user_requests')
@is_logged_in
@is_admin_in
def userRequests():

    # Create cursor
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM user WHERE user_type='-1'")

    #Get Records in Tuple Format
    users = cur.fetchall()

    if result > 0:
        # Close Connection
        cur.close()
        return render_template('user_requests.html',users=users)
    else:
        # Close Connection
        cur.close()
        msg = 'No User Requests Found'
        return render_template('user_requests.html',msg=msg)


# Accept User
@app.route('/user_requests/<string:id>',methods=['GET','POST'])
@is_logged_in
@is_admin_in
def acceptUser(id):

    if request.method == 'POST':
        # Create cursor
        cur = mysql.connection.cursor()
        # execute query
        result = cur.execute("SELECT email from user WHERE id=%s",[id])

        data = cur.fetchone()

        email = data['email']

        TEXT = "You're sign up request has been accepted\n\n Follow the link to login  http://127.0.0.1:5000/login"

        SUBJECT = "EczPsoC Application"

        message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
        #define gmail server
        server = smtplib.SMTP("smtp.gmail.com",587)   #587
        #starts up server

        # server.starttls()
        # # #app.logger.info(os.environ.get('Email'))
        # # server.login('mughal.ihtisham19@gmail.com','administrator19')
        # # server.sendmail('email',email,message)

        # execute query
        cur.execute("UPDATE user SET user_type='0' WHERE id=%s",[id])

        # Commit to DB
        mysql.connection.commit()

        # Close Connection
        cur.close()

        flash('Request Accepted','success')

        return redirect(url_for('userRequests'))

# Delete User
@app.route('/delete_user_request/<string:id>',methods=['POST'])
@is_logged_in
@is_admin_in
def deleteUserRequest(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE from user WHERE id=%s",[id])

    # Commit to DB
    mysql.connection.commit()

    # Close Connection
    cur.close()

    flash('Request Deleted','success')

    return redirect(url_for('userRequests'))


#Delete User Route
@app.route('/delete_user/<string:id>', methods=['POST'])
@is_logged_in
@is_admin_in
def delete_user(id):
    #Create Cursor
    cur = mysql.connection.cursor()

    #Execute
    cur.execute("DELETE FROM user WHERE id= %s", [id])

    #commit to DB
    mysql.connection.commit()

    #close connection
    cur.close()

    flash('User Deleted','success')
    return redirect(url_for('user'))



#Profile Route
@app.route('/profile')
@is_logged_in
def profile():
    #Create Cursor
    cur = mysql.connection.cursor()

    id = session['id']
    #Get Users
    result = cur.execute("SELECT * FROM user WHERE id=%s",[id])

    user = cur.fetchall()

    if result > 0:
        return render_template('profile.html', user=user,id=id)

    else:
        msg = "No User Found"
        return render_template('profile.html' , msg=msg)

    #Close Connection
    cur.close()

#Admin Dashboard Route
@app.route('/admin')
@is_logged_in
@is_admin_in
def admin():

    # Create cursor
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT COUNT(id) AS users FROM user WHERE user_type='0'")

    data = cur.fetchone()

    users = data['users']

    result = cur.execute("SELECT COUNT(p_id) AS all_patients FROM patients")

    data = cur.fetchone()

    patients = data['all_patients']

    result = cur.execute("SELECT * FROM user WHERE user_type='0'")

    user_records = cur.fetchall()

    result = cur.execute("SELECT COUNT(disease_id) AS disease_reports FROM disease")

    data = cur.fetchone()

    reports = data['disease_reports']

    result = cur.execute("SELECT *,concat('P21-',lpad(patients.p_id,5,'0')) AS p_id2 FROM patients")

    patient_records = cur.fetchall()

    cur.close()


    return render_template('admin_dashboard.html',patient_records=patient_records,reports=reports,user_records=user_records,patients=patients,users=users)



# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out','success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
@is_physician_in
def dashboard():

    # Create Cursor
    cur = mysql.connection.cursor()

    id = session['id']

    result = cur.execute("SELECT *,concat('P21-',lpad(p_id,5,'0')) AS p_id2  FROM patients WHERE user_id=%s",[id])

    patient_records = cur.fetchall()

    result = cur.execute("SELECT COUNT(p_id) AS all_patients FROM patients WHERE user_id=%s",[id])

    data = cur.fetchone()

    patients = data['all_patients']

    result = cur.execute("SELECT COUNT(disease_id) AS all_reports FROM disease WHERE patient_id in (SELECT p_id from patients WHERE user_id=%s)",[id])

    data = cur.fetchone()

    reports = data['all_reports']

    return render_template('dashboard.html',reports=reports,patients=patients,patient_records=patient_records)

# Forgot Password
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    form = ForgotForm(request.form)

    if request.method == 'POST' and form.validate():
        email = form.email.data
        # Create cursor
        cur = mysql.connection.cursor()
        # execute query
        result = cur.execute("SELECT * from user where email=%s",[email])

        data = cur.fetchone()

        if result > 0:

            token = str(uuid.uuid4())

            # execute query
            cur.execute("UPDATE user SET token=%s WHERE email=%s",(token,email))

            #commit to DB
            mysql.connection.commit()

            TEXT = "We have received a request for password reset.\n\n To reset your password, please click on this link:\n http://127.0.0.1:5000/reset/"+token

            SUBJECT = "Password reset request"

            message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
            #define gmail server
            server = smtplib.SMTP("smtp.gmail.com",587)
            #starts up server
            server.starttls()

            server.login('etopiyaaly611@gmail.com','Suppose your token of email')
            server.sendmail('email',email,message)
            # Close connection
            cur.close()
            msg = "You have received a password reset email"
            return render_template('forgot.html',form=form,msg=msg)
        else:
            # Close connection
            cur.close()
            error = "A user account with this email doesn't exist"
            return render_template('forgot.html',form=form,error=error)

    return render_template('forgot.html',form=form)


# reset Password
@app.route('/reset/<string:token>',methods=['GET','POST'])
def resetPassword(token):

    form = PasswordResetForm(request.form)

    # Start Connection
    cur = mysql.connection.cursor()

    # Execute query
    result = cur.execute("SELECT * from user WHERE token=%s",[token])

    if result > 0:
        if request.method == 'POST' and form.validate():
            # new password
            password = sha256_crypt.encrypt(str(form.password.data))

            # Execute query
            cur.execute("UPDATE user SET password=%s, token='' WHERE token=%s",(password,token))

            # commit to DB
            mysql.connection.commit()

            # close Connection
            cur.close()

            #send success message
            flash('Password successfully changed','success')

            return redirect(url_for('login'))
        return render_template('reset_password.html',form=form)

    else:
        # send danger message
        flash('Your token is invalid','danger')
        return redirect(url_for('login'))

#Patients Route
@app.route('/patients')
@is_logged_in
@is_admin_in
@is_physician_in
def patients():
    #Create Cursor
    cur = mysql.connection.cursor()

    id = session['id']
    #Get Patients
    result = cur.execute("SELECT *,concat('P21-',lpad(p_id,5,'0')) as p_id2 FROM patients WHERE user_id=%s",[id])

    patients = cur.fetchall()

    if result > 0:
        return render_template('patients.html', patients=patients)

    else:
        msg = "No Patients Found"
        return render_template('patients.html' , msg=msg)

    #Close Connection
    cur.close()


# Patient Form Class
class PatientForm(Form):
    user_id = StringField('User ID')
    p_name = StringField('Full Name')
    p_dob = StringField('Date of Birth')
    p_age = StringField('Age')
    p_docname = StringField('Doctor Name')
    p_gender = SelectField(u'Gender',choices = [('Male','Male'),('Female','Female')])


#Add Patient Route
@app.route('/add_patient',methods = ['GET', 'POST'])
@is_logged_in
@is_physician_in
def add_patient():
    form = PatientForm(request.form)
    if request.method == 'POST' and form.validate():
        p_name = form.p_name.data
        p_dob = form.p_dob.data
        p_age = form.p_age.data
        p_docname = form.p_docname.data
        p_gender = form.p_gender.data

        #Create cursor
        cur = mysql.connection.cursor()

        #Execute
        cur.execute("INSERT INTO patients(p_name, user_id, p_dob, p_age,p_docname,p_gender) VALUES(%s,%s,%s,%s,%s,%s)", (p_name, session['id'], p_dob,p_age,p_docname,p_gender))

        #commit to DB
        mysql.connection.commit()

        #close connection
        cur.close()

        flash('Patient Added','success')
        return redirect(url_for('patients'))
    return render_template('add_patient.html',form=form)



#Edit Patient Route
@app.route('/edit_patient/<string:id>',methods = ['GET', 'POST'])
@is_logged_in
@is_physician_in
def edit_patient(id):

    #Create Cursor
    cur = mysql.connection.cursor()

    #Get Patients by id
    result = cur.execute("SELECT * FROM patients WHERE p_id=%s", [id])

    patient = cur.fetchone()


    #Get form
    form = PatientForm(request.form)

    #populate patient form fields
    form.user_id.data =patient['user_id']
    form.p_name.data = patient['p_name']
    form.p_dob.data = patient['p_dob']
    form.p_age.data = patient['p_age']
    form.p_docname.data = patient['p_docname']
    form.p_gender.data = patient['p_gender']

    if request.method == 'POST' and form.validate():
        # user_id = request.form['user_id']
        p_name = request.form['p_name']
        p_dob = request.form['p_dob']
        p_age = request.form['p_age']
        p_docname = request.form['p_docname']
        p_gender = request.form['p_gender']
        #Create cursor
        cur = mysql.connection.cursor()

        #Execute
        cur.execute("UPDATE patients SET p_name=%s, p_dob=%s, p_age=%s, p_docname=%s, p_gender=%s WHERE p_id = %s", (p_name,p_dob,p_age,p_docname,p_gender, id))

        #commit to DB
        mysql.connection.commit()

        #close connection
        cur.close()

        flash('Patient Edited','success')
        return redirect(url_for('patients'))
    return render_template('edit_patient.html',form=form)

#Delete Patient Route
@app.route('/delete_patient/<string:id>', methods=['POST'])
@is_logged_in
@is_physician_in
def delete_patient(id):
    #Create Cursor
    cur = mysql.connection.cursor()

    #Execute
    cur.execute("DELETE FROM patients WHERE p_id= %s", [id])

    #commit to DB
    mysql.connection.commit()

    #close connection
    cur.close()

    flash('Patient Deleted','success')
    return redirect(url_for('patients'))





# Patient EczPso Classification History
@app.route('/history/<string:id>')
@is_logged_in
@is_physician_in
def eczpso_history(id):

    user_id = session['id']
    # Create cursor
    cur = mysql.connection.cursor()

    # execute query
    result = cur.execute("SELECT * FROM patients WHERE p_id=%s AND user_id=%s",(id,user_id))

    data = cur.fetchone()

    #To reject data not available in db(If user sends GET request from url)
    if data is None:
        # only initialized flash message
        flash("No Such Record Exists",'danger')
        return redirect(url_for('classify'))

    #Get EczPso History of a patient
    result = cur.execute("SELECT * FROM disease WHERE patient_id=%s ORDER BY create_date DESC",[id])

    history = cur.fetchall()

    if result > 0:
        #Close connection
        cur.close()
        return render_template('eczpso_history.html', history=history)
    else:
        #Close Connection
        cur.close()
        msg = "No History Found"
        return render_template('eczpso_history.html' , msg=msg)



@app.route('/classify')
@is_logged_in
@is_physician_in
def classify():
    #Create Cursor
    cur = mysql.connection.cursor()

    id = session['id']
    #Get Patients
    result = cur.execute("SELECT *,concat('P21-',lpad(p_id,5,'0')) as p_id2 FROM patients WHERE user_id=%s",[id])

    patients = cur.fetchall()

    if result > 0:
        return render_template('classify.html', patients=patients)

    else:
        msg = "No Patients Found"
        return render_template('classify.html' , msg=msg)

    #Close Connection
    cur.close()

# #Classify Image Route
@app.route('/classify_image/<string:id>',methods = ['GET', 'POST'])
@is_logged_in
@is_physician_in
def classify_image(id):

     user_id = session['id']
     # Create cursor
     cur = mysql.connection.cursor()

     # execute query
     result = cur.execute("SELECT * FROM patients WHERE p_id=%s AND user_id=%s",(id,user_id))

     data = cur.fetchone()

#     #To reject data not available in db(If user sends GET request from url)
     if data is None:
#         # only initialized flash message
         flash("No Such Record Exists",'danger')
         return redirect(url_for('classify'))


     full_filename =  'img/no_image.PNG'
#     # Execute if request is get
     if request.method == "GET":
         return render_template("classify_image.html", full_filename = full_filename)

#     # Execute if reuqest is post
     if request.method == "POST":

          image_upload = request.files['image_upload']


          if not(image_upload):

              flash('No File Uploaded','danger')
              return render_template('classify_image.html',full_filename=full_filename)


          elif not(allowed_file(image_upload.filename)):

              flash('Only .png, .jpg, .jpeg file extensions allowed','danger')
              return render_template('classify_image.html',full_filename=full_filename)

          else:


#              # Generating unique image name
              letters = string.ascii_lowercase
              name = ''.join(random.choice(letters) for i in range(10)) + '.png'
              full_filename =  'img/uploads/' + name

#              # Reading, resizing, saving and preprocessing image for predicition

              imagename = image_upload.filename
              image = Image.open(image_upload)
              image = image.resize((128,128))
              img_path = os.path.join(app.config['INITIAL_FILE_UPLOADS'], name)
              image.save(img_path)
              pred , prob = predict_label(img_path)

#              #Execute
              cur.execute("INSERT INTO disease(patient_id,disease_name,image) VALUES(%s,%s,%s)", (id,pred,img_path))

#              #commit to DB
              mysql.connection.commit()

#              #get last row id (meaning the id of the record just inserted)
              disease_id = cur.lastrowid
              app.logger.info(disease_id)

              #close connection
              cur.close()


              # Returning template, filename, extracted text
              return render_template('classify_image.html', full_filename = full_filename, pred = pred,prob=prob,disease_id=disease_id)

#Classify Image Classification into PDF
@app.route('/eczpso_pdf/<string:id>')
@is_logged_in
@is_physician_in
def eczpso_pdf(id):

    user_id = session['id']
    # Create cursor
    cur = mysql.connection.cursor()

    # execute query
    result = cur.execute("SELECT * FROM disease WHERE disease_id=%s",[id])

    data = cur.fetchone()

    #To reject data not available in db(If user sends GET request from url)
    if data is None:
        # only initialized flash message
        flash("No Such Record Exists",'danger')
        return redirect(url_for('classify'))

    # execute query
    result = cur.execute("SELECT *,concat('22-',lpad(patients.p_id,4,'0')) as p_id2 FROM patients INNER JOIN disease ON patients.p_id=disease.patient_id WHERE disease.disease_id=%s AND patients.user_id=%s",(id,user_id))

    data = cur.fetchone()

    # keep in mind the code is not repeating it is necessary
    # for doctors to only select data of only their patients
    if data is None:
        # only initialized flash message
        flash("No Such Record Exists",'danger')
        return redirect(url_for('classify'))


    id = data['p_id2']

    create_date = data['create_date']

    name=data['p_name']

    dob =  data['p_dob']

    age = data['p_age']

    gender = data['p_gender']

    disease_name = data['disease_name']

    #Close Connection
    cur.close()

    src = os.path.dirname(os.path.abspath(__file__))+'/'+data['image']#'/static/img/no_image.PNG'
    app.logger.info(src)
    rendered = render_template('eczpso_pdf.html',id=id,full_filename=src,name=name,dob=dob,age=age,gender=gender,time_added=create_date,pred=disease_name)
    options = {
  "enable-local-file-access": None
    }
    pdf = pdfkit.from_string(rendered,False,options=options)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; output.pdf'

    return response

class GenerateLabReport(Form):
    patient = SelectField(u'Patient Name',coerce = int)
    report_date = SelectField(u'Report Date',coerce = int)


#  Form data to generate lab report in pdf format
@app.route('/lab_reports',methods=['GET','POST'])
@is_logged_in
@is_physician_in
def labReports():
    form = GenerateLabReport(request.form)

    doc_id = session['id']

    #Create Cursor
    cur = mysql.connection.cursor()

    #Get Users
    patient_result = cur.execute("SELECT p_id,p_name FROM patients WHERE user_id=%s AND p_id in (SELECT patient_id FROM lab_reports)",[doc_id])

    patients = cur.fetchall()

    patientData = []
    for patient in patients:
        patientData.append((patient['p_id'],patient['p_name']))

    form.patient.choices = patientData

    if request.method == 'POST':
        patient = str(form.patient.data)
        report_date = str(request.form['report_date'])
        app.logger.info(report_date)
        return patient + " " + report_date

    return render_template('lab_reports.html',form=form)


# Process function is use to make receive an ajax request
# To receive patient name and return lab report dates of that patient
@app.route('/process',methods=['GET','POST'])
@is_logged_in
@is_physician_in
def process():

    patient_id = request.form['patient']

    if patient_id:
        #return jsonify({'one':'20-01-2020','two':'10-01-2010'})
            #Create Cursor
        cur = mysql.connection.cursor()

        #Get Users
        report_dates = cur.execute("SELECT DATE_FORMAT(date,'%%Y-%%m-%%d') as report_date FROM lab_reports WHERE patient_id = %s GROUP BY report_date",[patient_id])

        report_dates = cur.fetchall()


        return jsonify(report_dates)

    return 'error'

#Generate PDF of Lab Report
@app.route('/lab_report_pdf',methods=['GET','POST'])
@is_logged_in
@is_physician_in
def lab_report_pdf():

    physician_id = session['id']

    # Create cursor
    cur = mysql.connection.cursor()

    # Execute Query
    result = cur.execute("SELECT name from user WHERE id=%s",[physician_id])

    if result > 0:
        data = cur.fetchone();
        physician_name = data['name']
    else:
        return 'No User Data Found'


    if request.method == 'POST':
        # Extracting data from request form
        patient_id = request.form['patient'];
        report_date = request.form['report_date'];

        #Get Users
        result = cur.execute("SELECT * FROM (((lab_reports INNER JOIN patients ON p_id = patient_id) INNER JOIN tests_under ON lab_reports.test_id = tests_under.id) INNER JOIN lab_tests ON tests_under.test_id = lab_tests.Id) WHERE DATE_FORMAT(lab_reports.date,'%%Y-%%m-%%d')=%s AND lab_reports.patient_id=%s ORDER BY lab_tests.test_name",(report_date,patient_id))

        report_details = cur.fetchall()

        if result > 0:
            cur.close()

            report_data = {}
            for info in report_details:
                report_data[info['lab_tests.test_name']] = {'TEST':[],'RESULT':[],'UNIT':[],'UPPER_LIMIT':[],'LOWER_LIMIT':[]}

            for info in report_details:
                report_data[info['lab_tests.test_name']]['TEST'].append(info['test_name'])
                report_data[info['lab_tests.test_name']]['RESULT'].append(info['test_value'])
                report_data[info['lab_tests.test_name']]['UNIT'].append(info['unit'])
                report_data[info['lab_tests.test_name']]['UPPER_LIMIT'].append(info['upper_limit'])
                report_data[info['lab_tests.test_name']]['LOWER_LIMIT'].append(info['lower_limit'])
                report_data[info['lab_tests.test_name']]['LENGTH'] = len(report_data[info['lab_tests.test_name']]['TEST'])


            rendered = render_template('lab_report_pdf.html',report_details=report_details,report_date=report_date,physician_name=physician_name,report_data=report_data)
            options = {
          "enable-local-file-access": None
            }
            pdf = pdfkit.from_string(rendered,False,options=options)

            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = 'inline; lab_report.pdf'

            return response

        else:
            msg = "No User Data Found"
            return msg#render_template('profile.html' , msg=msg)

# Add Test Type Form
class labTest(Form):

    test_name = StringField(label='Test name',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^[a-zA-Z ]*$",message="Only alphabets and spaces are allowed")])

    code = StringField(label='code',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^[a-zA-Z ]*$",message="Only alphabets and spaces are allowed")])

    submit = SubmitField(label="Submit")
# View type of Lab Test
# Test Under Category Add Form
class TestUnder(Form):

    test_name = StringField(label='Test name',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^[a-zA-Z ]*$",message="Only alphabets and spaces are allowed")])

    lower_limit = StringField(label='Lower limit',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^([0-9]+[.]?[0-9]*)$",message="Only positive numeric or decimal values allowed")])

    upper_limit = StringField(label='Upper limit',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^([0-9]+[.]?[0-9]*)$",message="Only positive numeric or decimal values allowed")])

    unit = StringField(label='Unit',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^[a-zA-Z/%]*$",message="Only alphabets and some special characters allowed (/,%)")])

    unit_price = StringField(label='Unit price',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^([0-9]+[.]?[0-9]*)$",message="Only numeric or decimal values allowed")])

    taxes = StringField(label='Taxes',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^([0-9]+[.]?[0-9]*)$",message="Only numeric or decimal values allowed")])




# Lab Test Type Sub Category
@app.route('/test_under/<string:id>',methods=['GET','POST'])
@is_logged_in
@is_physician_in
def testUnder(id):

    form = TestUnder(request.form)

    if request.method == 'POST' and form.validate():
        test_name = form.test_name.data
        lower_limit = form.lower_limit.data
        upper_limit = form.upper_limit.data
        unit = form.unit.data
        unit_price = form.unit_price.data
        taxes = form.taxes.data


        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO tests_under(test_name,test_id,lower_limit,upper_limit,unit,unit_price,taxes) VALUES(%s, %s, %s, %s, %s, %s, %s)",(test_name,id,lower_limit,upper_limit,unit,unit_price,taxes))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Test Under Category Created', 'success')

        return redirect(url_for('testUnder',id=id))

    # Create cursor
    cur = mysql.connection.cursor()

    # Get user by Lab Test Type Name
    result = cur.execute("SELECT test_name from lab_tests WHERE id = %s ",[id])

    data = cur.fetchone()
    lab_test = data['test_name']

    # Get Tests
    result = cur.execute("SELECT * FROM tests_under WHERE test_id=%s",[id])

    tests = cur.fetchall()

    if result > 0:
        return render_template('test_under.html', tests=tests, form=form,lab_test=lab_test)
    else:
        msg = 'No Tests Under Category Found'

        return render_template('test_under.html',msg=msg,form=form,lab_test=lab_test);

    # Close connection
    cur.close()


# Lab Report Fields
class LabReport(Form):

    patient = SelectField(u'Patient',coerce = int)
    test_value = StringField(label='Test Value',validators=[DataRequired(),validators.Length(min=1),validators.Regexp(regex="^([0-9]+[.]?[0-9]*)$",message="Only numeric or decimal values allowed")])


# Add Lab Report Data of a patient
@app.route('/add_lab_report/<string:id>',methods=['GET','POST'])
@is_logged_in
@is_physician_in
def addLabReport(id):

    form = LabReport(request.form)

    doc_id = session['id']

    #Create Cursor
    cur = mysql.connection.cursor()

    #Get Users
    result = cur.execute("SELECT p_id,p_name FROM patients WHERE user_id=%s",[doc_id])

    patients = cur.fetchall()

    patientData = []
    for patient in patients:
        patientData.append((patient['p_id'],patient['p_name']))

    form.patient.choices = patientData

    if request.method == 'POST' and form.validate():
        patient_id = form.patient.data
        test_value = form.test_value.data

        #execute
        result = cur.execute("INSERT INTO lab_reports(test_id,patient_id,test_value) VALUES(%s,%s,%s)",(id,patient_id,test_value))

        #commit to DB
        mysql.connection.commit()

        flash('Report Added','success')
        return redirect(url_for('addLabReport',id=id))


    result = cur.execute("SELECT lab_tests.test_name as test_type_name,lab_tests.Id as type_id, tests_under.test_name as test_name  FROM lab_tests INNER JOIN tests_under ON lab_tests.Id=tests_under.test_id WHERE tests_under.id=%s",[id])

    data = cur.fetchone()

    test_data = data

    #Get Users
    result = cur.execute("SELECT p_id,p_name FROM patients WHERE user_id=%s",[doc_id])

    if result > 0:
        return render_template('add_lab_report.html',test_data=test_data,form=form)
    else:
        msg = "No Patients Found"
        return render_template('add_lab_report.html' , msg=msg,form=form)

# Lab Request Fields
class LabRequest(Form):

    patient = SelectField(u'Patient',coerce = int)
    request_date = DateTimeLocalField('Request Date',format='%Y-%m-%dT%H:%M',validators=[DataRequired()])
    urgency = SelectField(u'Urgency Level',choices = [('Normal','Normal'),('High','High'),('Very High','Very High')])


# Add Lab Request for a patient
@app.route('/add_lab_request/<string:id>',methods=['GET','POST'])
@is_logged_in
@is_physician_in
def addLabRequest(id):

    form = LabRequest(request.form)

    doc_id = session['id']

    #Create Cursor
    cur = mysql.connection.cursor()

    #Get Users
    patient_result = cur.execute("SELECT p_id,p_name FROM patients WHERE user_id=%s",[doc_id])

    patients = cur.fetchall()

    patientData = []
    for patient in patients:
        patientData.append((patient['p_id'],patient['p_name']))

    form.patient.choices = patientData

    if request.method == 'POST' and form.validate():
        request_date = form.request_date.data.strftime("%Y-%m-%d %H:%M:00")
        patient_id = form.patient.data
        urgency_level = form.urgency.data

        #execute
        result = cur.execute("INSERT INTO lab_requests(test_id,patient_id,urgency_level,request_date) VALUES(%s,%s,%s,%s)",(id,patient_id,urgency_level,request_date))

        #commit to DB
        mysql.connection.commit()

        flash('Request Added','success')
        return redirect(url_for('addLabRequest',id=id))



    result = cur.execute("SELECT lab_tests.test_name as test_type_name,lab_tests.Id as type_id, tests_under.test_name as test_name  FROM lab_tests INNER JOIN tests_under ON lab_tests.Id=tests_under.test_id WHERE tests_under.id=%s",[id])

    data = cur.fetchone()

    test_data = data

    if patient_result > 0:
        return render_template('add_lab_request.html',test_data=test_data,form=form)
    else:
        msg = "No Patients Found"
        return render_template('add_lab_request.html' , msg=msg,form=form)



if __name__ == "__main__":
    app.secret_key='secret123'
    app.run(debug=True)
