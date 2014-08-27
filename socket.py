1. [Errno 32] Broken pipe
向一个已经断开的socket写数据导致SIGPIPE

2.阻塞多服务器
import select
import socket

servers_address = (("localhost",80),("localhost",800))
servers = []
for address in servers_address:
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(address)
    s.listen(100)
    servers.append(s)

while 1:
    for s in servers:
        sock, addr = s.accept()
        print addr
        sock.send('hello world\r\n')
        sock.close()

3.select多服务器
import select
import socket

servers_address = (("localhost",80),("localhost",800))
servers = []
for address in servers_address:
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.setblocking(False)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(address)
    s.listen(100)
    servers.append(s)

wlist = []
while 1:
    rl, wl, el = select.select(servers, wlist, servers)
    for r in rl:
        if r in servers:
            s, addr = r.accept()
            s.setblocking(False)
            print addr
            wlist.append(s)
        else:
            print r.getpeername(),r.recv(1024)
    for r in wl:
        r.send('hello world\r\n')
        r.close()
        wlist.remove(r)

4.gevent loop使用
import socket
import gevent
from gevent.core import loop

def f():
    s, address = sock.accept()
    print address
    s.send("hello world\r\n")

loop = loop()
sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sock.bind(("localhost",8000))
sock.listen(10)
io = loop.io(sock.fileno(),1) #1代表read
io.start(f)
loop.run()

5.gevent recv流程
    
    gevent的socket对象被gevent重新封装，原始socket就是下面的self._sock
我们来看看gevent的socket一次recv做了什么操作。
    def recv(self, *args):
        sock = self._sock  # keeping the reference so that fd is not closed during waiting
        while True:
            try:
                return sock.recv(*args) # 1.如果此时socket已经有数据，则直接return
            except error:
                #没有数据将会抛出异常，且errno为EWOULDBLOCK
                ex = sys.exc_info()[1]
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
                # QQQ without clearing exc_info test__refcount.test_clean_exit fails
                sys.exc_clear()
            #此时将该文件描述符的”读事件“加入到loop中
            self._wait(self._read_event)
            """self._wait会调用hub.wait,
                def wait(self, watcher):
                    waiter = Waiter()
                    unique = object()
                    watcher.start(waiter.switch, unique) #这个watcher就是上面说的loop.io()实例，waiter.switch就是回调函数
                    try:
                        result = waiter.get()
                        assert result is unique, 'Invalid switch into %s: %r (expected %r)' % (getcurrent(), result, unique)
                    finally:
                    watcher.stop()
            当loop捕获到”可读事件“时，将会回调waiter.switch方法，此时将回到这里(因为while循环)继续执行sock.recv(*args)
            一般来说当重新recv时肯定是可以读到数据的，将直接返回
            """

    但是数据可能一次没有读完，所以可能会触发多次EWOULDBLOCK，只有recv为空字符串时才代表读取结束
    所以我们看到的经典的获取所有数据：
    buff = []
    while 1:
        s = socket.recv(1024)
        if not s:
            break
        else:
            buff.append(s)
    buff = "".jon(buff)

6.gevent cancel_wait

import gevent
from gevent.core import loop
from gevent.server import StreamServer

def f(s, address):
    print address
    s.send("hello world\r\n")
    print s.recv(1024)
    print s.close()
    print s.recv(124)

def g():
    s = StreamServer(("localhost",8000), f)
    s.serve_forever()

gevent.spawn(g).join()

7.gevent pool的功能实现
每一个greenlet要结束时将回调pool的_discard方法，这是在add时通过greenlet的rawlink(self._discard)注册的。


RLock对同一个greenlet可重入
    

Event提供了一个greenlet去唤醒其它的greenlet机制，在wait中只有flag被设置了(event.set())才会返回，否则会直接回到hub中
继续事件循环。
from gevent.event import Event
e=Event()
e.wait()

这个很明显将会导致无限循环，提示gevent.hub.LoopExit: This operation would block forever
因为在loop中没有事件将导致循环退出，我们可以看看loop的run方法
def run(self):
        assert self is getcurrent(), 'Do not call Hub.run() directly'
        while True:
            #raise Exception(11)
            loop = self.loop
            loop.error_handler = self
            try:
                loop.run()
            finally:
                loop.error_handler = None  # break the refcount cycle
            self.parent.throw(LoopExit('This operation would block forever'))

很明显，只要循环退出就会抛出LoopExit异常

其实gevent的Semaphore和Event并没有大的区别，虽然Semaphore的实现是通过_Semaphore.pyd提供的，
但如果你翻看下源码就会发现，_Semaphore.pyx中没有半点Cython的代码，全都是Python的代码，我想
这么干的出发点应该是想通过pyx加速py代码。


