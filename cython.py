cython学习笔记

windows环境搭建：
安装cython,mingw32

#1.C:\Python27\Lib\distutils\distutils.cfg
[build]
compiler = mingw32

[build_ext]
compiler = mingw32
#2.helloword.pyx
cdef extern from"stdio.h":
    extern int printf(const char *format, ...) 
def SayHello():
    printf("hello,world\n")
#3.setup.py
from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
 
setup(
  name = 'helloworld',
  ext_modules=cythonize([
    Extension("helloworld", ["helloworld.pyx"]),
    ]),
)
#4.python setup.py build --compiler=minigw32


class 文档：
http://docs.cython.org/src/userguide/extension_types.html?highlight=class


1.cdef 与cpdef
C函数定义使用cdef，参数是Python对象也可以是C值，返回值可以使Python对象也可以是值
cdef定义的方法只能在cython中调用
def定义的方法可以再Python和Cython中调用，但由于要经过Python API的处理，所有速度较慢
cpdef既可以在Cython中调用也可以在Python中调用，可以说是两者的结合体，但在Cython内部调用速度略低于cdef

在class中用cdef public int count,则可以通过Python的变量获取count属性，不过由于要涉及多个Python API调用，
比直接cdef要慢很多。此外public不可以用于指针。(class也是如此，添加cdef public class loop，提供python访问loop)

在cdef class中(扩展类型)，def与cdef定义的可以被继承，所以cython需要判断cpdef定义的方法是否被覆盖，这也加剧了cpdef与cdef慢。


cpdef 只用于函数(可实现复写)

cdef class Function:
    cpdef double evaluate(self, double x) except *:
        return 0

cdef class SinOfSquareFunction(Function):
    cpdef double evaluate(self, double x) except *:
        return sin(x**2)

2.cimport cython
@cython.boundscheck(False) => 关闭负数下标处理
@cython.wraparound(False) => 关闭越界检查

3.
pyd 头文件 cimport
pyi include文件 include "spamstuff.pxi"

4.
cdef char *s
s = pystring1 + pystring2 XXXX
这回产生临时变量，导致s悬疑指针

p = pystring1 + pystring2
s = p

5.内型转换
<type>a 这并不检查，直接转换
<type*>a 会检查

6.
cdef int spam() except -1 =》spam发生错误将返回-1

cdef int spam() except? -1 =》-1仅仅是可能错误，
如果返回-1，cython会调用PyErr_Occurred去判断是否有异常

cdef int spam() except * =》cython每次都会调用yErr_Occurred

7.编译时定义
DEF FavouriteFood = "spam"
DEF ArraySize = 42
DEF OtherArraySize = 2 * ArraySize + 17

cdef int a1[ArraySize]
cdef int a2[OtherArraySize

8.条件语句
IF UNAME_SYSNAME == "Windows":
    include "icky_definitions.pxi"
ELIF UNAME_SYSNAME == "Darwin":
    include "nice_definitions.pxi"
ELIF UNAME_SYSNAME == "Linux":
    include "penguin_definitions.pxi"
ELSE:
    include "other_definitions.pxi"

9.cdef extern
如果你需要包括一个头文件，这个头文件是别的头文件所要的，但是不想使用其中的任何声明，那么只要在后面的代码块中填上pass就行了，如：
cdef extern from “spam.h”:
    pass
如果你想包括一些外部的声明，但不想指定头文件，因为它们所在的头文件，你已经在其它地方包括了，在头文件名的地方你可以使用*来代替。例如：
cdef extern from *:

10. forward declaration 解决互相引用
cdef class Shrubbery # forward declaration

cdef class Shrubber:
    cdef Shrubbery work_in_progress

cdef class Shrubbery:
    cdef Shrubber creator


如果有基类，也需要指出: cdef class Shrubbery(Basebery)

11.创建对象
cdef class P:
    cdef object food

    def __cinit__(self, food):
        print 'cinit'
        print food
        self.food = food

    def __init__(self, food):
        print("eating!")
        print food

P('fish') => __cinit__和__init__都会调用
P.__new__(P,'fish') =>只会调用__cinit__

如果需要多个实例，可以使用cython.freelist

cimport cython

@cython.freelist(8)
cdef class Penguin:
    cdef object food
    def __cinit__(self, food):
        self.food = food

penguin = Penguin('fish 1')
penguin = None
penguin = Penguin('fish 2')  # does not need to allocate memory!


public class需要使用名字制定从句(Name specification clause)定义[object object_struct_name, type type_object_name ]

因为是public，说明其它的C需要使用，所以需要定义object_struct_name以生成相对应的结构体,以及type_object_name生成对应的type类型

cdef public class Person [object PPerson, type PPType]:
    cdef public int age
    def __init__(self, object age):
        self.age = age

对应的会生成如下.h(.c)文件：
struct PPerson {
  PyObject_HEAD
  int age;
};

DL_EXPORT(PyTypeObject) PPType = {
  PyVarObject_HEAD_INIT(0, 0)
  __Pyx_NAMESTR("helloworld.Person"), /*tp_name*/
  sizeof(struct PPerson), /*tp_basicsize*/
  0, /*tp_itemsize*/
  __pyx_tp_dealloc_10helloworld_Person, /*tp_dealloc*/
  0, /*tp_print*/
  0, /*tp_getattr*/
  0, /*tp_setattr*/
  ...
}





Cython优化笔记(http://wiki.sagemath.org/WritingFastPyrexCode)
 
1.Type checking
使用PyObject_TypeCheck(x, X) 代替isinstance(x, X)