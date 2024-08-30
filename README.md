# weibo-spider
不定期会进行更新，避免失效，微博评论爬虫tool，基于requests爬取指定link的评论和回复评论以及用户信息等内容

# usage
在main.py中配置默认参数可以直接使用，如果需要进行修改可以通过修改main中的参数
```
python main.py
```

# how to get cookie
浏览器F12进入开发者模式，选择最上一页的Network选项，刷新页面，找到当前页面link下的相关内容，可以找到可用的cookie
和相关的playload信息等内容


# Result
爬虫可以获取网页上面父评论，同时可以获取子评论（包括折叠的评论），主要是通过父评论的ID和信息等发送request不断获取子评论内容
