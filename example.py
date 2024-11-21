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
except Exception:
    print('Some error occured')


gc2 = pyglobalcache.GlobalCache('gc2')
door = gc2.RelayDevice()
status = door.pulse()
print(status)
