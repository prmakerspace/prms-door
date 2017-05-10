#!/usr/bin/env python
# -*- coding: utf8 -*-

# if no params, writes list of members without cards
# if --full param, writes list of all members in system, shames member
# if id param, writes id of member without a card to the next card
# if id and --replace, writes id of member replacement card to next card, shames member

import RPi.GPIO as GPIO
import MFRC522
import signal
import MySQLdb
import ConfigParser
import argparse
import sys

continue_reading = True

# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    global continue_reading
    print "Ctrl+C captured, ending read."
    continue_reading = False
    GPIO.cleanup()

# hook up the argparser
parser = argparse.ArgumentParser()
parser.add_argument(
    '--full',
    help='Show all members, including members who already have cards.',
    action="store_true",
    default=False
)
parser.add_argument(
    '--replace',
    help='Replace a card for a member; suggested donation $10.',
    action="store_true",
    default=False
)
parser.add_argument('id', help='Member id to write to card.', default=None, nargs='?')

args = parser.parse_args()

# parse the config:
config = ConfigParser.ConfigParser()
config.read("/home/pi/prms-door/door.ini")

# connect the database
db   = MySQLdb.connect(
  config.get('db', 'server'),
  config.get('db', 'user'),
  config.get('db', 'password'),
  config.get('db', 'database')
)
db.autocommit(True)
curs = db.cursor()

# no id, show list
if not args.id:
    query = 'SELECT id as member_id, name, account_status as status FROM thelist'
    if not args.full:
        query += ' WHERE has_card = 0'

    curs.execute(query)

    if curs.rowcount:
        print("ID\t\tName\t\t\tStatus")
    result = curs.fetchall()
    for row in result:
        print(str(row[0]) + "\t" + row[1] + "\t\t" + row[2])

    print("Use -h to show all options.")

    sys.exit()

# id, verify and write card
query = """SELECT account_status, has_card, name FROM thelist WHERE id = %s"""
if not args.replace:
    query += " AND has_card = 0"

curs.execute(query, (args.id))

if curs.rowcount != 1:
    print "Error - invalid id.  " + str(curs.rowcount) + " members found."
    sys.exit()

status, has_card, name = curs.fetchone()

if str(status) != 'Active':
    print("User's membership status is currently " + str(status) + ", cannot create card.")
    sys.exit()    

if has_card:
    print("Replacing a card for " + name + " again?  Please request a $10 donation to cover the cost.")
    
# valid id, replacement is flagged appropriately, let's write the card
print("Ready - please swipe the new card.")

# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)

# Create an object of the class MFRC522
cardreader = MFRC522.MFRC522()

# This loop keeps checking for chips. If one is near it will get the UID and authenticate
while continue_reading:
    
    # Scan for cards    
    (status,TagType) = cardreader.MFRC522_Request(cardreader.PICC_REQIDL)

    # If a card is found
    if status == cardreader.MI_OK:
        print "Card detected, preparing to write."
    
    # Get the UID of the card
    (status,uid) = cardreader.MFRC522_Anticoll()

    # If we have the UID, continue
    if status == cardreader.MI_OK:

        # Print UID
        #print "Card read UID: "+str(uid[0])+","+str(uid[1])+","+str(uid[2])+","+str(uid[3])
    
        # This is the default key for authentication
        key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
        
        # Select the scanned tag
        cardreader.MFRC522_SelectTag(uid, False)

        # Authenticate
        card_status = cardreader.MFRC522_Auth(cardreader.PICC_AUTHENT1A, 8, key, uid)

        # Check if authenticated
        if card_status == cardreader.MI_OK:
            # Variable for the data to write
            data = []

            # Fill the data with 0xFF
            for x in range(0,8):
                data.append(0xFF)

            for i in args.id:
                data.append(int(i))

            cardreader.MFRC522_Write(8, data, False)

            #read data to confirm
            data = cardreader.MFRC522_Read(8, False)
            cardreader.MFRC522_StopCrypto1()
            memberId = ''.join(map(str, data[len(data)/2:]))

            if memberId != args.id:
                print "Write error; unable to confirm member id written properly.  Please try again."
                print "Expected: " + args.id + "\t\tFound: " + memberId
                print "If this error continues, please file a bug."
                sys.exit()
            
            curs.execute("""INSERT INTO event_log VALUES (%s, %s, CURRENT_TIMESTAMP)""",(args.id, 'card written'))
            curs.execute ("""UPDATE thelist SET has_card=true, last_updated=CURRENT_TIMESTAMP WHERE id=%s""",(args.id))
            db.commit()
            print("Id " + memberId + " for '" + name + "' confirmed written to card.")

            # Make sure to stop reading for cards
            continue_reading = False
            db.close()
        else:
            print "Card authentication error - status: "+str(card_status)
