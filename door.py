#!/usr/bin/env python
# -*- coding: utf8 -*-

import time
import pigpio
import sys
sys.path.append('../MFRC522-python')
import MFRC522
import RPi.GPIO as GPIO
import signal

# servo config
servo_gpio   = 14     # Servos connected to gpio 14
direction    = 1
pulse_width  = 1500
pos_unlocked = 2400
pos_locked   = 800

pi = pigpio.pi() # Connect to local Pi.
pi.set_mode(servo_gpio, pigpio.OUTPUT)

continue_reading = True

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
  print "Ctrl+C captured, ending read, locking door."
  continue_reading = False;
  door_lock()
  GPIO.cleanup()

# hook the SIGINT
signal.signal(signal.SIGINT, end_read)

cardreader = MFRC522.MFRC522()

# rotate to locked position when powered on initially
door_lock()

while(continue_reading):
  valid_card = False

  # scan for cards
  (status, TagType) = cardreader.MFRC522_Request(cardreader.PICC_REQIDL)

  if status == cardreader.MI_OK:
    print "Card detected"  

  (status, uid)     = cardreader.MFRC522_Anticoll()

  if status == cardreader.MI_OK:
    uid_string = str(uid[0])+","+str(uid[1])+","+str(uid[2])+","+str(uid[3])
    
    # default key for auth
    key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]

    # select the scanned tag
    cardreader.MFRC522_SelectTag(uid)

    status = cardreader.MFRC522_Auth(cardreader.PICC_AUTHENT1A, 8, key, uid)

    # @TODO: lookup info in db
    if status == cardreader.MI_OK:
      cardreader.MFRC522_Read(8)
      cardreader.MFRC522_StopCrypto1()
      valid_card = True

  # @TODO: trigger on motion sensor
  motion_sensor = False
  
  if (valid_card or motion_sensor):
    # @TODO: record video on trigger
    # unlock
    print("Valid input.")
    door_unlock()

    # @TODO: handle door being open - needs a sensor
    # motion sensor, maybe?  When motion stops, assume closed?
    time.sleep(30)

    # lock again
    print("Relocking.")
    door_lock()

pi.stop()
