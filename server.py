import os
import threading
import smtplib
import serial
import time
import serial.tools.list_ports
from datetime import datetime
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

def servercheck():
    print('Server Started')
    while True:
        if not db.lockers.find_one({})['server']:
            db.lockers.update_one({}, {'$set': {'server': True}})
        check_locker_connection()
        time.sleep(0.1)

def backgroundserver():
    print('Background Server Running')
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
        time.sleep(0.2)

def lockerserver():
    print('Locker Server running')
    while True:
        if db.lockers.find_one({})['locker_actions']:
            locker_actions = db.lockers.find_one({})['locker_actions']
            for i in locker_actions:
                arduino.write(i.encode('utf-8'))
                receive = arduino.readline().decode().strip()
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