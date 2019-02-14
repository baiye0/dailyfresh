from django.shortcuts import render,redirect
from django.views.generic import View
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse
from user.models import User,Address
from goods.models import GoodsSKU
from django.core.mail import send_mail

from celery_tasks.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import re
from itsdangerous import SignatureExpired
from utils.mixin import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django_redis import get_redis_connection
# Create your views here.

# /user/
def register(request):
    '''注册'''
    if request.method == 'GET' :
        return render(request,'register.html')
    else:
        '''进行注册处理 '''
        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据的校验
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 进行业务处理：进行用户注册
        # user = User()
        # user.username = username
        # user.password = password
        # ...
        # user.save()
        user = User.objects.create_user(username, password, email)
        user.is_active = 0
        user.save()
        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))

def register_handle(request):
    '''进行注册处理 '''
    # 接受数据
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')

    # 进行数据的校验
    if not all([username,password,email]):
        return render(request,'register.html',{'errmsg':'数据不完整'})
    # 校验邮箱
    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
        return render(request,'register.html',{'errmsg':'邮箱格式不正确'})

    if allow != 'on':
        return render(request, 'register.html', {'errmsg': '请同意协议'})
    # 校验用户名是否重复
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # 用户名不存在
        user = None
    if user:
        return render(request,'register.html',{'errmsg':'用户名已存在'})
    # 进行业务处理：进行用户注册
    # user = User()
    # user.username = username
    # user.password = password
    # ...
    # user.save()
    user = User.objects.create_user(username,password,email)
    user.is_active = 0
    user.save()
    # 发送激活邮件，包含激活链接 /uesr/active/1
    # 激活链接中需要包含用户的身份信息,并且把身份信息加密
    # 返回应答,跳转到首页
    return redirect(reverse('goods:index'))

class RegisterView(View):
    '''注册'''
    def get(self,request):
        '''显示注册页面'''
        return render(request,'register.html')
    def post(self,request):
        '''进行注册处理'''
        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据的校验
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 进行业务处理：进行用户注册
        # user = User()
        # user.username = username
        # user.password = password
        # ...
        # user.save()
        user = User.objects.create_user(username=username,password=password, email=email)
        user.is_active = 0
        user.save()
        # 发送激活邮件，包含激活链接 /uesr/active/1
        # 激活链接中需要包含用户的身份信息,并且把身份信息加密
        # 加密用户信息，生成激活token
        serializer = Serializer(settings.SECRET_KEY,3600)
        info = {'confirm':user.id}
        token = serializer.dumps(info) # bytes
        token = token.decode()
        # 发邮件
        send_register_active_email.delay(email,username,token)
        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''用户激活'''
    def get(self,request,token):
        '''进行用户激活'''
        # 进行解密，获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取激活用户的id
            user_id = info['confirm']
            #根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 跳转到登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse('激活链接已过期')

# /user/login
class LoginView(View):
    '''登录'''
    def get(self,request):
        '''显示登录页面'''
        # 判断是否记住了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request,'login.html',{'username': username, 'checked': checked})
    def post(self,request):
        '''登录校验'''
        # 接受数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        # 校验数据
        if not all([username,password]):
            return render(request,'login.html',{'errmsg':'数据不完整'})
        # # 业务处理：登录校验
        # User.objects.get(username=username,password=password) # 获取数据库数据
        user = authenticate(username=username,password=password)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户的登录状态
                login(request, user)
                # 获取登陆后所要跳转后的地址
                # 默认跳转到首页
                next_url = request.GET.get('next',reverse('goods:index'))
                # 跳转到next_url
                response =  redirect(next_url)
                remember = request.POST.get('remember')
                # 判断是否记住用户名
                if remember == 'on':
                    response.set_cookie('username',username,max_age=7*24*3600)
                else:
                    response.delete_cookie('username')
                return response

            else:
                # 用户未激活 ，！！！待处理
                return render(request,'login.html',{'errmsg':'账户未激活'})
        else:
            # 用户名或密码错误s
            return render(request,'login.html',{'errmsg':'用户名或密码错误'})
        # 返回应答

# /user/logout
class LogoutView(View):
    '''退出登录'''
    def get(self,request):
        '''退出登录'''
        # 清除用户的session信息
        logout(request)

        # 跳转到首页
        return redirect(reverse('goods:index'))

# /user
class UserInfoView(LoginRequiredMixin,View):
    '''用户中心信息页'''
    def get(self,request):
        '''显示'''
        # page='user'
        # request.user
        # 如果用户未登录->AnonymousUser的一个实例
        # 如果用户登录->User类的一个实例
        # request.user.is_authenticated()
        # 除了给模板文件传递的模板变量之外，django框架会把django.user也传给模板文件
        # 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取用户的历史浏览记录
        # from redis import StrictRedis
        # str = StrictRedis(host='127.0.0.1',port='6379',db=9)

        # 取出用户的历史浏览记录
        con = get_redis_connection('default')
        history_key = 'history_%d' % user.id
        # 获取用户最新浏览的5个商品的id
        print("----"+history_key)
        sku_ids = con.lrange(history_key,0,4)
        print(sku_ids)
        # 从数据库中查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)
        # 遍历获取用户浏览的商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page':'user',
                   'address':address,
                   'goods_li':goods_li}


        return render(request,'user_center_info.html',context)

# /user/order
class UserOrderView(LoginRequiredMixin,View):
    '''用户中心订单页'''
    def get(self,request):
        '''显示'''
        # page='order'
        # 获取用户的订单信息

        return render(request,'user_center_order.html',{'page':'order'})
# /user/order
class AddressView(LoginRequiredMixin,View):
    '''用户中心地址页'''
    def get(self,request):
        '''显示'''
        # 获取用户的默认收货地址
        user = request.user
        # try:
        #     address = Address.objects.get(user=user,is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认收货地址
        #     address = None
        address = Address.objects.get_default_address(user)
        # 使用模板
        return render(request,'user_center_site.html',{'page':'address','address':address})
    def post(self,request):
        '''地址的添加'''
        # 接受数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request,'user_center_site.html',{'errmsg':'数据不完整'})

        # 校验手机号
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$',phone):
            return render(request,'user_center_site.html',{'errmsg':'手机格式不正确'})

        # 业务处理：地址添加
        # 如果用户已存在默认收货地址，添加的地址不作为默认收货地址，否则作为默认收货地址
        user = request.user
        # try:
        #     address = Address.objects.get(user=user,is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        address = Address.objects.get_default_address(user)
        if address:
            is_default = False
        else:
            is_default = True
        # 添加地址
        Address.objects.create(user=user,receiver=receiver,addr=addr,zip_code=zip_code,phone=phone,is_default=is_default)
        # 返回应答,刷新地址页面
        return redirect(reverse('user:address'))# get请求方式

