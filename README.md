# prms-door
Powell River Makerspace Door Project

RFID door lock for our Makerspace

Required features:
1.  current access control (keys) still work
1.  members can scan an rfid card/key fob; door unlocks
1.  the door can be unlocked from inside
1.  new members are added by entering the key card id into the member database manually

Optional features:
1.  door can be unlocked from inside without a rfid key/card
1.  list of members is updated from our website
  * non-paying members are removed from the list automatically
1.  there's a way to scan new members into the system
1.  the door knows it's open 
  * and won't lock until closed
  * and will alarm if left open, until a card is swiped
1.  there's a camera connected
  * that takes video when the card is swiped?
  * that takes video when the door is opened?
  * that allows people to see if there's anybody in the Makerspace
  * that can be used for training machine learning to see if there's anybody in the space
