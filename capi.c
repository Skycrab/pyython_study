一些有用C函数积累

1.
offsetof获取偏移
#define offsetof(type, member) ( (int) & ((type*)0) -> member )
注意最后使用int将地址转换为整数

2.GET_OBJECT 根据一结构体某一成员地址获取整个结构体指针
#define GET_OBJECT(PY_TYPE, EV_PTR, MEMBER) \
    ((struct PY_TYPE *)(((char *)EV_PTR) - offsetof(struct PY_TYPE, MEMBER)))

这出现在gevent源码中，和linux内核中container_of类似，顺序不同而已

比如在gevent中loop = GET_OBJECT(PyGeventLoopObject, watcher, _prepare);
