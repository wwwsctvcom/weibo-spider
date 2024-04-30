import sys
import time
import re
import json
import requests
from loguru import logger
from bs4 import BeautifulSoup


class WeiboCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': "",
            'Cookie': "",
            'Referer': 'https://s.weibo.com',
            'Connection': 'keep-alive'
        }

    @staticmethod
    def weibo_date_strptime(date_str):
        """
        :param date_str: Tue Apr 30 07:50:34 +0800 2024
        :return: 2024-04-30 07:50:34
        """
        from datetime import datetime
        # '%a' 是星期缩写, '%b' 是月份缩写, '%z'是UTC偏移量
        dt = datetime.strptime(date_str, '%a %b %d %H:%M:%S %z %Y')
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        return formatted_time

    @staticmethod
    def get_searched_mids(query: str = None, max_pages: int = None) -> list:
        """获取搜索结果中max_pages中的所有微博的mid和微博内容"""
        mids = []
        for page in range(1, max_pages + 1):
            try:
                base_url = "https://s.weibo.com/weibo"

                headers = {
                    'User-Agent': "",
                    'Cookie': "",
                    'Referer': 'https://s.weibo.com',
                    'Connection': 'keep-alive'
                }

                params = {
                    'q': query,
                    'page': page
                }

                response = requests.get(base_url, headers=headers, params=params, verify=False, timeout=10)

                if response.status_code != 200:
                    logger.error(f"Cannot access the {response.url}, exit!")
                    return mids

                soup = BeautifulSoup(response.text, 'html.parser')
                divs = soup.select('div[action-type="feed_list_item"]')

                for div in divs:
                    mid = div.get('mid')

                    uid = div.select('div.card-feed > div.avator > a')
                    if uid:
                        uid = uid[0].get('href').replace('.com/', '?').split('?')[1]
                    else:
                        uid = ""

                    create_date = div.select('div.card-feed > div.content > div.from > a:first-of-type')
                    create_date = create_date[0].string.strip() if create_date else ""

                    p = div.select('div.card-feed > div.content > p:last-of-type')
                    if p:
                        p = p[0].strings
                        content = '\n'.join([para.replace('\u200b', '').strip() for para in list(p)]).strip()
                    else:
                        content = ""

                    # add searched info
                    mids.append([mid, uid, create_date, content])
            except Exception as e:
                logger.error(e)
        return mids

    def get_comment(self, mid: str, uid: str, the_first=True, max_id=None):
        base_url = "https://weibo.com/ajax/statuses/buildComments"
        """
        is_asc: 0
        is_reload: 1
        id: 5025502403756659
        is_show_bulletin: 3
        is_mix: 0
        count: 20
        uid: 6660905731
        fetch_level: 0
        locale: zh-CN
        """

        params = {
            "is_reload": 1,
            "id": mid,
            "is_show_bulletin": 3,
            "is_mix": 0,
            "count": 20,  # 评论数
            "uid": uid,
            "fetch_level": 0,
            "locale": "zh-CN",
        }

        if not the_first:
            params['flow'] = 0
            params['max_id'] = max_id

        response = requests.get(base_url, headers=self.headers, params=params, verify=False, timeout=10)
        time.sleep(3)
        return response

    def get_child_comment(self, mid: str, uid: str, the_first=True, max_id=None):
        base_url = "https://weibo.com/ajax/statuses/buildComments"
        """
        is_reload: 1
        id: 5028765698621629
        is_show_bulletin: 2
        is_mix: 1
        fetch_level: 1
        max_id: 0
        count: 20
        uid: 1642634100
        locale: zh-CN
        """

        params = {
            "is_reload": 1,
            "id": mid,
            "is_show_bulletin": 2,
            "is_mix": 1,
            "fetch_level": 1,
            "count": 20,
            "uid": uid,
            "locale": "zh-CN",
        }

        if not the_first:
            params['flow'] = 0
            params['max_id'] = max_id
        else:
            params['max_id'] = 0
        response = requests.get(base_url, headers=self.headers, params=params, verify=False, timeout=10)
        time.sleep(3)
        return response

    def start_crawl(self, query: str, max_pages: int, months_ago: int):
        """
        max_id为0则代表当前评论已经已经请求结束，首次请求的max_id应该为空
        """
        if months_ago is None:
            nearest_months_to_now = months_ago_date(months=1)
        else:
            nearest_months_to_now = months_ago_date(months=months_ago)

        mids_info = self.get_searched_mids(query, max_pages)

        for index, mids in enumerate(mids_info):
            mid, uid, weibo_create_date, weibo_content = mids
            # mid, uid = "5028762471369664", "1642634100"  # https://weibo.com/1642634100/Oc4f55Kjm

            the_first, max_id = True, ""  # for the first request
            while True:
                # 不断通过requests加载更多未加载的评论
                response = self.get_comment(mid, uid, the_first=the_first, max_id=max_id)
                max_id = response.json()["max_id"]

                # 获取当前requests加载出来的多个父评论以及其对应的回复
                for parent_meta_data in response.json()["data"]:
                    links, comments, dates = [], [], []
                    parent_comment = "父评论: " + self.comment_clean(
                        parent_meta_data['reply_original_text'] if 'reply_original_text' in parent_meta_data else
                        parent_meta_data['text'])
                    parent_comment_create_at = self.weibo_date_strptime(parent_meta_data["created_at"])

                    # save parent comment
                    links.append(response.url)
                    comments.append(parent_comment)
                    dates.append(parent_comment_create_at)

                    print(parent_comment, parent_comment_create_at)

                    # parent的mid为parent中的["id"]
                    child_the_first, child_mid, child_uid, child_max_id = True, parent_meta_data["id"], uid, ""
                    while True:
                        # 通过requests获取父评论下的未加载完全的回复
                        response = self.get_child_comment(child_mid, child_uid, the_first=child_the_first,
                                                          max_id=child_max_id)
                        child_max_id = response.json()["max_id"]  # update child max_id
                        for child_meta_data in response.json()["data"]:
                            child_comment_create_at = self.weibo_date_strptime(child_meta_data["created_at"])
                            if date_compare(child_comment_create_at.split(" ")[0], nearest_months_to_now) <= 0:
                                continue
                            child_comment = self.comment_clean(child_meta_data['reply_original_text']
                                                               if 'reply_original_text' in child_meta_data else
                                                               child_meta_data["text"])

                            # save child comment
                            links.append(response.url)
                            comments.append(child_comment)
                            dates.append(child_comment_create_at)

                            print(child_comment_create_at, child_comment)

                        if child_the_first:
                            child_the_first = False
                        if child_max_id == 0:
                            break

                if the_first:
                    the_first = False
                if max_id == 0:
                    break
                time.sleep(10)

    def get_tweet_info(self, tweet_id: str = None) -> dict:
        response = None
        tweet_info = {}
        base_url = 'https://m.weibo.cn/detail/{}'
        try:
            response = requests.get(url=base_url.format(tweet_id), headers=self.headers, verify=False, timeout=10)

            if response.status_code != 200:
                return tweet_info

            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = soup.find_all("script")
            for script in scripts:
                if "$render_data" in script.text:
                    script_json_data = re.search(r'var \$render_data = (\[.*?])\[0]', script.text, re.DOTALL).group(1)
                    script_json = json.loads(script_json_data)
                    tweet_info["user_id"] = script_json[0]['status']['user']['id']
                    tweet_info["screen_name"] = script_json[0]['status']['user']['screen_name']
                    tweet_info["created_at"] = script_json[0]['status']['created_at']
                    tweet_info["comments_count"] = script_json[0]['status']['comments_count']
                else:
                    continue
        except Exception as e:
            logger.error(f"access for {response.url} failed, wait for 10s and retry.", e)
            time.sleep(10)
            logger.error("start retry...")
            response = requests.get(url=base_url.format(tweet_id),
                                    headers=self.headers, verify=False, timeout=10)
            if response.status_code != 200:
                logger.error("query tweet info failed, just exit(1)", e)
                sys.exit(1)
        return tweet_info

    @staticmethod
    def comment_clean(html_content):
        """
        :param html_content:
        :return:
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text()


if __name__ == "__main__":
    wb_crawler = WeiboCrawler()
    wb_crawler.start_crawl(query="小说", max_pages=1, months_ago=1)
