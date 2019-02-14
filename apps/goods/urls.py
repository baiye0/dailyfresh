from django.conf.urls import url
from goods.views import IndexView,DetailView,ListView

# 在include方法里面指定namespace却不提供app_name是不允许的。
# 在包含的模块里设置app_name变量，或者在include方法里面提供app_name参数
app_name='[goods]'
urlpatterns = [
    url(r'^index$', IndexView.as_view(), name='index'), # 首页
    url(r'^goods/(?P<goods_id>\d+)$',DetailView.as_view(),name='detail'),# 详情页
    url(r'^list/(?P<type_id>\d+)/(?P<page>\d+)$', ListView.as_view(), name='list'), # 列表页
]