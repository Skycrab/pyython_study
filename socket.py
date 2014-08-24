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





