#!/usr/bin/env python
# coding: utf-8

import time
from datetime import datetime, timedelta, date
from time import mktime
from re import findall
import os

import vk_api
from telegram import Bot, ParseMode
from telegram.error import BadRequest
from tokens import TG_TOKEN, VK_TOKEN


CHANNEL = '-1001866265997'

DOMAIN = 'domain'
OWNER_ID = 'owner_id'
TITLE = 'title'

DELIMITER = '=' * 20

NOW = datetime.now()
try:
    with open('last') as f:
        LAST = int(f.readline().strip())
        LAST = datetime.fromtimestamp(LAST)
except FileNotFoundError:
    LAST = NOW - timedelta(days=1)

config = [{'title': 'СИЦ ИММиКН', 'domain': 'sic_mmcs', 'owner_id': -142132054},
          {'title': 'Южный федеральный университет (ЮФУ)', 'domain': 'sfedu_official', 'owner_id': -47535294},
          {'title': 'Объединенный совет обучающихся ЮФУ', 'domain': 'oso.sfedu', 'owner_id': -38100236},
          {'title': 'Студенческий спортивный клуб ЮФУ\\/ССК ЮФУ', 'domain': 'ssc_sfedu', 'owner_id': -43045610},
          {'title': 'SfeduNet: проектные решения', 'domain': 'sfedunet', 'owner_id': -187689044},
          {'title': 'СИЦ ЮФУ (Студенческий информационный центр ЮФУ)', 'domain': 'sicsfedu', 'owner_id': -76527561},
          {'title': 'SAMODELKA | МехМат', 'domain': 'mm_samodelka', 'owner_id': -206981452},
          {'title': 'ПРОФСОЮЗНАЯ ОРГАНИЗАЦИЯ ЮФУ', 'domain': 'studprof.sfedu', 'owner_id': -584315},
          {'title': '&quot;IT-куб&quot; Ростов-на-Дону', 'domain': 'itcube.rostov', 'owner_id': -194934545},
          {'title': 'Мехмат ЮФУ', 'domain': 'mmcs.official', 'owner_id': -88704999},
          {'title': 'SFEDU MEMES', 'domain': 'sfedumemes2020', 'owner_id': -164020433},
          {'title': 'SFEDUMEDIA | Студенческий медиацентр ЮФУ', 'domain': 'sfedumedia', 'owner_id': -143573419},
          {'title': 'Цитатник Мехмата', 'domain': 'mmcs_quotes', 'owner_id': -213227654},
          {'title': 'Центр культуры и творчества ЮФУ (ЦКТ ЮФУ)', 'domain': 'culture.sfedu', 'owner_id': -35849816},
          {'title': 'Акселератор SBS ЮФУ', 'domain': 'acsfedu', 'owner_id': -172386407},
          {'title': 'Точка кипения Южный федеральный университет', 'domain': 'tksfedu', 'owner_id': -182057604},
          {'title': 'Подслушано в ЮФУ', 'domain': 'overhearsfedu', 'owner_id': -58676702},
          {'title': 'IT-лаборатория мехмата ЮФУ', 'domain': 'itlab_mmcs', 'owner_id': -67527475},
          {'title': 'Кафедра физической культуры - Ростов', 'domain': 'kafedrafkrostov', 'owner_id': -210333190},
          {'title': 'Типичный ЮФУ', 'domain': 'vuz_sfedu', 'owner_id': -198100876},
          {'title': 'ЮФУ абитуриенту 2022', 'domain': 'abitur.sfedu', 'owner_id': -205247745},
          {'title': 'Волонтерский центр ЮФУ', 'domain': 'sfedu_volunteer', 'owner_id': -87836855},
          {'title': 'Oggetto', 'domain': 'oggettoweb', 'owner_id': -38493020},
          {'title': 'Промышленный коворкинг Garaж | Ростов-на-Дону', 'domain': 'garazh.space', 'owner_id': -122406894},
          {'title': 'Хакатон Autumn 2022 | Ростов-на-Дону', 'domain': 'fantastic_hackathon', 'owner_id': -106352936}]


class Post:
    def __init__(self, j, community=None):
        self.date = datetime.fromtimestamp(j['date'])
        self.text = self.parse_links(j['text'])
        self.id = j['id']
        self.from_id = j['from_id']
        self.owner_id = j['owner_id']

        self.community = community

    @staticmethod
    def parse_links(text):
        for vk_link in findall(r'\[[a-z]{1,4}\d+\|[^\[]+\]', text):
            href, caption = vk_link[1:-1].split('|', 1)
            text = text.replace(vk_link, link(caption.strip(), 'https://vk.com/' + href))
        return text

    def get_date(self, f='%H:%M %d.%m.%Y'):
        return self.date.strftime(f)

    def get_unix(self):
        return mktime(self.date.timetuple())

    def get_link_part(self):
        return f'?w=wall{self.owner_id}_{self.id}'

    def get_link(self):
        if self.community is not None:
            return 'https://vk.com/' + self.community.domain + self.get_link_part()
        return ''

    def __repr__(self):
        return '\n'.join(filter(lambda x: x, map(lambda x: x.strip(), self.text.split('\n')[:3])))

    def __str__(self):
        return self.get_date() + '\n' + self.text


class Community:
    def __init__(self, vk, config):
        self.vk = vk
        self.title = config[TITLE].replace(r'\/', r'/')
        self.domain = config[DOMAIN]
        self.owner_id = config[OWNER_ID]
        self.posts = []

    def get_posts(self, refresh=False):
        if not self.posts or refresh:
            self.load_posts()
        return self.posts

    def load_posts(self, count=20):
        self.posts = list(Post(p, self) for p in self.vk.wall.get(owner_id=self.owner_id, count=count)['items'])

    def get_recent_posts(self):
        return list(filter(lambda x: LAST < x.date <= NOW, self.get_posts()))


class Feed:
    def __init__(self, vk, config):
        self.communities = list(Community(vk, c) for c in config)

    def __str__(self):
        text = ''
        for c in self.communities:
            posts = c.get_recent_posts()
            if not posts:
                continue
            text += bold(link(c.title, 'https://vk.com/' + c.domain)) + '\n\n'
            for post in reversed(posts):
                text += code(post.get_date('%d %b, %H:%M')) + '\n'
                text += repr(post) + '\n'
                text += post.get_link() + '\n\n'
            text += DELIMITER + '\n\n'
        return text[:-23]


def link(caption, href):
    return f'<a href="{href}">{caption}</a>'


def bold(text):
    return f'<b>{text}</b>'


def code(text):
    return f'<code>{text}</code>'


vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

feed = Feed(vk, config)
bot = Bot(TG_TOKEN)
message = str(feed).split(DELIMITER)
while message:
    part = message.pop(0)
    while message and len(part) + len(message[0]) < 4096:
        part += DELIMITER + message.pop(0)
    # bot.send_message(CHANNEL, part, ParseMode.HTML, disable_web_page_preview=True)
    print(len(part))
with open('last', 'wt') as f:
    f.write(str(int(mktime(NOW.timetuple()))))
