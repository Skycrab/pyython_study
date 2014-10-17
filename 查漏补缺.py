1.unicode-escape 与Unicode字面量u""相同的格式
raw-unicode-escape ur""
u"你好" =》 unicode("你好","unicode-escape")

f='\u53eb\u6211'  => unicode码
print(f.decode('unicode-escape'))  

2.marshal struct pickle
Why use struct.pack() for pickling but marshal.loads() for
unpickling?  struct.pack() is 40% faster than marshal.dumps(), but
marshal.loads() is twice as fast as struct.unpack()!

marshal.loads('i'+struct.pack('<i',10)) == 10 #True

__getstate__()返回值应该是字符串，列表，元组，或字典，__setstate__解包接受值

3.python -i 运行脚本后启动交互式(用于调试)
chr ord

4.int类型检查
isinstance(1, numbers.Integral)
class I(object):
    __metaclass__ = ABCMeta
    __slot__ = ()

I.register(int)

isinstance(1, I) #True

5.next(iter,default)
如果有default将不会抛出StopIteration异常
pow(x,y,z) => x**y % z

6.很多人好奇super(type,obj)为啥需要两个参数?
class A(object):
    def show(self):
        print 'a show'

class B(A):
    def show(self):
        print 'b show'


class C(B):
    def show(self):
        super(C,self).show()
        super(B,self).show()


C().show()


7.raise class ,instance 区别

raise Exception == raise Exception()

class MyException(Exception):
    def __init__(self ,name):
        pass

raise MyException 
##TypeError: __init__() takes exactly 2 arguments (1 given)

8.
sys.executable => "c:\\python\\python.exe"



9. python frame, tb


code = 199

def g():
    gname = 999
    f()

def f(n='name'):
    age = 19
    raise ValueError(111)

def h():
    h = 78
    try:
        g()
    except:
        import traceback
        print sys.exc_info()
        b = sys.exc_info()[2]
        print b.tb_next.tb_frame.f_locals  # {'gname': 999}
        print b.tb_next.tb_next.tb_frame.f_locals  # {'age': 19, 'n': 'name'}
        print b.tb_frame.f_locals  # {'h': 78, 'b': <traceback object at 0x02515EE0>}
        print b.tb_frame.f_back.f_locals # 全局{'h': 78, 'b': <traceback object at 0x02515EE0>}

h()

sys._getframe(0) =>返回当前栈
sys._getframe(1) =>返回当前调用栈
sys._current_frames() =>{3420: <frame object at 0x02565F98>} =>(threadid,frame)

10. 
sys.exc_info和sys.last_type区别在于sys.exc_info是线程安全的
sys.exc_clear只清除调用线程特有的信息
sys.getsizeof() == object.__sizeof__() 

11.randon模块中的函数都不是线程安全的，如果要在不同的线程中生成随机数，
应该使用锁防止并发。

12.
collections模块
words1 = defaultdict(list)
words1.append(n)
比dict快
words.setdefault(w,[]).append(n) 

namedtuple的属性访问没有类高效，比类访问速度慢两倍

13.contextlib

class GeneratorContextManager(object):
    """Helper for @contextmanager decorator."""

    def __init__(self, gen):
        self.gen = gen

    def __enter__(self):
        try:
            return self.gen.next()
        except StopIteration:
            raise RuntimeError("generator didn't yield")

    def __exit__(self, type, value, traceback):
        if type is None:
            try:
                self.gen.next() 
            except StopIteration:
                return #正常没有异常将直接返回
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                # Need to force instantiation so we can reliably
                # tell if we get the same exception back
                value = type()
            try:
                self.gen.throw(type, value, traceback)
                raise RuntimeError("generator didn't stop after throw()")
            except StopIteration, exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                #一般来讲，gen
                #try:
                #   pass
                #except:
                #   pass 在这里没有抛出其它的异常，gen.throw将导致fun抛出StopIteration,
                #所以运行到这里
                return exc is not value
            except:
                # only re-raise if it's *not* the exception that was
                # passed to throw(), because __exit__() must not raise
                # an exception unless __exit__() itself failed.  But throw()
                # has to raise the exception to signal propagation, so this
                # fixes the impedance mismatch between the throw() protocol
                # and the __exit__() protocol.
                #
                #如果没有捕获抛出了其它异常，将走到这里，基本上下面是True的，除非你在yield那边捕获
                #gen.throw抛出的value
                if sys.exc_info()[1] is not value:
                    raise

14.datetime模块
d1 = datetime.datetime.now()
d2 = datetime.datetime(2014, 9, 4, 9, 42)
d = d1 - d2
d.days() =>返回的是两者时间差的天数

要返回天数之差可转换为Date
d = d1.date() - d2.date()

15.codecs模块
提供了编解码支持
EncodedFile:
#encoding=utf8
f=open('cs.txt','w')
ff=codecs.EncodedFile(f, 'utf8','gbk') #从utf8->gbk
ff.write("你妹")

#open read()后字符为unicode编码
with codecs.open("cs.txt",'r','gbk') as f: #cs.txt为gbk编码
    g=open('cs2.txt','w')
    g.write(f.read().encode('utf8'))

16.re模块 
{m,n}? 
"\s" => "[\t\r\n\f\v]"

In [27]: r=re.compile(r":(?P<name>.+)")

In [28]: m=r.search("name:lwy")

In [29]: m.expand("hello \g<name>") #命名引用
Out[29]: 'hello lwy'

17.struct模块
In [95]: struct.pack('5p','1234') => p 第一个字节是字符串长度
Out[95]: '\x041234'

struct.pack('0s','1234') => 长度为0的字符串
有时候，必须对齐结构的末尾，可使用该类型的来结束结构格式字符串，重复次数为0
如"llh01" =>l是4字节对齐，由于有h,所以会在最后插入两个填充字节。
这只适用于使用本机大小和对齐方式，标准大小和对齐方式不会强制实施对齐规则。

17.threading _MainThread



# Special thread class to represent the main thread
# This is garbage collected through an exit handler

class _MainThread(Thread):

    def __init__(self):
        Thread.__init__(self, name="MainThread")
        self._Thread__started.set()
        self._set_ident()
        with _active_limbo_lock:
            _active[_get_ident()] = self

    def _set_daemon(self):
        return False

    def _exitfunc(self):
        self._Thread__stop()
        t = _pickSomeNonDaemonThread()
        if t:
            if __debug__:
                self._note("%s: waiting for other threads", self)
        while t:
            t.join()
            t = _pickSomeNonDaemonThread()
        if __debug__:
            self._note("%s: exiting", self)
        self._Thread__delete()

def _pickSomeNonDaemonThread():
    for t in enumerate():
        if not t.daemon and t.is_alive():
            return t
    return None

# Create the main thread object,
# and make it available for the interpreter
# (Py_Main) as threading._shutdown.

_shutdown = _MainThread()._exitfunc



pythonrun.c:

/* Wait until threading._shutdown completes, provided
   the threading module was imported in the first place.
   The shutdown routine will wait until all non-daemon
   "threading" threads have completed. */
static void
wait_for_thread_shutdown(void)
{
#ifdef WITH_THREAD
    PyObject *result;
    PyThreadState *tstate = PyThreadState_GET();
    PyObject *threading = PyMapping_GetItemString(tstate->interp->modules,
                                                  "threading");
    if (threading == NULL) {
        /* threading not imported */
        PyErr_Clear();
        return;
    }
    result = PyObject_CallMethod(threading, "_shutdown", "");
    if (result == NULL)
        PyErr_WriteUnraisable(threading);
    else
        Py_DECREF(result);
    Py_DECREF(threading);
#endif
}


import os
import sys
import Queue
import threading
import urllib2
import time

#threading._VERBOSE = True

class D(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
    def run(self):
        try:
            while  True:
                url = self.queue.get()
                self.download_file(url)
                self.queue.task_done()
        except:
            print sys.exc_info()

    def download_file(self, url):
        h = urllib2.urlopen(url)
        f = os.path.basename(url)+'.html'
        with open(f,'wb') as f:
            while  True:
                c = h.read(1024)
                if not c:
                    break
                f.write(c)

if __name__ == "__main__":
    urls= ['http://www.baidu.com','http://www.sina.com']
    queue = Queue.Queue()
    for i in range(5):
        t = D(queue)
        t.setDaemon(True)
        t.start()

    for u in urls:
        queue.put(u)

    queue.join()
    time.sleep(3)


你可能会很好奇，下载线程的run不是死循环吗，那线程是如何退出的呢？
关键点就是t.setDaemon(True)，将线程设置为守护线程，当queue任务都结束时，主线程结束将强制结束所有子线程，
这也很明显，主线程结束,python将销毁运行时环境，子线程肯定被结束。
所以设置daemon为True不会导致死循环。

当把setDaemon(True)注释掉后，主线程将等待非守护线程的结束，这时将导致死循环。


18. flask cache

python3中引入了__qualname__ 属性，qualified name for class and functions

class Adder(object):
    @cache.memoize()
    def add(self, b):
        return b + random.random()

addr = Adder()
addr.add(2)
此时fname, instance_fname分别为__main__.Adder.add, __main__.Adder.add.__main__.Adderobjectat0x02D642B0
所以不同对象的instance_fname是不一样的，当你cache.delete_memoized(addr.add)时cache会更新instance_fname对应的value值，
并不会更新fname对应的value值。fname和instance_fname对应value值加起来称为version_data，而保存add.add(2)时的key是包含version_data的.
addr1 = Adder()
addr1.add(2)
当删除cache.delete_memoized(addr1.add)时，由于instance_fname改变了，所以version_data也不同，最后导致cache中的key也不同，
所以实现了各个实例的分离

而cache.delete_memoized(Adder.add)时，fname和addr1是相同的，但instance_fname为None，此时就会更新cache中的fname，
调用add1.add时由于version_data与之前不一致，导致缓存失效，实现了当调用类方法是导致所有实例方法的缓存失效。