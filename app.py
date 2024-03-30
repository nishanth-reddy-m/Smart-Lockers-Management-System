import os
import random
from datetime import datetime
#import serial
from flask import *
from flask_mail import Mail, Message
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongodb = os.getenv('MONGODB')
username = os.getenv('MAILUSERNAME')
password = os.getenv('MAILPASSWORD')

#arduino = serial.Serial('COM5',9600)

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
                    body=message
            )
            try:
                mail.send(msg)
                flash('OTP Sent')
                return render_template('register.html',userid=userid)
            except Exception as e:
                flash(f'Failed to send email: {str(e)}')
                return render_template('register.html',userid=userid)
    if 'verifyotp' in request.form:
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
    if 'register' in request.form:
        userid = session['userid']
        username = request.form['username'].lower()
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
            'qanda':{
                'q1':q1,
                'a1':a1,
                'q2':q2,
                'a2':a2,
                'q3':q3,
                'a3':a3,
                },
            'checked_in':{},
            'wallet':0.0 })
        session.pop('userid', None)
        session.pop('otp', None)
        return render_template('registrationsuccess.html')
    flash('Not yet Verified')
    return render_template('register.html',condition2='disabled')

@app.route('/recharge', methods=['GET','POST'])
def recharge():
    db = mongo.majorproject
    if 'next' in request.form:
        userid = request.form['userid']
        exists = db.users.find_one({'userid':userid})
        if exists:
            session['userid'] = userid
            return render_template('recharge.html', userid=userid, valid=True, condition='disabled', display=False)
        else:
            flash("User don't exist")
            return render_template('recharge.html',display=True, userid=userid)
    if 'pay' in request.form:
        userid = session['userid']
        amount = float(request.form['amount'])
        db.users.update_one({'userid':userid}, {'$inc': {'wallet': amount}})
        wallet = balance(userid)
        session.pop('userid', None)
        return render_template('rechargesuccess.html', wallet=wallet)
    return render_template('recharge.html', display=True)

def private_disabled(locker):
    userid = session['userid']
    db = mongo.majorproject
    dblocker = db.users.find_one({'userid':userid},{'_id': 0, 'checked_in': 1})
    privatelockers = dblocker.get('checked_in',{})
    return locker not in privatelockers

def public_disabled(locker):
    db = mongo.majorproject
    dblocker = db.lockers.find_one({},{'_id': 0, 'available_lockers': 1})
    publiclockers = dblocker.get('available_lockers',[])
    return locker not in publiclockers

def balance(userid):
    db = mongo.majorproject
    dbamount = db.users.find_one({'userid':userid},{'_id': 0, 'wallet': 1})
    amount = dbamount['wallet']
    return amount

def unoaction(checked,Input):
    action = ''
    for locker in checked:
        action += locker
    action += Input
    arduino.write(action.encode('utf-8'))
    receive = arduino.readline().decode().strip()

@app.route('/login', methods=['GET','POST'])
def login():
        db = mongo.majorproject
        if 'login' in request.form:
            userid = request.form['userid']
            userpass = request.form['userpass']
            user=db.users.find_one({'userid':userid,'userpass':userpass})
            if user:
                wallet = balance(userid)
                if wallet > 0:
                    session['userid'] = userid
                    amount = balance(userid)
                    dblockers = db.lockers.find_one({},{'_id': 0, 'all_lockers': 1})
                    lockers = dblockers['all_lockers']
                    session['lockers'] = lockers
                    return render_template('interface.html',lockers=lockers,private_disabled=private_disabled,public_disabled=public_disabled, amount=amount)
                else:
                    return render_template('balancecheck.html', amount=wallet)
            else:
                flash('Invalid UserID or Password')
                return render_template('login.html', userid=userid)
        if 'checkin' in request.form:
            userid = session['userid']
            lockers = session['lockers']
            amount = balance(userid)
            checked = request.form.getlist('global_lockers')
            db.lockers.update_one({},{'$pull':{'available_lockers':{'$in': checked}}})
            db.users.update_one({'userid':userid}, {"$set": {f"checked_in.{locker}": datetime.now() for locker in checked}})
            user = db.users.find_one({'userid':userid})
            if 'timestamp' not in user:
                db.users.update_one({'_id': user['_id']}, {'$set': {'timestamp': datetime.now()}})
            #unoaction(checked,'1')
            return render_template('interface.html',lockers=lockers,private_disabled=private_disabled,public_disabled=public_disabled, amount=amount)
        if 'checkout' in request.form:
            userid = session['userid']
            lockers = session['lockers']
            amount = balance(userid)
            checked = request.form.getlist('user_lockers')
            db.users.update_one({'userid':userid}, {"$unset": {f"checked_in.{locker}": "" for locker in checked}})
            db.lockers.update_one({},{'$push':{'available_lockers':{'$each': checked}}})
            user = db.users.find_one({'userid':userid})
            if user['checked_in'] == {}:
                db.users.update_one({'_id': user['_id']}, {'$unset': {'timestamp': ''}})
                db.users.update_one({'_id': user['_id']}, {'$unset': {'mail_threshold': ''}})
            #unoaction(checked,'0')
            return render_template('interface.html',lockers=lockers,private_disabled=private_disabled,public_disabled=public_disabled, amount=amount)
        if 'logout' in request.form:
            session.pop('userid', None)
            session.pop('lockers', None)
            return redirect('/')
        return render_template('login.html')

@app.route('/reset', methods=['GET','POST'])
def reset():
    db = mongo.majorproject
    if 'next' in request.form:
        userid = request.form['userid']
        exists = db.users.find_one({'userid':userid})
        if exists:
            session['userid'] = userid
            return render_template('validate.html', userid=userid, valid=True, condition='disabled', display=False)
        else:
            flash("User don't exist")
            return render_template('validate.html',display=True, userid=userid)
    if 'check' in request.form:
        userid = session['userid']
        username = request.form['username']
        exists = db.users.find_one({'userid':userid, 'username':username.lower()})
        if exists:
            return render_template('reset.html',userid=userid)
        else:
            flash('Incorrect Username')
            return render_template('validate.html', userid=userid, username=username, valid=True, condition='disabled')
    if 'sendotp' in request.form:
        userid = session['userid']
        otp = str(random.randint(100000,999999))
        message = f'Your otp to reset password is {otp}'
        session['otp']=otp
        msg = Message(subject='Verification',
                recipients=[userid],
                body=message
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
            session.pop('otp', None)
            return render_template('changepassword.html')
        else:
            flash('Incorrect OTP. Please try again')
            return render_template('reset.html',otpsent=True,userid=userid)
    if 'securityquestions' in request.form:
        userid = session['userid']
        dbqanda = db.users.find_one({'userid':userid}, {'_id': 0, 'qanda': 1})
        qanda = dbqanda['qanda']
        session['qanda'] = qanda
        q1 = qanda['q1']
        q2 = qanda['q2']
        q3 = qanda['q3']
        return render_template('reset.html', answersq=True, userid=userid, q1=q1, q2=q2, q3=q3)
    if 'verifyanswers' in request.form:
        userid = session['userid']
        qanda = session['qanda']
        a1 = request.form['a1']
        a2 = request.form['a2']
        a3 = request.form['a3']
        session['a1'] = a1
        session['a2'] = a2
        session['a3'] = a3
        if a1.lower().replace(" ", "") == qanda['a1'] and a2.lower().replace(" ", "") == qanda['a2'] and a3.lower().replace(" ", "") == qanda['a3']:
            session.pop('qanda', None)
            session.pop('a1', None)
            session.pop('a2', None)
            session.pop('a3', None)
            return render_template('changepassword.html')
        else:
            qanda = session['qanda']
            q1 = qanda['q1']
            q2 = qanda['q2']
            q3 = qanda['q3']
            a1 = session['a1']
            a2 = session['a2']
            a3 = session['a3']
            flash("Incorrect Answer(s)!")
            return render_template('reset.html', answersq=True, userid=userid, q1=q1, q2=q2, q3=q3, a1=a1, a2=a2, a3=a3)
    if 'change' in request.form:
        userid = session['userid']
        userpass = request.form['userpass']
        db.users.update_one({'userid':userid},{'$set':{'userpass':userpass}})
        message = 'Your password has been successfully changed'
        msg = Message(subject='Reset Password',
                recipients=[userid],
                body=message
        )
        try:
            mail.send(msg)
            session.pop('userid', None)
            return render_template('resetsuccess.html')
        except Exception as e:
            flash(f'Failed to send email: {str(e)}')
            return render_template('changepassword.html')
    return render_template('validate.html',display=True)

@app.route('/testing', methods=['GET','POST'])
def testing():
    pass
    return redirect('/#')

if(__name__=='__main__'):
    app.run(debug = True, port = 5001)