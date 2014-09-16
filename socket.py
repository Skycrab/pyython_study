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
            pass

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


9.gevent hub

class Hub(greenlet):
    def wait(self, watcher):
        waiter = Waiter()
        unique = object()
        watcher.start(waiter.switch, unique)
        try:
            result = waiter.get()
            assert result is unique, 'Invalid switch into %s: %r (expected %r)' % (getcurrent(), result, unique)
            #这里为什么要assert？
            #因为正常肯定是loop调用waiter.switch(unique),那么waiter.get()获取的肯定是unique,
            #如果不是unique，肯定是有其它地方调用waiter.switch，这很不正常
        finally:
            watcher.stop()

可看如下代码:
def f(t):
    gevent.sleep(t)

p = gevent.spawn(f,2)
gevent.sleep(0) # 2s后libev将回调f，所以下面p.get获取的是2 
switcher = gevent.spawn(p.switch, 'hello') #强先回调p.switch,传递参数hello
result = p.get()

将报如下异常：
AssertionError: Invalid switch into <Greenlet at 0x252c2b0: f(2)>: 'hello' (expected <object object at 0x020414E0>)
<Greenlet at 0x252c2b0: f(2)> failed with AssertionError

10. gevent timeout
用法
Timeout对象有pending属性，判断是是否还未运行

t=Timeout(1)
t.start()
try:
    print 'aaa'
    import time
    assert t.pending == True
    time.sleep(2)
    gevent.sleep(0.1) 
    #注意这里不可以是sleep(0),虽然sleep(0)也切换到hub,定时器也到了，但gevent注册的回调
    #是优先级是高于定时器的(在libev事件循环中先调用callback,然后才是timer)
except Timeout,e:
    assert t.pending == False
    assert e is t #判断是否是我的定时器，和上面的assert一致，防止不是hub调用t.switch
    print sys.exc_info()
finally: #取消定时器，不管定时器是否可用，都可取消
    t.cancel()

Timout对象还提供了with上下文支持:
with Timeout(1) as t:
    assert t.pending
    gevent.sleep(0.5)
assert not t.pending

Timeout第二个参数可以自定义异常，如果是Fasle,with上下文将不传递异常
sys.exc_clear()
with Timeout(1,False) as t:
    assert t.pending
    gevent.sleep(2)
assert not sys.exc_info()[1]
我们看到并没有抛出异常


还有一个with_timeout，
def f():
    import time
    time.sleep(2)
    gevent.sleep(0.1) #不能使用gevent.sleep(0)
    print 'fff'

t = with_timeout(1,f,timeout_value=10)
assert t == 10

注意with_timeout必须有timeout_value参数时才不会抛Timeout异常。

11.gevent switch_out
在gevent中switch_out是和switch相对应的一个概念，当切换到Greenlet时将调用switch方法，
切换到hub时将调用Greenlet的switch_out方法，也就是给Greenlet一个保存恢复的功能。
gevent中backdoor.py(提供了一个python解释器的后门)使用了switch,我们来看看

class SocketConsole(Greenlet):

    def switch(self, *args, **kw):
        self.saved = sys.stdin, sys.stderr, sys.stdout
        sys.stdin = sys.stdout = sys.stderr = self.desc
        Greenlet.switch(self, *args, **kw)

    def switch_out(self):
        sys.stdin, sys.stderr, sys.stdout = self.saved

因为交换环境需要使用sys.stdin,sys.stdout,sys.stderr，所以当切换到我们Greenlet时，把这三个变量都替换成我们自己的
socket描述符，但当要切换到hub时需要恢复这三个变量，所以在switch中先保存，在switch_out中再恢复。

因为Greenlet通过hub.switch切换到hub的，所以在hub.switch中肯定有调用之前Greenlet.switch_out方法。
class Hub(Greenlet):
    def switch(self):
        #我们看到的确是先调用先前的Greenlet.switch_out
        switch_out = getattr(getcurrent(), 'switch_out', None)
        if switch_out is not None:
            switch_out()
        return greenlet.switch(self)

可以通过下面两句话就启动一个python后门解释器：
from gevent.backdoor import BackdoorServer
BackdoorServer(('127.0.0.1', 9000)).serve_forever()

通过telnet,你可以为所欲为。

12.gevent core就是封装了libev,使用了cython的语法，感兴趣童鞋可以好好研究研究。
其实libev是有python的封装pyev(https://pythonhosted.org/pyev/)，不过pyev是使用C来写扩展的，
代码巨复杂。我找到一中文文档，http://dirlt.com/libev.html

http://www.cnblogs.com/wunaozai/p/3950249.html

class loop:
    def __init__(self, object flags=None, object default=None, size_t ptr=0):
        pass

flags: 确定后端使用的异步IO模型,如"select, epoll",可直接字符串也可数字(需参考libev/ev.h)
default：是否使用libev的默认loop,否则将创建一个新的loop

可通过loop.backend确定是否和你设置一致，loop.backend_int返回libev内部对应序号
如：
from gevent import core
flag = "select"
loop=core.loop(flag)
assert loop.backend == flag
assert core._flags_to_int(flag) == loop.backend_int

libev支持的watcher：
所有watcher都通过start启动，并传递回调函数
1.io：
    loop.io(int fd, int events, ref=True, priority=None)
        fd: 文件描述符,可通过sock.fileno()获取
        events: 事件 1:read 2:write 3.read_write

        下面两个参数所有watcher都适用
        ref: 是否增加mainLoop的引用次数，默认是增加的。在libev中watcher.start都会增加引用次数,watcher.stop都会减少引用次数。
            当libev发现引用次数为0，也就没有需要监视的watcher，循环就会退出。
        priority: 设置优先级

2.timer定时器
    loop.timer(double after, double repeat=0.0, ref=True, priority=None)
        after: 多久后启动
        repeat: 多次重复之间间隔
    可通过一下小程序看看:
    def f():
        print time.time()
        print 'eeeee'
    from gevent.core import loop
    l = loop()
    timer = l.timer(2,3) #2秒后启动，3秒后再次启动
    print time.time()
    timer.start(f)
    l.run()

3.signer信号 收到信号处理方式
    loop.signal(int signum, ref=True, priority=None)
hub中有封装signal,使用如下：
def f():
    raise ValueError('signal')
sig = gevent.signal(signal.SIGALRM, f)
assert sig.ref is False
signal.alarm(1)
try:
    gevent.sleep(2)
    raise AssertionError('must not run here')
except ValueError:
    assert str(sys.exc_info()[1]) == 'signal'

和其它watcher不同的是ref默认是False,因为信号并不是必须的，所以循环不需等待信号发生。

4.async 唤醒线程
    loop.async(ref=True, priority=None)
    这主要是通过管道实现的，async.send方法将向管道发送数据，循环检查到读事件唤醒线程.
    hub = gevent.get_hub()
    watcher = hub.loop.async()
    gevent.spawn_later(0.1, thread.start_new_thread, watcher.send, ())
    start = time.time()
    with gevent.Timeout(0.3):
        hub.wait(watcher)

    gevent中线程池中使用了async,当worker线程运行回调函数后，设置返回值，通过async.send唤醒hub主线程

5.fork 子进程事件
    loop.fork(ref=True, priority=None)
    当调用fork时将会回调注册的子进程watcher,但必须得调用libev.ev_loop_fork才有效，
而且要在子进程中使用libev也必须要调用libev.ev_loop_fork
    在gevent的threadpool中使用了fork监视器
    self.fork_watcher = hub.loop.fork(ref=False)
    self.fork_watcher.start(self._on_fork)
    def _on_fork(self):
        # fork() only leaves one thread; also screws up locks;
        # let's re-create locks and threads
        pid = os.getpid()
        if pid != self.pid:
            self.pid = pid
            # Do not mix fork() and threads; since fork() only copies one thread
            # all objects referenced by other threads has refcount that will never
            # go down to 0.
            self._init(self._maxsize)
    回调_on_fork目的就是重新初始化线程池，但是刚才说了子进程要有效必须要调用libev.ev_loop_fork，
这又是在在哪里调用的呢？
if hasattr(os, 'fork'):
    _fork = os.fork

    def fork():
        result = _fork()
        if not result: #子进程
            reinit() #调用libev.ev_loop_fork
        return result
问题的关键就是gevent/os.py中重定义了fork函数,当fork返回0，也就是子进程，将调用reinit
最后真正调用的就是core.pyx的loop.reinit
    def reinit(self):
        if self._ptr:
            libev.ev_loop_fork(self._ptr)

gevent中的线程池在gevent中使用的很广，尤其是windows中，如dns请求，os.read write都是通过线程池，
花点时间看看threadpool.py源码，会收获很多。


5.ev_prepare  每次event loop之前事件
    loop.prepare(ref=True, priority=None)
    还记得上面timeout中说的，在loop中回调比定时器优先级高，在loop中是没有添加回调的，gevent是通过
    ev_prepare实现的，具体实现原理在下面。  


6.ev_check 每次event loop之后事件
    loop.check(ref=True, priority=None)
    这个和ev_prepare刚好相反

7.stat 文件属性变化
    loop.stat(path, float interval=0.0, ref=True, priority=None)
    interval说明期望多久以后libev开始检测文件状态变化

开两个窗口，一个运行该程序，另一个可touch cs.log文件，文件有无也是状态变化
hub = gevent.get_hub()
filename = 'cs.log'
watcher = hub.loop.stat(filename,2) #2s以后才监听文件状态
def f():
    print os.path.exists(filename)
watcher.start(f)
gevent.sleep(100)


我们可以看一下ev_run:

int
ev_run (EV_P_ int flags)
{
  do
    {
      ......
    }
  while (expect_true (
    activecnt
    && !loop_done
    && !(flags & (EVRUN_ONCE | EVRUN_NOWAIT))
  ));

  return activecnt;
}

其中activecnt就是我们上面说的loop的引用计数，所以除非特殊情况ref最好为True。


gevent loop.run_callback实现原理：
    1.loop.run_callback会向loop._callbacks中添加回调
    2.在loop的__init__中初始化prepare: libev.ev_prepare_init(&self._prepare, <void*>gevent_run_callbacks)
        注册回调为gevent_run_callbacks
    3.在gevent_run_callbacks中会调用loop的_run_callbacks
        result = ((struct __pyx_vtabstruct_6gevent_4core_loop *)loop->__pyx_vtab)->_run_callbacks(loop);
    4.loop的_run_callbacks中会逐个调用_callbacks中的回调

这也就是为什么说callback优先级高的原因。

loop.run_callback返回的是一个callback对象，具有stop(),pending属性，也就是说如果回调还没运行，我们可以通过stop()方法停止。
事例代码如下：
def f(a):
    a.append(1)

from gevent.hub import get_hub
loop = get_hub().loop
a= []
f = loop.run_callback(f,a)
f.stop()
gevent.sleep(0)
assert not f.pending #没有阻塞可能是已运行或被停止
assert not a

如果注释掉f.stop(),那么a是[1],因为gevent.sleep(0)也是直接run_callback,肯定是谁先加入谁先调用，
但如果是其它watcher就没有机会调用了。


考虑一下，为什么libev.ev_prepare_init(&self._prepare, <void*>gevent_run_callbacks)回调的是gevent_run_callbacks，
然后最后还是调用loop的_run_callbacks,为什么不直接把_run_callbacks作为回调？
想一想就知道了，因为ev_prepare_init的回调具有固定格式，
# define EV_CB_DECLARE(type) void (*cb)(EV_P_ struct type *w, int revents);








13.gevent threadpool

hub中有一个线程池，大小为10

apply_async 

import gevent
from gevent import get_hub
def g(r):
    print r
pool = get_hub().threadpool
pool.apply_async(f,(6,33),callback=g)
pool.apply_async(f,(2,22),callback=g)
gevent.sleep(10)



14.c-ares

cares.ares_library_init(cares.ARES_LIB_INIT_ALL)
初始化ares库，其实只对windows平台做了处理，主要是为了加载iphlpapi.dll，在非windows平台可不调用。
如果调用一定要在c-ares任何函数之前调用。

cares.ares_library_cleanup()
相对于cares.ares_library_init，在windows平台将释放iphlpapi.dll，非windows平台可不调用。
gevent中并没有调用该函数，作者在__dealloc__中也用？号表明了这一点，我不太理解，可能有更好的理由吧。

cares.ares_destroy(self.channel)
销毁channel，释放内存，关闭打开的socket,这是在__dealloc__中调用

cares.ares_init_options(&channel, &options, optmask)
这是ares中最核心的函数，用于初始化channel,options，optmask主要是通过channel的__init__构造
def __init__(self, object loop, flags=None, timeout=None, tries=None, ndots=None,
                 udp_port=None, tcp_port=None, servers=None):
flags用于控制一查询行为，如ARES_FLAG_USEVC，将只发送TCP请求(我们知道DNS既有TCP也有UDP)
ARES_FLAG_PRIMARY :只向第一个服务器发送请求，还有其它选项参考ares_init_options函数文档
timeout：指明第一次请求的超时时间，单位为秒,c-ares单位为毫秒，gevent会转换，第一次之后的超时c-area有它自己的算法
tries：请求尝试次数，默认4次
ndots：最少'.'的数量，默认是1，如果大于1,就直接查找域名，不然会和本地域名合并(init_by_environment设置本地域名)
udp_port，tcp_port：使用的udp,tcp端口号，默认53
servers：发送dns请求的服务器，见下面ares_set_servers

ndots多说一句，比如ping bifeng(这是我一同事的主机),检测发现没有'.'(也就是小于ndots)，所以会把本地域给加上去
该操作在ares_search.c中ares_search函数中

cares.ares_set_servers(self.channel, cares.ares_addr_node* c_servers)
设置dns请求服务器，设置完成需要free掉c_servers的内存空间，因为ares_set_servers中重新malloc内存空间了。
在set_servers中，通过finally free内存空间
            c_servers = <cares.ares_addr_node*>malloc(sizeof(cares.ares_addr_node) * length)
            if not c_servers:
                raise MemoryError
            try:
                index = 0
                for server in servers:
                    ...
                c_servers[length - 1].next = NULL
                index = cares.ares_set_servers(self.channel, c_servers)
                if index:
                    raise ValueError(strerror(index))
            finally:
                free(c_servers)

#ares.h
struct ares_options {
  int flags;
  int timeout; /* in seconds or milliseconds, depending on options */
  int tries;
  int ndots;
  unsigned short udp_port;
  unsigned short tcp_port;
  int socket_send_buffer_size;
  int socket_receive_buffer_size;
  struct in_addr *servers;
  int nservers;
  char **domains;
  int ndomains;
  char *lookups;
  ares_sock_state_cb sock_state_cb;
  void *sock_state_cb_data;
  struct apattern *sortlist;
  int nsort;
  int ednspsz;
};

def __init__(...)
    options.sock_state_cb = <void*>gevent_sock_state_callback
    options.sock_state_cb_data = <void*>self

