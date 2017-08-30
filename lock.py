#!/usr/bin/python2
#!/usr/bin/env python
# -*- coding: utf8 -*-

import time
import pigpio
import sys
import RPi.GPIO as GPIO
import signal
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

config = ConfigParser.ConfigParser()
config.read("/home/pi/prms-door/door.ini")

logging.basicConfig(
    filename=logfile,
    filemode='a',
    format="%(asctime)s, %(levelname)s: %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.debug("Manually locking..")
pi.set_servo_pulsewidth(servo_gpio, pos_locked)
time.sleep(2)
