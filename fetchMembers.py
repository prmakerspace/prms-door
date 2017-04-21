import WaApi
import urllib.parse
import json
import MySQLdb
from datetime import datetime
import calendar
import time
import sys
import configparser

def get_new_members():
    params = {'$filter': 'member eq true',
              '$select': '\'DisplayName\', \'Email\', \'Member ID\', \'Membership status\'',
              '$async': 'false'}
    request_url = contactsUrl + '?' + urllib.parse.urlencode(params)
#    print(request_url)
    return api.execute_request(request_url).Contacts

# if the member was updated more recently than we have on record, update the local database
# check to see if the member exists locally by
# fetch the local last_modified field
# if the remote last_modified is newer than the local last_modified, update the account
# if the local last_modified is not detected (no rows returned) insert the account

def update_member_db(contact):
    # pull off last : from time format
    time_format = '%Y-%m-%dT%H:%M:%S%z'
    k = contact.FieldValues[0].Value.rfind(':')
    server_formatted = contact.FieldValues[0].Value[:k]+contact.FieldValues[0].Value[k+1:]

    # and sometimes it has a decimal in the seconds value - remove if present
    if "." in server_formatted:
        decimal_pos = server_formatted.rfind('.')
        dash_pos = server_formatted.rfind('-')

        server_formatted = server_formatted[:decimal_pos]+server_formatted[dash_pos:]

    # convert last modified to unix time in UTC for comparison and storage
    server_modified = datetime.strptime(server_formatted, time_format)
    unixtime = server_modified.timestamp()

    try:
        contactId = str(contact.Id)
        curs.execute("""SELECT last_modified, account_status FROM thelist WHERE id=%s""", (contactId,))
    except Exception as e:
        print ("Error - could not fetch updated date/time from member list for id " + str(contact.Id))
        print(str(e))

    # if the user already exists, update status if out of date
    if curs.rowcount:
        last_modified, account_status = curs.fetchone()

        # update if out of date or if status has changed
        if account_status != contact.FieldValues[5].Value.Value or str(last_modified) < str(server_modified):
            curs.execute ("""UPDATE thelist SET account_status=%s, last_modified=from_unixtime(%s), last_updated=CURRENT_TIMESTAMP WHERE id=%s""",
                (contact.FieldValues[5].Value.Value, unixtime, contactId,))

    # if new user, insert record
    else:
        # id, name, email, account_status, has_card, last_modified, last_update
        try:
            curs.execute(
                """INSERT INTO thelist VALUES (%s, %s, %s, %s, %s, from_unixtime(%s), CURRENT_TIMESTAMP)""",
                (str(contact.Id),
                contact.DisplayName,
                contact.Email,
                contact.FieldValues[5].Value.Value,
                0, # does not have card if new member
                unixtime,
                )
            )
        except Exception as e:
            print ("ohcrap - fail insert: " + str(e))
            print(contact)


config = configparser.ConfigParser()
config.read('door.ini')

# How to obtain application credentials:
# https://help.wildapricot.com/display/DOC/API+V2+authentication#APIV2authentication-Authorizingyourapplication
api = WaApi.WaApiClient(config['wa']['client'], config['wa']['key'])
api.authenticate_with_contact_credentials(config['wa']['user'], config['wa']['password'])
accounts = api.execute_request("/v2/accounts")
account = accounts[0]

# print('Fetching data from '+account.PrimaryDomainName)

contactsUrl = next(res for res in account.Resources if res.Name == 'Contacts').Url

# get new  members and print their details
contacts = get_new_members()
db   = MySQLdb.connect(
  config['db']['server'],
  config['db']['user'],
  config['db']['password'],
  config['db']['database']
)
db.autocommit(True)
curs = db.cursor()

if len(contacts) > 0:
    for contact in contacts:
        update_member_db(contact)
#        print_contact_info(contact)
else:
    print('No members found.')

db.close()
