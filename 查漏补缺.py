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