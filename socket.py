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
但如果你翻看下源码就会发现，_Semaphore.pyx中没有半点C的代码，全都是Python的代码，我想
这么干的出发点应该是想通过pyx加速py代码。


8.gevent greenlet分析

class Greenlet(greenlet):
    pass

gevent中所有的parent都是hub,

ready() => 判断是否结束

来看看Greenlet的生命周期：
启动Greenlet需要调用start()方法，
    def start(self):
        """Schedule the greenlet to run in this loop iteration"""
        if self._start_event is None:
            self._start_event = self.parent.loop.run_callback(self.switch)

也就是将当前的switch加入到loop事件循环中。当loop回调self.switch时
将运行run方法(这是底层greenlet提供的),继承时我们可以提供_run方法。
    def run(self):
        try:
            if self._start_event is None:
                self._start_event = _dummy_event
            else:
                self._start_event.stop() #取消之前添加的回调函数，loop将会从回调链中剔除该函数。
                #libev提供了一系列的对象封装，如io,timer,都有start,stop方法
                #而回调是通过loop.run_callback开启的,和其它有所不同
            try:
                result = self._run(*self.args, **self.kwargs) #运行自定义_run方法
            except:
                self._report_error(sys.exc_info())
                return
            self._report_result(result) #设置返回结果，这是个比较重要的方法，下面会单独看看
        finally:
            self.__dict__.pop('_run', None)
            self.__dict__.pop('args', None)
            self.__dict__.pop('kwargs', None)

一切顺利，没有异常将调用_report_result方法，我们具体看看：
    def _report_result(self, result):
        self._exception = None
        self.value = result #设置返回结果，可通过get()获取，注意要获取value时
        #不要直接通过.value，一定要用get方法，因为get()会获取到真正的运行后结果，
        #而.value那是该Greenlet可能还没结束
        if self._links and not self._notifier: #这个是干什么的？
            self._notifier = self.parent.loop.run_callback(self._notify_links)

先不要着急上面那个到底是干什么的，我们看看get()你就明白了？
可能Greenlet还在运行run()时，我们就调用了get()想获取返回结果。

    def get(self, block=True, timeout=None):
        """Return the result the greenlet has returned or re-raise the exception it has raised.

        If block is ``False``, raise :class:`gevent.Timeout` if the greenlet is still alive.
        If block is ``True``, unschedule the current greenlet until the result is available
        or the timeout expires. In the latter case, :class:`gevent.Timeout` is raised.
        """
        if self.ready(): #该Greenlet已经运行结束，直接返回结果
            if self.successful():
                return self.value
            else:
                raise self._exception
        if block: #到这里说明该Greenlet并没有结束
            switch = getcurrent().switch
            self.rawlink(switch) #将当前Greenlet.switch加到自己的回调链中
            """
            self._links.append(callback)
            """
            try:
                t = Timeout.start_new(timeout)
                try:
                    result = self.parent.switch() #切换到hub,可以理解为当前get()阻塞了，当再次回调刚刚注册的switch将回到这里
                    #可问题是好像我们没有将switch注册到hub中，那是谁去回调的呢？
                    #幕后黑手其实就是上面的_report_result，当Greenlet结束最后会调用_report_result，
                    #而_report_result把将_notify_links注册到loop的回调中，最后由_notify_links回调我们刚注册的switch
                    # def _notify_links(self):
                    #     while self._links:
                    #     link = self._links.popleft()
                    #     try:
                    #         link(self) #就是这里了，我们看到还把self传给了switch,所以result结果就是self(greenlet通过switch传递结果)
                    #     except:
                    #         self.parent.handle_error((link, self), *sys.exc_info())
                    assert result is self, 'Invalid switch into Greenlet.get(): %r' % (result, ) 
                    #知道为什么result是self的原因了吧
                finally:
                    t.cancel()
            except:
                # unlinking in 'except' instead of finally is an optimization:
                # if switch occurred normally then link was already removed in _notify_links
                # and there's no need to touch the links set.
                # Note, however, that if "Invalid switch" assert was removed and invalid switch
                # did happen, the link would remain, causing another invalid switch later in this greenlet.
                self.unlink(switch)
                raise
            #运行到这里，其实Greenlet已经结束了，换句话说self.ready()肯定为True
            if self.ready():
                if self.successful():
                    return self.value
                else:
                    raise self._exception
        else: #还没结束，你又不等待，没有值返回啊，只能抛出异常了
            raise Timeout

明白了get你再去看看join,逻辑几乎一样，只是少了返回value值，懂了上面get的逻辑，也就知道了
为什么join能等待Greenlet结束了。






