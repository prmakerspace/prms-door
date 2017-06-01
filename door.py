#!/usr/bin/python2
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
import logging

# system config
lock_timeout = 15  # timeout in seconds
logfile = '/home/pi/prms-door/door.log'

# servo config
servo_gpio   = 15     # Servos connected to gpio 14
pulse_width  = 1500
pos_locked = 2400
pos_unlocked   = 800

pi = pigpio.pi() # Connect to local Pi.
pi.set_mode(servo_gpio, pigpio.OUTPUT)

continue_reading = True

config = ConfigParser.ConfigParser()
config.read("/home/pi/prms-door/door.ini")

logging.basicConfig(
    filename=logfile,
    filemode='a',
    format="%(asctime)s, %(levelname)s: %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)

logging.info('Starting card reader')
logger = logging.getLogger(__name__)

def door_lock():
  logger.debug("Locking..")
  pi.set_servo_pulsewidth(servo_gpio, pos_locked)
  time.sleep(2)

def door_unlock():
  logger.debug("Unlocking.")
  pi.set_servo_pulsewidth(servo_gpio, pos_unlocked)
  time.sleep(2)

# capture SIGINT for cleanup when script is aborted
def end_read(signal,frame):
  global continue_reading
  logger.debug("Ctrl+C captured, ending read, locking door.")
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
 
    logger.debug('read from card uid: %s', uid_string);
   
    # default key for auth
    key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]

    # select the scanned tag
    cardreader.MFRC522_SelectTag(uid, False)

    status = cardreader.MFRC522_Auth(cardreader.PICC_AUTHENT1A, 8, key, uid)

    if status == cardreader.MI_OK:
      data = cardreader.MFRC522_Read(8, False)
      logger.debug('read card data %s', data)
      cardreader.MFRC522_StopCrypto1()
      logger.debug('converting card data to member id')
      try:
        memberId = ''.join(map(str, data[len(data)/2:]))
        logger.debug('read member id %s', memberId)
      except Exception as e:
        logger.debug('Failure of some type parsing card data')
        logger.debug(str(e))
        memberId = 'FAILURE'
        pass

      try:
        curs.execute("""SELECT account_status, name FROM thelist WHERE id=%s""", (memberId,))
      except Exception as e:
        logger.error("Error - could not fetch updated date/time from member list for id " + memberId)
        logger.debug(str(e))
        
      if curs.rowcount==1:
        account_status, name = curs.fetchone()
        if str(account_status) == 'Active':
          valid_card = True
          curs.execute("""INSERT INTO event_log VALUES (%s, %s, CURRENT_TIMESTAMP)""",(memberId, 'card swipe'))
        else:
          logger.info("Member %s status is not 'Active' (is %s)", memberId, str(account_status))
      else:
        logger.info("Could not find member %s in list.", memberId)
          
  # @TODO: trigger on inside input
  inside_input = get_inside_input()
  
  if (valid_card or inside_input):
    # @TODO: record video on trigger
    # unlock
    logger.debug("Valid input.")
    door_unlock()

    # @TODO: handle door being open - needs a sensor
    # motion sensor, maybe?  When motion stops, assume closed?
    time.sleep(lock_timeout)

    # lock again
    door_lock()

pi.stop()
