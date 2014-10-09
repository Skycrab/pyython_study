flask源码阅读 - 2014/9/24开始

1.首先理解一下request对象
在我们视图中要使用request时只需要from flask import request就可以了
很好奇在多线程的环境下，是如何保证request没有混乱的

在flask.globals.py中
def _lookup_req_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of request context')
    return getattr(top, name)

_request_ctx_stack = LocalStack()
request = LocalProxy(partial(_lookup_req_object, 'request'))
session = LocalProxy(partial(_lookup_req_object, 'session'))

其实可以看到不管request还是session最后都是通过getattr(top, name)获取的，也就是说肯定有一个上下文对象
同时保持request和session。

我们只要一处导入request，在任何视图函数中都可以使用request，关键是每次的都是不同的request对象，说明获取request
对象肯定是一个动态的操作，不然肯定都是相同的request。

这里的魔法就是_lookup_req_object函数和LocalProxy组合完成的，

LocalProxy是werkzeug.local.py中定义的一个代理对象，它的作用就是将所有的请求都发给内部的_local对象

class LocalProxy(object):
    def __init__(self, local, name=None):
        #LocalProxy的代码被我给简化了，这里的local不一定就是local.py中定义的线程局部对象，也可以是任何可调用对象
        #在我们的request中传递的就是_lookup_req_object函数
        object.__setattr__(self, '_LocalProxy__local', local)
        object.__setattr__(self, '__name__', name)

    def _get_current_object(self):
        #很明显，_lookup_req_object函数没有__release_local__
        if not hasattr(self.__local, '__release_local__'):
            return self.__local()
        try:
            return getattr(self.__local, self.__name__)
        except AttributeError:
            raise RuntimeError('no object bound to %s' % self.__name__)
    
    def __getattr__(self, name):
        return getattr(self._get_current_object(), name)

当我们调用request.method时会调用_lookup_req_object，对request的任何调用都是对_lookup_req_object返回对象的调用。

既然每次request都不同，要么调用top = _request_ctx_stack.top返回的top不同，要么top.request属性不同，
在flask中每次返回的top是不一样的，所以request的各个属性都是变化的。


现在需要看看_request_ctx_stack = LocalStack()，LocalStack其实就是简单的模拟了堆栈的基本操作，push,top,pop，内部保存的
线程本地变量是在多线程中request不混乱的关键。

class Local(object):
    __slots__ = ('__storage__', '__ident_func__')

    def __init__(self):
        object.__setattr__(self, '__storage__', {})
        object.__setattr__(self, '__ident_func__', get_ident)
    def __getattr__(self, name):
        return self.__storage__[self.__ident_func__()][name]
简单看一下Local的代码，__storage__为内部保存的自己，键就是thread.get_ident，也就是根据线程的标示符返回对应的值。

下面我们来看看整个交互过程，_request_ctx_stack堆栈是在哪里设置push的，push的应该是我们上面说的同时具有request和session属性的对象，
那这家伙又到底是什么？

flask从app.run()开始
class Flask(_PackageBoundObject):
    def run(self, host=None, port=None, debug=None, **options):
        from werkzeug.serving import run_simple
        run_simple(host, port, self, **options)

使用的是werkzeug的run_simple，根据wsgi规范，app是一个接口，并接受两个参数,即，application(environ, start_response)
在run_wsgi的run_wsgi我们可以清晰的看到调用过程
    def run_wsgi(self):
        environ = self.make_environ()
    
        def start_response(status, response_headers, exc_info=None):
            if exc_info:
                try:
                    if headers_sent:
                        reraise(*exc_info)
                finally:
                    exc_info = None
            elif headers_set:
                raise AssertionError('Headers already set')
            headers_set[:] = [status, response_headers]
            return write

        def execute(app):
            application_iter = app(environ, start_response)
            #environ是为了给request传递请求的
            #start_response主要是增加响应头和状态码，最后需要werkzeug发送请求
            try:
                for data in application_iter: #根据wsgi规范，app返回的是一个序列
                    write(data) #发送结果
                if not headers_sent:
                    write(b'')
            finally:
                if hasattr(application_iter, 'close'):
                    application_iter.close()
                application_iter = None

        try:
            execute(self.server.app)
        except (socket.error, socket.timeout) as e:
            pass

flask中通过定义__call__方法适配wsgi规范，
class Flask(_PackageBoundObject):
    def __call__(self, environ, start_response):
        """Shortcut for :attr:`wsgi_app`."""
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        ctx = self.request_context(environ)
        #这个ctx就是我们所说的同时有request,session属性的上下文
        ctx.push()
        error = None
        try:
            try:
                response = self.full_dispatch_request()
            except Exception as e:
                error = e
                response = self.make_response(self.handle_exception(e))
            return response(environ, start_response)
        finally:
            if self.should_ignore_error(error):
                error = None
            ctx.auto_pop(error)

    def request_context(self, environ):
        return RequestContext(self, environ)
哈哈，终于找到神秘人了，RequestContext是保持一个请求的上下文变量，
之前我们_request_ctx_stack一直是空的，当一个请求来的时候调用ctx.push()将向_request_ctx_stack中push ctx
我们看看ctx.push
class RequestContext(object):
    def __init__(self, app, environ, request=None):
        self.app = app
        if request is None:
            request = app.request_class(environ) #根据环境变量创建request
        self.request = request
        self.session = None

    def push(self):
        _request_ctx_stack.push(self) #将ctx push进 _request_ctx_stack
        # Open the session at the moment that the request context is
        # available. This allows a custom open_session method to use the
        # request context (e.g. code that access database information
        # stored on `g` instead of the appcontext).
        self.session = self.app.open_session(self.request)
        if self.session is None:
            self.session = self.app.make_null_session()

    def pop(self, exc=None):
        rv = _request_ctx_stack.pop()
     
    def auto_pop(self, exc):
        if self.request.environ.get('flask._preserve_context') or \
           (exc is not None and self.app.preserve_context_on_exception):
            self.preserved = True
            self._preserved_exc = exc
        else:
            self.pop(exc)
我们看到ctx.push操作将ctx push到_request_ctx_stack，所以当我们调用request.method时将调用_lookup_req_object
def _lookup_req_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of request context')
    return getattr(top, name)
top此时就是ctx上下文对象，而getattr(top, "request")将返回ctx的request，而这个request就是在ctx的__init__中根据环境变量创建的。
哈哈，明白了吧，每一次调用视图函数操作之前，flask会把创建好的ctx放在线程Local中，当使用时根据线程id就可以拿到了。

在wsgi_app的finally中会调用ctx.auto_pop(error),会根据情况判断是否清除放在_request_ctx_stack中的ctx。

上面是我简化的代码，其实在RequestContext push中_app_ctx_stack = LocalStack()是None，也会把app push进去，对应的
app上下文对象为AppContext。
我们知道flask还有一个神秘的对象g，flask从0.10开始g是和app绑定在一起的(http://flask.pocoo.org/docs/0.10/api/#flask.g)，
g是AppContext的一个成员变量。虽然说g是和app绑定在一起的，但不同请求的AppContext是不同的，所以g还是不同。
也就是说你不能再一个视图中设置g.name，然后再另一个视图中使用g.name，会提示AttributeError


http://linuxlearn.net/news/new/105/14655/

到这里各位小伙伴们都明白了吧，flask以优雅的方式给我们提供了很大的便利，自己做了很多的工作。


2.flask 2014/9/25

#1
在Flask警告:Flask的第一个参数
因为我们大都习惯直接 app = Flask(__name__)，这是由前提的
1.在单独的模块中，可以直接Flask(__name__)
2.在包的__init__.py中也可以直接Flask(__name__)
但是如果是在application/app.py中(application是一个包)就不能直接使用__name__
因为在app.py中的__name__指向的是

#2 flask instance_path概念
一般我们配置config时都会把配置文件放在包下，这是因为默认读取配置文件使用的是root_path
app = Flask(__name__, instance_path='/path/to/instance/folder',instance_relative_config=True)
instance_relative_config为True时配置文件将使用instance_path

#3 flask 信号
信号用来做通知使用，比如当模板渲染完成会通知所有已订阅“模板渲染”这个信号
在flask.signal中
template_rendered = _signals.signal('template-rendered')
当模板渲染完毕后会发送完成信息，app是发送者，其它的是可变参数
template_rendered.send(app, template=template, context=context)

如果想订阅该信号，用connect，record是回调函数，app是信号的发送者，就是说只有app发送的你才接受
template_rendered.connect(record, app)

disconnect取消订阅
template_rendered.disconnect(record, app)


3.flask ext import 原理(2014/10/8)

主要通过sys.meta_path实现的
当导入 from falsk.ext.example import E是将会执行flask/ext/__init__.py
def setup():
    from ..exthook import ExtensionImporter
    importer = ExtensionImporter(['flask_%s', 'flaskext.%s'], __name__)
    importer.install()

install将会向sys.meta_path添加模块装载类，当import时会调用其find_module，如果返回非None,会调用load_module加载

比如当我们 from flask.ext.script import Manager时
会调用find_module('flask.ext.script')，prefinx是flask.ext所以将会调用load_module()
此时将会尝试import flask_script模块或flaskext.script

   def install(self):
        sys.meta_path[:] = [x for x in sys.meta_path if self != x] + [self]

    def find_module(self, fullname, path=None):
        if fullname.startswith(self.prefix):
            return self

    def load_module(self, fullname):
        modname = fullname.split('.', self.prefix_cutoff)[self.prefix_cutoff]
        for path in self.module_choices:
            realname = path % modname
            __import__(realname)

4.flask bootstrap扩展原理
如果app没有做特殊配置的话，将会使用cdn版本，
配置app.config['BOOTSTRAP_SERVE_LOCAL'] = True时，将会使用本地bootstrap

flask_bootstrap是通过blueprint实现的，下面均假设配置了BOOTSTRAP_SERVE_LOCAL=True
<link href="{{bootstrap_find_resource('css/bootstrap.css', cdn='bootstrap')}}">将产生url为
"/static/bootstrap/css/bootstrap.min.css?bootstrap=3.0.3.1"
这里有两点需要注意:

1.前缀地址/static/bootstrap是通过配置static_url_path=app.static_url_path + '/bootstrap'实现的
所以访问该地址时请求会交给前面提到的blutprint处理，那么通过url_for指定的enter_point就需要指明是
bootstrap blueprint的static，这是通过配置local指定的
所以local = StaticCDN('bootstrap.static', rev=True)

2.不做任何配置会加入版本号参数，可通过配置app.config["BOOTSTRAP_QUERYSTRING_REVVING"]=False关闭
但加入版本号有一个最大的好处就是对升级有好处，因为静态文件一帮缓存时间都很长，有了版本号妈妈再也不用担心我的更新升级了。 

5. flask moment原理

    def init_app(self, app):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['moment'] = _moment
        app.context_processor(self.context_processor)

    @staticmethod
    def context_processor():
        return {
            'moment': current_app.extensions['moment']
        }

通过app.context_processor给模板上下文添加了额为属性
def render_template(template_name_or_list, **context):
    ctx.app.update_template_context(context)

在render_template中会把前面注册的变量添加到context,所以在模板中就可以使用moment了，
而flask bootstrap是通过app.jinja_env.globals['bootstrap_find_resource'] = bootstrap_find_resource实现的

我们知道flask在初始化jinja环境的时候就将request,g,session等注入到全局了
rv.globals.update(
            url_for=url_for,
            get_flashed_messages=get_flashed_messages,
            config=self.config,
            # request, session and g are normally added with the
            # context processor for efficiency reasons but for imported
            # templates we also want the proxies in there.
            request=request,
            session=session,
            g=g
        )
但我在看源码时发现_default_template_ctx_processor也会注入g，request，如下
def _default_template_ctx_processor():
    """Default template context processor.  Injects `request`,
    `session` and `g`.
    """
    reqctx = _request_ctx_stack.top
    appctx = _app_ctx_stack.top
    rv = {}
    if appctx is not None:
        rv['g'] = appctx.g
    if reqctx is not None:
        rv['request'] = reqctx.request
        rv['session'] = reqctx.session
    return rv

这不是重复嘛，有啥必要呢？
哈哈，认真看上面rv.globals.update的注释部分能大概明白。
flask模板可以使用宏，需要使用import导入，此时导入的模板不能访问不能访问当前模板的本地变量，只能使用全局变量。
这也就是为什么global中有g,request,session的理由。而本地变量导入g等是为了效率的原因，具体细节需要参考jinja2的文档。

flask moment原理很简单，使用带有时间的格式话字符串在dom加载后，使用moment.js处理一下，
该步操作有moment.include_moment()完成。
如果使用其它语言，如中文，调用moment.lang('zh-cn')
如果使用了flask bootstrap，只需要在最后添加以下代码即可
{% block scripts %}
{{ super() }}
{{ moment.include_moment() }}
{{ moment.lang('zh-cn') }}
{% endblock %}

flask moment还提供了过了多长时间统计，refresh为True时，每分钟刷新一次，refresh也可为具体的刷新时间，单位为分钟
{{ moment(current_time).fromNow(refresh=True) }}


6.flask flash原理
flask flash消息是通过session存放的，get_flashed_messages会从session中取出，并在_request_ctx_stack.top.flashes
上做个拷贝，由于取session中的值需要解码及认证，其它部分使用就可以减少这步操作

flask session =》 csrf token , flash, 


7.flask sqlalchemy
app.config['SQLALCHEMY_ECHO'] = True =》配置输出sql语句
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True =》每次request自动提交db.session.commit(),
通过app.teardown_appcontext注册实现

        @teardown
        def shutdown_session(response_or_exc):
            if app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN']:
                if response_or_exc is None:
                    self.session.commit()
            self.session.remove()
            return response_or_exc
response_or_exc为异常值，默认为sys.exc_info()[1]


重新时BaseQuery对象输出就是sql语句 

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

对db.relationship lazy的理解:
假设role是已经获取的一个Role的实例
lazy:dynamic => role.users不会返回User的列表， 返回的是sqlalchemy.orm.dynamic.AppenderBaseQuery对象
                当执行role.users.all()是才会真正执行sql，这样的好处就是可以继续过滤

lazy:select => role.users直接返回User实例的列表，也就是直接执行sql


db.session.commit只有在对象有变化时才会真的执行update

