#include <EEPROM.h>
#include <Servo.h>

const int lockers = 6;
const int pin = 2;
const int doorlock = 180;
const int doorunlock = 0;
const int keylock = 90;
const int keyunlock = 0;

Servo servo[lockers * 2];

void setup() 
{
  Serial.begin(9600);
  for (int i = 0; i < lockers * 2; i++) 
  {
    servo[i].attach(pin + i);
    servo[i].write(EEPROM.read(i));
  }
}

void lock(int locker, int motor[]) 
{
  for (int j = doorunlock; j <= doorlock; j++) 
  {
    servo[motor[locker] * 2].write(j);
    delay(10);
  }
  delay(200);
  servo[motor[locker] * 2 + 1].write(keylock);
  EEPROM.write(motor[locker] * 2, doorlock);
  EEPROM.write(motor[locker] * 2 + 1, keylock);
}

void unlock(int locker, int motor[]) 
{
  servo[motor[locker] * 2 + 1].write(keyunlock);
  delay(200);
  for (int j = doorlock; j >= doorunlock; j--) 
  {
    servo[motor[locker] * 2].write(j);
    delay(10);
  }
  EEPROM.write(motor[locker] * 2, doorunlock);
  EEPROM.write(motor[locker] * 2 + 1, keyunlock);
}

void loop() 
{
  if (Serial.available() > 0) 
  {
    String receivedserial = Serial.readStringUntil('\n');
    int serial = receivedserial.toInt();
    int inputs = (serial / 10), input, count = 0, clone = inputs;
    bool action = serial % 10;
    while (clone != 0) 
    {
      clone = clone / 10;
      count += 1;
    }
    int motor[count];
    for (int i = 0; i < count; i++) 
    {
      clone = inputs % 10;
      inputs = inputs / 10;
      motor[i] = clone - 1;
    }
    if (action) 
    {
      for (int i = 0; i < count; i++) 
      {
        lock(i, motor);
      }
    } 
    else 
    {
      for (int i = 0; i < count; i++) 
      {
        unlock(i, motor);
      }
    }
    Serial.println(serial);
  }
}