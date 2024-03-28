import os
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

db = mongo.majorproject
users = db.users

while True:
    all_users = users.find()
    for user in all_users:
        if 'timestamp' not in user:
            continue
        else:
            timestamp = user['timestamp']
            checked_in_lockers = len(user['checked_in'])
            time_difference = datetime.now() - timestamp
            minute_difference = int(time_difference.total_seconds() / 60)
            if minute_difference >= 1:
                users.update_one({'_id': user['_id']}, {'$inc': {'wallet': -(minute_difference*checked_in_lockers)}})
                print(f'Wallet amount debited at {datetime.now()}')
                users.update_one({'_id': user['_id']}, {'$set': {'timestamp': datetime.now()}})
    print(f'Server running, Last run : {datetime.now()}')

if(__name__=='__main__'):
    app.run(debug = True, port = 5002)