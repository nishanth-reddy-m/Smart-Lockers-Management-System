import os
import random
import smtplib
from datetime import datetime
#import serial
from flask import *
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongodb = os.getenv('MONGODB')
username = os.getenv('MAILUSERNAME')
password = os.getenv('MAILPASSWORD')

#arduino = serial.Serial('COM5',9600)

app=Flask(__name__)

app.config["SECRET_KEY"] = 'project3141621'

mongo = MongoClient(mongodb)
db = mongo.majorproject
session_error = 'Session Ended'

def sendmail(userid,msg,status):
    try:
        mail = smtplib.SMTP('smtp.gmail.com',587)
        mail.starttls()
        mail.login(username,password)
        message = msg.encode('utf-8')
        mail.sendmail(username,userid,message)
        return status
    except Exception as e:
        return f'Failed to send email: {str(e)}'
    finally:
        mail.close()

@app.route('/')
def home():
    if 'log_userid' in session or 'reg_userid' in session or 'rec_userid' in session or 'res_userid' in session or 'log_user' in session:
        session.pop('reg_userid', None)
        session.pop('reg_otp', None)
        session.pop('rec_userid', None)
        session.pop('log_user', None)
        session.pop('log_userid', None)
        session.pop('log_lockers', None)
        session.pop('res_userid', None)
        session.pop('res_otp', None)
        session.pop('res_qanda', None)
        session.pop('res_a1', None)
        session.pop('res_a2', None)
        session.pop('res_a3', None)
        return render_template('home.html',alert = session_error)
    return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if 'sendotp' in request.form:
        userid=request.form['userid']
        session['reg_userid']=userid
        exists=db.users.find_one({'userid':userid})
        if exists:
            alert = 'User already exists'
            return render_template('register.html',userid=userid, condition2='disabled', alert=alert)
        else:
            userid=session['reg_userid']
            otp = str(random.randint(100000,999999))
            session['reg_otp']=otp
            msg = f'Subject: Verification\n\nYour otp for verification is {otp}'
            status = 'OTP Sent'
            output = sendmail(userid,msg,status)
            if output == status:
                alert = f'{output}'
                return render_template('register.html',userid=userid, alert=alert)
            else:
                alert = f'{output}'
                return render_template('register.html', userid=userid, condition2='disabled', alert=alert)
    if 'reg_userid' in session:
        if 'verifyotp' in request.form:
            if 'reg_otp' not in session:
                return redirect('/register')
            entered_otp=request.form['otp']
            otp=session['reg_otp']
            if(entered_otp == otp):
                session.pop('reg_otp', None)
                userid = session['reg_userid']
                return render_template('register.html',userid=userid,condition1='disabled',condition2='disabled',verified=True)
            else:
                userid=session['reg_userid']
                alert = 'Incorrect OTP. Please try again'
                return render_template('register.html',userid=userid, alert=alert)
        if 'register' in request.form:
            userid = session['reg_userid']
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
                'qanda':{
                    'q1':q1,
                    'a1':a1,
                    'q2':q2,
                    'a2':a2,
                    'q3':q3,
                    'a3':a3,
                    },
                'checked_in':{},
                'debit_status':False,
                'wallet':0.0 })
            session.pop('reg_userid', None)
            return render_template('registrationsuccess.html')
    return render_template('register.html',condition2='disabled')

@app.route('/balancerecharge', methods=['POST'])
def balancerecharge():
    if 'rec_userid' in session:
        userid = session['rec_userid']
        balance = db.users.find_one({'userid':userid})['wallet']
        return jsonify({'balance':balance})
    else:
        return jsonify({'balance':'error'})

@app.route('/recharge', methods=['GET','POST'])
def recharge():
    if 'next' in request.form:
        userid = request.form['userid']
        exists = db.users.find_one({'userid':userid})
        if exists:
            session['rec_userid'] = userid
            return render_template('recharge.html', userid=userid, valid=True, condition='disabled', display=False)
        else:
            alert = "User don't exist"
            return render_template('recharge.html',display=True, userid=userid, alert=alert)
    if 'rec_userid' in session:
        if 'pay' in request.form:
            userid = session['rec_userid']
            amount = float(request.form['amount'])
            if amount > 0:
                db.users.update_one({'userid':userid}, {'$inc': {'wallet': amount}})
                credit_log = [amount,datetime.now()]
                db.users.update_one({'userid': userid}, {'$push': {'credit_log': credit_log}})
                wallet = db.users.find_one({'userid':userid})['wallet']
                session.pop('rec_userid', None)
                return render_template('rechargesuccess.html', wallet=wallet)
            else:
                alert = 'Invalid Amount'
                return render_template('recharge.html', userid=userid, valid=True, condition='disabled', display=False, alert=alert)
    return render_template('recharge.html', display=True)

def private_disabled(locker):
    userid = session['log_userid']
    privatelockers = db.users.find_one({'userid':userid})['checked_in']
    return locker not in privatelockers

def public_disabled(locker):
    publiclockers = db.lockers.find_one({})['available_lockers']
    return locker not in publiclockers

def unoaction(checked,Input):
    action = ''
    for locker in checked:
        action += locker
    action += Input
    arduino.write(action.encode('utf-8'))
    receive = arduino.readline().decode().strip()

def setlog(userid,checked):
    lockers = db.users.find_one({'userid':userid})['checked_in']
    payable = db.lockers.find_one({})['payable']
    user_log = []
    for locker in checked:
        if locker in lockers:
            checkin = lockers[locker]
            checkout = datetime.now()
            checked_time = checkout - checkin
            amount = int(checked_time.total_seconds() / 60)*payable
            user_log.append([locker,checkin,checkout,amount])
    db.users.update_one({'userid': userid}, {'$push': {'debit_log': {'$each': user_log}}})

def creditlog():
    userid = session['log_userid']
    user = db.users.find_one({'userid':userid})
    if 'credit_log' in user:
        logs = user['credit_log']
        return logs
    else:
        return

def debitlog():
    userid = session['log_userid']
    user = db.users.find_one({'userid':userid})
    if 'debit_log' in user:
        logs = user['debit_log']
        return logs
    else:
        return

@app.route('/fetchbalance', methods=['POST'])
def fetchbalance():
    if 'log_userid' in session:
        userid = session['log_userid']
        balance = db.users.find_one({'userid':userid})['wallet']
        return jsonify({'balance':balance})
    else:
        return jsonify({'balance':'error'})

@app.route('/login', methods=['GET','POST'])
def login():
    if 'log_userid' in session:
        session.pop('log_userid', None)
        return render_template('login.html', alert=session_error)
    if 'usercheck' in request.form:
        userid = request.form['userid']
        user=db.users.find_one({'userid':userid})
        if user:
            session['log_user'] = user['userid']
            return render_template('login.html', userid=userid, displaypass=True)
        else:
            alert = 'Invalid UserID'
            return render_template('login.html', userid=userid, alert=alert)
    if 'log_user' in session:
        if 'login' in request.form:
            userid = session['log_user']
            userpass = request.form['userpass']
            if db.users.find_one({'userid':userid, 'userpass':userpass}):
                session['log_userid'] = userid
                session.pop('log_user', None)
                return render_template('loginconsole.html')
            else:
                alert = 'Invalid Password'
                return render_template('login.html', userid=userid, displaypass=True, alert=alert)
        return redirect('/')
    else:
        return render_template('login.html')

@app.route('/login/console', methods=['GET','POST'])
def console():
    if 'log_userid' not in session:
        return redirect('/')
    try:
        payable = db.lockers.find_one({})['payable']
        userid = session['log_userid']
        amount = db.users.find_one({'userid':userid})['wallet']
        lockers = db.lockers.find_one({})['all_lockers']
        session['log_lockers'] = lockers
        if 'checkin' in request.form:
            userid = session['log_userid']
            lockers = session['log_lockers']
            amount = db.users.find_one({'userid':userid})['wallet']
            if db.lockers.find_one({})['server']:
                if amount > 0:
                    checked = request.form.getlist('global_lockers')
                    available_lockers = db.lockers.find_one({})['available_lockers']
                    if all(locker in available_lockers for locker in checked):
                        db.lockers.update_one({},{'$pull':{'available_lockers':{'$in': checked}}})
                        db.users.update_one({'userid':userid}, {"$set": {f"checked_in.{locker}": datetime.now() for locker in checked}})
                        user = db.users.find_one({'userid':userid})
                        if 'timestamp' not in user:
                            db.users.update_one({'_id': user['_id']}, {'$set': {'timestamp': datetime.now()}})
                        #unoaction(checked,'1')
                        flash('Please make sure to Logout')
                        return redirect(url_for('console'))
                    else:
                        flash('Locker unavailable')
                        return redirect(url_for('console'))
                else:
                    flash('Please recharge your Wallet to CheckIn')
                    return redirect(url_for('console'))
            else:
                flash('Unable to reach Server')
                return redirect(url_for('console'))
        if 'checkout' in request.form:
            userid = session['log_userid']
            lockers = session['log_lockers']
            amount = db.users.find_one({'userid':userid})['wallet']
            if db.lockers.find_one({})['server']:
                if amount >= 0:
                    checked = request.form.getlist('user_lockers')
                    user_lockers = db.users.find_one({'userid':userid})['checked_in']
                    if all(locker in user_lockers for locker in checked):
                        if db.users.find_one({'userid':userid})['debit_status']:
                            setlog(userid,checked)
                        db.users.update_one({'userid':userid}, {"$unset": {f"checked_in.{locker}": "" for locker in checked}})
                        db.lockers.update_one({},{'$push':{'available_lockers':{'$each': checked}}})
                        user = db.users.find_one({'userid':userid})
                        if user['checked_in'] == {}:
                            db.users.update_one({'_id': user['_id']}, {'$unset': {'timestamp': ''}})
                            db.users.update_one({'_id': user['_id']}, {'$unset': {'mail_threshold': ''}})
                            db.users.update_one({'userid':userid}, {'$set': {'debit_status': False}})
                        #unoaction(checked,'0')
                        flash('Please make sure to Logout')
                        return redirect(url_for('console'))
                    else:
                        flash('Locker already checked out')
                        return redirect(url_for('console'))
                else:
                    flash('Please recharge your Wallet to CheckOut')
                    return redirect(url_for('console'))
            else:
                flash('Unable to reach Server')
                return redirect(url_for('console'))
        if 'logout' in request.form:
            session.pop('log_userid', None)
            session.pop('log_lockers', None)
            return redirect('/')
        return render_template('interface.html',userid=userid,lockers=lockers,private_disabled=private_disabled,public_disabled=public_disabled, creditlog=creditlog, debitlog=debitlog, amount=amount, payable=payable)
    except KeyError:
        return redirect('/login')

@app.route('/reset', methods=['GET','POST'])
def reset():
    try:
        if 'log_user' in session:
            userid = session['res_userid'] = session['log_user']
            session.pop('log_user', None)
            return render_template('validate.html', userid=userid, valid=True, condition='disabled', display=False)
        if 'next' in request.form:
            userid = request.form['userid']
            exists = db.users.find_one({'userid':userid})
            if exists:
                session['res_userid'] = userid
                return render_template('validate.html', userid=userid, valid=True, condition='disabled', display=False)
            else:
                alert = "User don't exist"
                return render_template('validate.html',display=True, userid=userid, alert=alert)
        if 'res_userid' in session:
            if 'check' in request.form:
                userid = session['res_userid']
                dbusername = db.users.find_one({'userid':userid})['username'].lower()
                username = request.form['username'].lower()
                if dbusername == username:
                    return render_template('reset.html',userid=userid)
                else:
                    alert = 'Incorrect Username'
                    return render_template('validate.html', userid=userid, username=username, valid=True, condition='disabled', alert=alert)
            if 'sendotp' in request.form:
                userid = session['res_userid']
                otp = str(random.randint(100000,999999))
                session['res_otp']=otp
                msg = f'Subject: Verification\n\nYour otp for verification is {otp}'
                status = 'OTP Sent'
                output = sendmail(userid,msg,status)
                if output == status:
                    alert = f'{output}'
                    return render_template('reset.html', otpsent=True, userid=userid, alert=alert)
                else:
                    alert = f'{output}'
                    return render_template('reset.html', userid=userid, alert=alert)
            if 'verifyotp' in request.form:
                entered_otp=request.form['otp']
                otp=session['res_otp']
                userid = session['res_userid']
                if(entered_otp == otp):
                    session.pop('res_otp', None)
                    return render_template('changepassword.html')
                else:
                    alert = 'Incorrect OTP. Please try again'
                    return render_template('reset.html',otpsent=True,userid=userid, alert=alert)
            if 'securityquestions' in request.form:
                userid = session['res_userid']
                dbqanda = db.users.find_one({'userid':userid}, {'_id': 0, 'qanda': 1})
                qanda = dbqanda['qanda']
                session['res_qanda'] = qanda
                q1 = qanda['q1']
                q2 = qanda['q2']
                q3 = qanda['q3']
                return render_template('reset.html', answersq=True, userid=userid, q1=q1, q2=q2, q3=q3)
            if 'verifyanswers' in request.form:
                userid = session['res_userid']
                qanda = session['res_qanda']
                a1 = request.form['a1']
                a2 = request.form['a2']
                a3 = request.form['a3']
                session['res_a1'] = a1
                session['res_a2'] = a2
                session['res_a3'] = a3
                if a1.lower().replace(" ", "") == qanda['a1'] and a2.lower().replace(" ", "") == qanda['a2'] and a3.lower().replace(" ", "") == qanda['a3']:
                    session.pop('res_qanda', None)
                    session.pop('res_a1', None)
                    session.pop('res_a2', None)
                    session.pop('res_a3', None)
                    return render_template('changepassword.html')
                else:
                    qanda = session['res_qanda']
                    q1 = qanda['q1']
                    q2 = qanda['q2']
                    q3 = qanda['q3']
                    a1 = session['res_a1']
                    a2 = session['res_a2']
                    a3 = session['res_a3']
                    alert = "Incorrect Answer(s)!"
                    return render_template('reset.html', answersq=True, userid=userid, q1=q1, q2=q2, q3=q3, a1=a1, a2=a2, a3=a3, alert=alert)
            if 'change' in request.form:
                userid = session['res_userid']
                userpass = request.form['userpass']
                db.users.update_one({'userid':userid},{'$set':{'userpass':userpass}})
                msg = 'Subject: Password Reset\n\nYour password has been successfully changed'
                status = 'success'
                output = sendmail(userid,msg,status)
                session.pop('res_userid', None)
                if output == status:
                    return render_template('resetsuccess.html')
                else:
                    alert = f'{output}'
                    return render_template('resetsuccess.html', alert=alert)
        return render_template('validate.html',display=True)
    except KeyError:
        return redirect('/')

@app.route('/testing', methods=['GET','POST'])
def testing():
    userid = 'nishanth.reddym004@gmail.com'
    check = ['1','2']
    checked = db.users.find_one({'userid':user['userid']},{f'checked_in.{locker}': 1 for locker in check})
    table = []
    for locker_num,checkin_time in checked.items():
        table.append([locker_num,checkin_time,datetime.now()])
    return render_template('index.html', table=table)

if(__name__=='__main__'):
    app.run(debug = True)