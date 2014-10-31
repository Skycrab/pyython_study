#coding:utf-8
'''
Created on 2014-7-18

@author: root
'''
from flask import request, session, redirect
from flask.ext.admin import  BaseView, expose
from flask.ext.admin.contrib.mongoengine import ModelView

from .role import Role

class Login(BaseView):

    def is_visible(self):
        if session.get('auth') == "ok":
            return False
        else:
            return True

    @expose('/')
    def index(self):
        return self.render("login.html")

    @expose('/auth', methods=('GET','POST'))
    def auth(self):
        if request.form.get('name') == "dazhuzai" and request.form.get('passwd') == "9miaodzz":
            session['auth'] = "ok"
            return redirect("/admin/")
        else:
            return redirect("/admin/login")


class AuthView(ModelView):
    def is_accessible(self):
        if session.get('auth') == "ok":
            return True
        else:
            return False


class RoleView(AuthView):
    column_list = ('openid', 'nickname')
    column_filters = ['openid']
    column_searchable_list = ('openid', 'nickname')
    

def init_admin(app):
    app.config['SECRET_KEY'] = '$\xa1<\xadB\xabNg\xa3q\x13\xf5\xfc+W'
    app.config['MONGODB_SETTINGS'] = {'DB': 'testdb'}
    from flask.ext import admin
    admin = admin.Admin(app, '后台管理')
    admin.add_view(Login(name="登录"))
    admin.add_view(RoleView(Role))
 