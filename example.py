#!/usr/bin/env python3
# This is an example file using the pyglobalcache API.
# The commands sent are meaningful for me; they may not meaningful for others ;-).

import logging
import pyglobalcache

logging.basicConfig(level=logging.INFO)
try:
    gc = pyglobalcache.GlobalCache.globalcache('globalcache')
    print(gc.getversion())
    tv = gc.IRDevice(2, 1, 'sonytv.txt')
    ver = tv.getversion()
    print(ver)
    status = tv.send("ok", 3)
    print(status)
    status = tv.send("ok", 3)
    print(status)
    gc.close()

except Exception as ex:
    print('Some error occured', ex)
    print(ex)

gc2 = pyglobalcache.GlobalCache.globalcache('gc2')
print(gc2.getversion())
#pana = gc2.IRDevice(5, 1, 'panasonic.txt')
#print(pana.getversion())
#status = pana.send('power_toggle')
#print(status)
#print(pana.getversion())
print(gc2.getmoduleversion(4))
gc2ir = gc2.IRDevice(4)
print(gc2ir.getversion())

oppo = gc2.SerialDevice(1)
#answ = gc2.getserial(1)
#print(answ)
#answ = gc2.setserial(1, 1, '19200,FLOW_HARDWARE,PARITY_EVEN')
#print(answ)
#answ = gc2.getserial(1, 1)
#print(answ)
#answ = gc2.setserial()
#print(answ)

#answ = oppo.set('9600,FLOW_NONE,PARITY_NONE')
#print(answ)
try:
    answ = oppo.send('EJT', 1)[0]
    print(answ)
    oppo.close()
except TimeoutError:
    print('*** Timeout ***')

denon = gc2.SerialDevice(2)
answ = gc2.getserial(2)
print(answ)
#answ = denon.set('9600,FLOW_NONE,PARITY_NONE')
#print(answ)
try:
    answ = denon.send('MV?', 1)[0]
    print(answ)
    denon.close()
except TimeoutError:
    print('*** Timeout ***')

gcX = pyglobalcache.GlobalCache.globalcache('192.168.1.72')
print(gcX.getversion())
#gcX.close()

door = gc2.RelayDevice()
status = door.pulse()
print(status)
relay = gc2.RelayDevice(3, 2)
state = relay.getstate()
print("Switch 2 is now " + ("on" if state else "off"))
print(relay.toggle())
state = relay.getstate()
print("Switch 2 is now " + ("on" if state else "off"))
gc2.close()
