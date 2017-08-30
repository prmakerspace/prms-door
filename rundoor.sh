#! /bin/bash

COUNT="$(pidof /usr/bin/python2 /home/pi/prms-door/door.py | wc -w)"
case $(pidof /usr/bin/python2 /home/pi/prms-door/door.py | wc -w) in
0)  echo "Found no door script running, started a new one:     $(date)" >> /home/pi/prms-door/restart.log
    /usr/bin/python2 /home/pi/prms-door/door.py &
    ;;
1)  # all ok
    ;;
*)  echo "Found $COUNT door scripts, killed one: $(date)" >> /home/pi/prms-door/restart.log
    kill $(pidof /usr/bin/python2 /home/pi/prms-door/door.py | awk '{print $1}')
    ;;
esac
