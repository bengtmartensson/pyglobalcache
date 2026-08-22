#!/usr/bin/env python3

import logging
import pyglobalcache

logging.basicConfig(level=logging.INFO)
try:
    gc = pyglobalcache.GlobalCache()
    print(gc.getversion())
    tv = gc.IRDevice(2, 1, 'sonytv.txt')
    status = tv.send("ok", 3)
    print(status)
#    answ = gc.getserial()
#    print(answ)
except Exception as ex:
    print('Some error occured')
    print(ex)

gc2 = pyglobalcache.GlobalCache('gc2')
answ = gc2.getserial(1, 1)
print(answ)
#answ = gc2.setserial(1, 1, '19200,FLOW_HARDWARE,PARITY_EVEN')
#print(answ)
#answ = gc2.getserial(1, 1)
#print(answ)
#answ = gc2.setserial()
#print(answ)

oppo = gc2.SerialDevice()
answ = gc2.getserial()
print(answ)
answ = oppo.set('9600,FLOW_NONE,PARITY_NONE')
print(answ)
try:
    answ = oppo.send('EJT', 1)[0]
    print(answ)
except TimeoutError:
    print('*** Timeout ***')

denon = gc2.SerialDevice(2)
answ = gc2.getserial(2, 1)
print(answ)
answ = denon.set('9600,FLOW_NONE,PARITY_NONE')
print(answ)
try:
    answ = denon.send('MV?', 1)[0]
    print(answ)
except TimeoutError:
    print('*** Timeout ***')

gcX = pyglobalcache.GlobalCache('192.168.1.72')
print(gcX.getversion())

door = gc2.RelayDevice()
status = door.pulse()
print(status)
relay = gc2.RelayDevice(3, 2)
print(relay.getstate())
print(relay.toggle())
print(relay.getstate())
