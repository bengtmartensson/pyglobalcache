import logging
import pyglobalcache

logging.basicConfig(level=logging.INFO)
try:
    gc = pyglobalcache.GlobalCache()
    print(gc.getversion())
    tv = gc.IRDevice(2, 1, 'sonytv.txt')
    status = tv.send("ok", 3)
    print(status)
    status = tv.send("ok", 3)
    print(status)
    answ = gc.getserial(3,1)
    print(answ)
except Exception:
    print('Some error occured')

gc2 = pyglobalcache.GlobalCache('gc2')
answ = gc2.getserial(2, 1)
print(answ)
door = gc2.RelayDevice()
status = door.pulse()
print(status)
