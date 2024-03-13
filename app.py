import os
import random
from flask import *
from flask_mail import Mail, Message
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongodb = os.getenv('MONGODB')
username = os.getenv('MAILUSERNAME')
password = os.getenv('MAILPASSWORD')

app=Flask(__name__)

app.config["SECRET_KEY"] = 'project3141621'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = username
app.config['MAIL_PASSWORD'] = password
app.config['MAIL_DEFAULT_SENDER'] = username
mongo = MongoClient(mongodb)
mail = Mail(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        db = mongo.majorproject
        if 'sendotp' in request.form:
            userid=request.form['userid']
            session['userid']=userid
            exists=db.users.find_one({'userid':userid})
            if exists:
                flash('User already exists')
                return render_template('register.html',userid=userid, condition2='disabled')
            else:
                userid=session['userid']
                otp = str(random.randint(100000,999999))
                message = f'Your otp for verification is {otp}'
                session['otp']=otp
                msg = Message(subject='Verification',
                      recipients=[userid],
                      body=message,
                      extra_headers={"Importance": "High"}
                )
                try:
                    mail.send(msg)
                    flash('OTP Sent')
                    return render_template('register.html',userid=userid)
                except Exception as e:
                    flash(f'Failed to send email: {str(e)}')
                    return render_template('register.html',userid=userid)
                    
        elif 'verifyotp' in request.form:
            entered_otp=request.form['otp']
            otp=session['otp']
            if(entered_otp == otp):
                userid = session['userid']
                flash('Verification Successful')
                return render_template('register.html',userid=userid,condition1='disabled',condition2='disabled',verified=True)
            else:
                userid=session['userid']
                flash('Incorrect OTP. Please try again')
                return render_template('register.html',userid=userid)
        elif 'register' in request.form:
            userid = session['userid']
            username = request.form['username']
            userpass = request.form['userpass']
            checkpass = request.form['checkpass']
            q1 = request.form['question1']
            a1 = request.form['answer1'].lower().replace(" ", "")
            q2 = request.form['question2']
            a2 = request.form['answer2'].lower().replace(" ", "")
            q3 = request.form['question3']
            a3 = request.form['answer3'].lower().replace(" ", "")
            db.users.insert_one({ 
                'userid':userid, 
                'userpass':userpass,
                'username':username,
                'qanda':{q1:a1, q2:a2, q3:a3},
                'checked_in':[],
                'locker_log':{}, 
                'wallet':0 })
            session.pop('userid', None)
            session.pop('otp', None)
            return render_template('registrationsuccess.html')
    flash('Not yet Verified')
    return render_template('register.html',condition2='disabled')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if 'login' in request.form:
            db = mongo.majorproject
            userid = request.form['userid']
            userpass = request.form['userpass']
            user=db.users.find_one({'userid':userid,'userpass':userpass})
            if user:
                return 'Logged in'
            else:
                return 'Invalid UserID or password'
    return render_template('login.html')

@app.route('/reset', methods=['GET','POST'])
def reset():
    db = mongo.majorproject
    if 'next' in request.form:
        userid = request.form['userid']
        session['userid'] = userid
        exists = db.users.find_one({'userid':userid})
        if exists:
            userid = session['userid']
            return render_template('reset.html', userid=userid)
        else:
            flash("User don't exist")
            return render_template('validate.html',userid=userid)
    if 'sendotp' in request.form:
        userid = session['userid']
        otp = str(random.randint(100000,999999))
        message = f'Your otp to reset password is {otp}'
        session['otp']=otp
        msg = Message(subject='Verification',
                recipients=[userid],
                body=message,
                extra_headers={"Importance": "High"}
        )
        try:
            mail.send(msg)
            flash('OTP Sent')
            return render_template('reset.html', otpsent=True, userid=userid)
        except Exception as e:
            flash(f'Failed to send email: {str(e)}')
            return render_template('reset.html', userid=userid)
    if 'verifyotp' in request.form:
        entered_otp=request.form['otp']
        otp=session['otp']
        userid = session['userid']
        if(entered_otp == otp):
            return render_template('changepassword.html')
        else:
            flash('Incorrect OTP. Please try again')
            return render_template('reset.html',otpsent=True,userid=userid)
    if 'change' in request.form:
        userid = session['userid']
        userpass = request.form['userpass']
        db.users.update_one({'userid':userid},{'$set':{'userpass':userpass}})
        session.pop('userid', None)
        session.pop('otp', None)
        return render_template('resetsuccess.html')

    return render_template('validate.html')

@app.route('/test')
def test():
    return redirect('/#')

if(__name__=='__main__'):
    app.run(debug = True)