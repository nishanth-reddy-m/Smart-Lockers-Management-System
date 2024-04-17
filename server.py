import os
import atexit
import smtplib
from datetime import datetime
#import serial
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongodb = os.getenv('MONGODB')
username = os.getenv('MAILUSERNAME')
password = os.getenv('MAILPASSWORD')

#arduino = serial.Serial('COM5',9600)

mongo = MongoClient(mongodb)
db = mongo.majorproject

def servercleanup():
    db.lockers.update_one({}, {'$set': {'server': False}})
    mongo.close()
    print(f'Server Stopped')

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

atexit.register(servercleanup)

db.lockers.update_one({}, {'$set': {'server': True}})
print('Server Started')
deduction_amount = db.lockers.find_one({})['payable']
while True:
    all_users = db.users.find()
    for user in all_users:
        if 'timestamp' not in user:
            continue
        else:
            userid = user['userid']
            timestamp = user['timestamp']
            checked_in_lockers = len(user['checked_in'])
            time_difference = datetime.now() - timestamp
            minute_difference = int(time_difference.total_seconds() / 60)
            if minute_difference >= 1:
                debit = minute_difference*deduction_amount*checked_in_lockers
                deduction = deduction_amount*checked_in_lockers
                db.users.update_one({'userid':userid}, {'$inc': {'wallet': -debit}})
                db.users.update_one({'userid':userid}, {'$set': {'debit_status': True}})
                print(f'₹{debit} debited from {userid} at {datetime.now()}')
                db.users.update_one({'userid':userid}, {'$set': {'timestamp': datetime.now()}})
                dbuser = db.users.find_one({'userid':userid})
                balance = dbuser['wallet']
                if balance <= 30:
                    if 'mail_threshold' not in dbuser:
                        msg = f'Subject: Low Balance\n\nPlease recharge your wallet for uninterrupted Checkin and Checkout of your valuables from the lockers,\n\nYou won\'t be able to login to Smart Lockers if the balance is less than ₹1.\n\nYour current balance is ₹{balance}'
                        status = f'Low Balance Message sent to {userid} at {datetime.now()}'
                        output = sendmail(userid,msg,status)
                        if output == status:
                            print(output)
                            db.users.update_one({'userid':userid}, {'$set': {'mail_threshold':datetime.now()}})
                        else:
                            print(output)
                    else:
                        threshold = dbuser['mail_threshold']
                        threshold_time = datetime.now() - threshold
                        threshold_difference = int(threshold_time.total_seconds() / 60)
                        if threshold_difference >= 60:
                            msg = f'Subject: Low Balance\n\nPlease recharge your wallet for uninterrupted Checkin and Checkout of your valuables from the lockers,\n\nYou won\'t be able to login to Smart Lockers if the balance is less than ₹1.\n\nYour current balance is ₹{balance}'
                            status = f'Low Balance Message sent to {userid} at {datetime.now()}'
                            output = sendmail(userid,msg,status)
                            if output == status:
                                print(output)
                                db.users.update_one({'userid':userid}, {'$set': {'mail_threshold':datetime.now()}})
                            else:
                                print(output)