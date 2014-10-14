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