#!/usr/bin/python3
"""
SakuraNami <39543214+SakuraNami@users.noreply.github.com>
微博超话签到模块
需要安装的依赖 在青龙面板 依赖管理 Python3 中添加
requests 和 ServerPush
需要抓包 微博国际版app - 我的 - 关注的超话 - 往下拉一段 刷新翻页 如果超话数量不多 打开了应该也可以
找到以 https://api.weibo.cn/2/cardlist? 开头的链接
填写在青龙环境变量里 变量名 topic_sc 有多个账号就添加多个
如果在本地运行 需要修改第 25 行 user_list = None
将 None 改为你的ck 如果有多个 ck 使用 & 连接
cron定时规则 参考 0 0 12 * * ? （每天中午12点运行）
命令 task topic.py
拉取 ql raw https://raw.githubusercontent.com/SakuraNami/auto/master/weibo/topic.py
"""
import os
import re
import sys
import ServerPush
from time import sleep
from requests import get, post


# 获取账号
user_list = None

# 延时设定（每个超话签到完成后的等待时间）
sleep_time = 3
# 是否发送通知 默认关闭
send_notify = False
# Bark_token
Bark_token = os.environ.get('Bark_token')
# 通知发送渠道
if send_notify and Bark_token:
    Push = ServerPush.Bark(Bark_token)
else:
    send_notify = False
# 以上部分 请按需求修改


# 以下部分 若非必要 不建议修改
class Topic:
    def __init__(self, cookie: str):
        self.ck = cookie
        self.headers = {
            'Accept': '*/*',
            'Host': 'api.weibo.cn',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'WeiboOverseas/4.5.4 (iPhone; iOS 15.1; Scale/3.00)',
            'Accept-Language': 'zh-Hans-CN;q=1',
            'X-Sessionid': 'F5128B9D-9E5E-4CBC-B302-1986AFAC36CE',
        }
        self.api = 'https://api.weibo.cn'

    @staticmethod
    def format_ck(ck: str):
        params = {
            'aid': '',
            'c': '',
            'containerid': '',
            'extparam': '',
            'from': '',
            'gsid': '',
            'i': '',
            'lang': '',
            'page': '',
            's': '',
            'ua': '',
            'v_f': '',
            'v_p': '',
            'since_id': ''
        }
        text = ck[ck.find('cardlist?') + len('cardlist?'):len(ck)]
        for i, value in enumerate(text.split('&')):
            params[value[0:value.find('=')]] = value[value.find('=') + 1:len(value)]
        params['containerid'] = '100803_-_followsuper'
        return params

    def get_follow_topic_list(self, time: int = 3):
        page = '1'
        follow_list = []
        data = self.format_ck(self.ck)
        data['since_id'] = ''
        url = 'https://api.weibo.cn/2/cardlist'
        while True:
            sleep(time)
            data['v_f'] = page
            data['page'] = page
            r = get(url, params=data, headers=self.headers)
            if r.json().get('errno') == -100:
                print('参数已失效')
                break
            elif r.json().get('errno') == -200:
                print('参数不存在')
                break
            for index in range(len(r.json()['cards'])):
                if 'card_group' in r.json()['cards'][index]:
                    card_group = r.json()['cards'][index]['card_group']
                    for value in card_group:
                        if value["card_type"] == '8':
                            follow_list.append(
                                {
                                    'title_sub': value['title_sub'],
                                    'title_level': value["desc1"][
                                                   value["desc1"].find("LV"): len(value["desc1"])],
                                    'sort_level':
                                        int(value["desc1"][value["desc1"].find(".") + 1: len(value["desc1"])]),
                                    'sign_status': value["buttons"][0]["name"],
                                    'sign_action': value["buttons"][0]["params"]["action"]
                                    if value["buttons"][0]["name"] == '签到' else '',
                                    'page': value["itemid"][
                                            value["itemid"].find("super_follow") + len("super_follow") + 1:
                                            value["itemid"].find("super_follow") + len("super_follow") + 2]
                                }
                            )
                else:
                    print('{}不存在'.format(index))
                    pass
            # 写新的页码标签
            cardlistinfo = r.json()['cardlistInfo']
            since_id = str(cardlistinfo["since_id"])
            data['since_id'] = str(cardlistinfo["since_id"])
            if since_id == '':
                break
        return follow_list

    def start_sign(self, _list, time: int = 3):
        api = self.api
        msg = ''
        data = self.format_ck(self.ck)
        for index, value in enumerate(_list):
            page = value['page']
            data['v_f'] = f'{page}'
            sleep(time)
            if value['sign_status'] == '签到':
                sign_url = api + value['sign_action']
                r = post(sign_url, headers=self.headers, data=data)
                if r.json().get('errno') == -100:
                    print('参数已失效')
                    break
                if r.json().get('errno') == -200:
                    print('参数不存在')
                    break
                if r.json()['msg'] == '已签到':
                    msg = msg + '超话 {} 签到成功 {}/{}'.format(
                        value['title_sub'], int(index) + 1, len(_list)) + '\n'
                    print('超话 {} 签到成功 {}/{}'.format(value['title_sub'], int(index) + 1, len(_list)))
                    value['sign_status'] = '已签'
            elif value['sign_status'] == '已签':
                msg = msg + '超话 {} 已签到 {}/{}'.format(
                    value['title_sub'], int(index) + 1, len(_list)) + '\n'
                print('超话 {} 已签到 {}/{}'.format(value['title_sub'], int(index) + 1, len(_list)))
        if send_notify:
            Push.send(title='超话签到结果', msg=msg)


# 获取账号CK
if not user_list:
    user_list = os.environ.get('topic_sc')
if not user_list:
    sys.exit('请设置topic_sc变量')
user_list = user_list.strip()
# 多账号处理
user_list = re.split(r'&(?=https?://)', user_list)
print('任务开始 共有{}个账号'.format(len(user_list)))
for key in user_list:
    # 获取关注的超话
    _Topic = Topic(cookie=key)
    follow_topic_list = _Topic.get_follow_topic_list(time=sleep_time)
    # 开始签到
    if len(follow_topic_list) > 1:
        if follow_topic_list[0]['title_sub'] == follow_topic_list[len(follow_topic_list) - 1]['title_sub']:
            del follow_topic_list[0]
            _Topic.start_sign(follow_topic_list, time=sleep_time)
        else:
            _Topic.start_sign(follow_topic_list, time=sleep_time)
    else:
        _Topic.start_sign(follow_topic_list, time=sleep_time)
print('任务完成')
