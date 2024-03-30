import os
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
users = db.users
lockers = db.lockers
deduction_amount = 0.5

def sendmail(userid,balance):
    msg = f'Subject: Low Balance\n\nPlease recharge your wallet for uninterrupted Checkin and Checkout of your valuables from the lockers,\n\nYou won\'t be able to login to Smart Lockers if the balance is less than ₹1.\n\nYour current balance is ₹{balance}'
    message = msg.encode('utf-8')
    try:
        server = smtplib.SMTP('smtp.gmail.com',587)
        server.starttls()
        server.login(username,password)
        server.sendmail(username,userid,message)
        print(f'Low Balance Message sent to {userid} at {datetime.now()}')
        server.close()
    except Exception as e:
        print(f'Failed to send email: {str(e)}')

try:
    lockers.update_one({}, {'$set': {'server': True}})
    print('Server Started')
    while True:
        all_users = users.find()
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
                    users.update_one({'userid':userid}, {'$inc': {'wallet': -debit}})
                    print(f'₹{debit} debited from {userid} at {datetime.now()}')
                    users.update_one({'userid':userid}, {'$set': {'timestamp': datetime.now()}})
                    dbuser = users.find_one({'userid':userid})
                    balance = dbuser['wallet']
                    if balance <= 30:
                        if 'mail_threshold' not in dbuser:
                            sendmail(userid,balance)
                            users.update_one({'userid':userid}, {'$set': {'mail_threshold':datetime.now()}})
                        else:
                            threshold = dbuser['mail_threshold']
                            threshold_time = datetime.now() - threshold
                            threshold_difference = int(threshold_time.total_seconds() / 60)
                            if threshold_difference >= 60:
                                sendmail(userid,balance)
                                users.update_one({'userid':userid}, {'$set': {'mail_threshold':datetime.now()}})
finally:
    lockers.update_one({}, {'$set': {'server': False}})
    print(f'Server Stopped')
    exit()