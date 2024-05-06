import os
import threading
import smtplib
import serial
import time
import serial.tools.list_ports
from datetime import datetime,UTC,timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongodb = os.getenv('MONGODB')
username = os.getenv('MAILUSERNAME')
password = os.getenv('MAILPASSWORD')

mongo = MongoClient(mongodb)
db = mongo.majorproject

def check_locker_connection():
    global lockersport
    lockers_port = [
        p.device
        for p in serial.tools.list_ports.comports()
        if 'USB-SERIAL CH340' in p.description
    ]
    if lockers_port:
        lockersport = lockers_port[0]
    else:
        print('Lockers are disconnected')
        os._exit(0)

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

def mailusername(userid):
    username = db.users.find_one({'userid': userid})['username'].split()
    return username[0]

def servercheck():
    print('Server Started')
    while True:
        if not db.lockers.find_one({})['server']:
            db.lockers.update_one({}, {'$set': {'server': True}})
        check_locker_connection()
        time.sleep(0.1)

def backgroundserver():
    print('Background Server Running')
    try:
        deduction_amount = db.lockers.find_one({})['payable']
    except KeyError:
        db.lockers.update_one({}, {'$set': {'payable': 0.0}})
    while True:
        all_users = db.users.find()
        for user in all_users:
            if 'timestamp' not in user:
                continue
            else:
                userid = user['userid']
                timestamp = user['timestamp'].replace(tzinfo=UTC)
                checked_in_lockers = len(user['checked_in'])
                time_difference = datetime.now(UTC) - timestamp
                minute_difference = int(time_difference.total_seconds() / 60)
                if minute_difference >= 1:
                    debit = minute_difference*deduction_amount*checked_in_lockers
                    deduction = deduction_amount*checked_in_lockers
                    db.users.update_one({'userid':userid}, {'$inc': {'wallet': -debit}})
                    db.users.update_one({'userid':userid}, {'$set': {'debit_status': True}})
                    print(f'₹{debit} debited from {userid} at {datetime.now(UTC) + timedelta(hours=5,minutes=30)}')
                    db.users.update_one({'userid':userid}, {'$set': {'timestamp': datetime.now(UTC)}})
                    dbuser = db.users.find_one({'userid':userid})
                    balance = dbuser['wallet']
                    if balance <= 30 and balance > 0:
                        if 'mail_threshold' not in dbuser:
                            username = mailusername(userid)
                            msg = f'Subject: Low Balance\n\nHi,{username}\n\nPlease recharge your wallet for uninterrupted Checkin and Checkout of your valuables from the lockers,\n\nYou won\'t be able to access Smart Lockers if the balance is less than ₹1.\n\nYour current balance is ₹{balance}'
                            status = f'Low Balance Message sent to {userid} at {datetime.now(UTC) + timedelta(hours=5,minutes=30)}'
                            output = sendmail(userid,msg,status)
                            if output == status:
                                print(output)
                                db.users.update_one({'userid':userid}, {'$set': {'mail_threshold':datetime.now(UTC)}})
                            else:
                                print(output)
                        else:
                            threshold = dbuser['mail_threshold'].replace(tzinfo=UTC)
                            threshold_time = datetime.now(UTC) - threshold
                            threshold_difference = int(threshold_time.total_seconds() / 60)
                            if threshold_difference >= 60:
                                username = mailusername(userid)
                                msg = f'Subject: Low Balance\n\nHi,{username}\n\nPlease recharge your wallet for uninterrupted Checkin and Checkout of your valuables from the lockers,\n\nYou won\'t be able to login to Smart Lockers if the balance is less than ₹1.\n\nYour current balance is ₹{balance}'
                                status = f'Low Balance Message sent to {userid} at {datetime.now(UTC) + timedelta(hours=5,minutes=30)}'
                                output = sendmail(userid,msg,status)
                                if output == status:
                                    print(output)
                                    db.users.update_one({'userid':userid}, {'$set': {'mail_threshold':datetime.now(UTC)}})
                                else:
                                    print(output)
                    elif balance <= 0:
                        if 'zero_balance' not in dbuser:
                            username = mailusername(userid)
                            msg = f'Subject: No Balance\n\nHi,{username}\n\nPlease recharge your wallet to Checkin and Checkout of your valuables from the lockers.\n\nYour current balance is ₹{balance}'
                            status = f'No Balance Message sent to {userid} at {datetime.now(UTC) + timedelta(hours=5,minutes=30)}'
                            output = sendmail(userid,msg,status)
                            if output == status:
                                print(output)
                                db.users.update_one({'userid':userid}, {'$set': {'zero_balance':datetime.now(UTC)}})
                            else:
                                print(output)
                        else:
                            threshold = dbuser['zero_balance'].replace(tzinfo=UTC)
                            threshold_time = datetime.now(UTC) - threshold
                            threshold_difference = int(threshold_time.total_seconds() / 60)
                            if threshold_difference >= 20:
                                username = mailusername(userid)
                                msg = f'Subject: No Balance\n\nHi,{username}\n\nPlease recharge your wallet to Checkin and Checkout of your valuables from the lockers.\n\nYour current balance is ₹{balance}'
                                status = f'No Balance Message sent to {userid} at {datetime.now(UTC) + timedelta(hours=5,minutes=30)}'
                                output = sendmail(userid,msg,status)
                                if output == status:
                                    print(output)
                                    db.users.update_one({'userid':userid}, {'$set': {'zero_balance':datetime.now(UTC)}})
                                else:
                                    print(output)
                    else:
                        db.users.update_one({'userid':userid}, {'$unset': {'mail_threshold': ''}})
                        db.users.update_one({'userid':userid}, {'$unset': {'zero_balance': ''}})
        time.sleep(0.2)

def lockerserver():
    print('Locker Server running')
    while True:
        if db.lockers.find_one({})['locker_actions']:
            locker_actions = db.lockers.find_one({})['locker_actions']
            for i in locker_actions:
                arduino.write(i.encode('utf-8'))
                print(f'Locker action: {i} updating')
                receive = arduino.readline().decode().strip()
                print(f'Locker action: {receive} updated')
                db.lockers.update_one({}, {'$pull': {'locker_actions': i}})
        else:
            continue

if __name__ == "__main__":
    check_locker_connection()
    arduino = serial.Serial()
    arduino.baudrate = 9600
    arduino.port = lockersport
    arduino.open()
    time.sleep(2)
    
    thread1 = threading.Thread(target=servercheck)
    thread2 = threading.Thread(target=backgroundserver)
    thread3 = threading.Thread(target=lockerserver)

    thread1.start()
    thread2.start()
    thread3.start()

    thread1.join()
    thread2.join()
    thread3.join()