cython学习笔记

1.cdef 与cpdef
C函数定义使用cdef，参数是Python对象也可以是C值，返回值可以使Python对象也可以是值
cdef定义的方法只能在cython中调用
def定义的方法可以再Python和Cython中调用，但由于要经过Python API的处理，所有速度较慢
cpdef既可以在Cython中调用也可以在Python中调用，可以说是两者的结合体，但在Cython内部调用速度略低于cdef

在class中用cdef public int count,则可以通过Python的变量获取count属性，不过由于要涉及多个Python API调用，
比直接cdef要慢很多。此外public不可以用于指针。(class也是如此，添加cdef public class loop，提供python访问loop)

在cdef class中(扩展类型)，def与cdef定义的可以被继承，所以cython需要判断cpdef定义的方法是否被覆盖，这也加剧了cpdef与cdef慢。

cdef double f(double) except? -2 =》 返回-2时就是出错了