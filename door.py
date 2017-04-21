#!/usr/bin/env python
# -*- coding: utf8 -*-

import time
import pigpio
import sys
import MFRC522
import RPi.GPIO as GPIO
import signal
import MySQLdb
import ConfigParser

# system config
lock_timeout = 15  # timeout in seconds

# servo config
servo_gpio   = 14     # Servos connected to gpio 14
direction    = 1
pulse_width  = 1500
pos_unlocked = 2400
pos_locked   = 800

pi = pigpio.pi() # Connect to local Pi.
pi.set_mode(servo_gpio, pigpio.OUTPUT)

continue_reading = True

config = ConfigParser.ConfigParser()
config.read("door.ini")

def door_lock():
  print("Locking..")
  pi.set_servo_pulsewidth(servo_gpio, pos_locked)
  time.sleep(2)

def door_unlock():
  print("Unlocking.")
  pi.set_servo_pulsewidth(servo_gpio, pos_unlocked)
  time.sleep(2)

# capture SIGINT for cleanup when script is aborted
def end_read(signal,frame):
  global continue_reading
  print ("Ctrl+C captured, ending read, locking door.")
  continue_reading = False;
  door_lock()
  GPIO.cleanup()
  db.close()

# for use with a motion sensor, button, or something else for exiting
# for now, just card swipe out.
def get_inside_input():
  return False

# hook the SIGINT
signal.signal(signal.SIGINT, end_read)

cardreader = MFRC522.MFRC522()

# rotate to locked position when powered on initially
door_lock()

db   = MySQLdb.connect(
  config.get('db', 'server'),
  config.get('db', 'user'),
  config.get('db', 'password'),
  config.get('db', 'database')
)
db.autocommit(True)
curs = db.cursor()

while(continue_reading):
  valid_card = False

  # scan for cards
  (status, TagType) = cardreader.MFRC522_Request(cardreader.PICC_REQIDL)
  (status, uid) = cardreader.MFRC522_Anticoll()

  if status == cardreader.MI_OK:
    uid_string = str(uid[0])+","+str(uid[1])+","+str(uid[2])+","+str(uid[3])
    
    # default key for auth
    key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]

    # select the scanned tag
    cardreader.MFRC522_SelectTag(uid, False)

    status = cardreader.MFRC522_Auth(cardreader.PICC_AUTHENT1A, 8, key, uid)

    if status == cardreader.MI_OK:
      data = cardreader.MFRC522_Read(8, False)
      print(data)
      cardreader.MFRC522_StopCrypto1()
      memberId = ''.join(map(str, data[len(data)/2:]))
      print(memberId)

      try:
        curs.execute("""SELECT account_status, name FROM thelist WHERE id=%s""", (memberId,))
      except Exception as e:
        print ("Error - could not fetch updated date/time from member list for id " + memberId)
        print(str(e))
        
      if curs.rowcount==1:
        account_status, name = curs.fetchone()
        if str(account_status) == 'Active':
          valid_card = True
          curs.execute("""INSERT INTO event_log VALUES (%s, %s, CURRENT_TIMESTAMP)""",(memberId, 'card swipe'))
        else:
          print("status is not 'Active' - is " + str(account_status))
      else:
        print("Could not find member in list")
          

  # @TODO: trigger on inside input
  inside_input = get_inside_input()
  
  if (valid_card or inside_input):
    # @TODO: record video on trigger
    # unlock
    print("Valid input.")
    door_unlock()

    # @TODO: handle door being open - needs a sensor
    # motion sensor, maybe?  When motion stops, assume closed?
    time.sleep(lock_timeout)

    # lock again
    print("Relocking.")
    door_lock()

pi.stop()
