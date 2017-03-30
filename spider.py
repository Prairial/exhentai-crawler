# encoding=utf-8

import sys
import logging
import datetime
import requests
import re
import os
from bs4 import BeautifulSoup
import time

reload(sys)
sys.setdefaultencoding('utf8')

import logging
logger = logging.getLogger(__name__)

'''
logging.basicConfig(
  level=logging.DEBUG,
  format="[%(asctime)s] %(name)s:%(levelname)s,%(lineno)d: %(message)s",
)
'''

logging.basicConfig(
  level=logging.INFO,
  format="[%(name)s,%(lineno)d: %(message)s",
)

proxies = None

cookies = {
  "ipb_member_id" : "",
  "ipb_pass_hash" : "",
  "igneous" : "",
  "s" : "",
  "lv" : "",
}

headers = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.80 Safari/537.36'
}

# get请求，自带重试
def geturl(url):
  for i in xrange(5):
    try:
      return requests.get(url, cookies=cookies, timeout=5, proxies=proxies, headers=headers)
    except Exception,e:
      time.sleep(5+i)
      logger.info('retry times : %s', i + 1)

# 生成目录
# 主页是形如https://exhentai.org/g/637778/8e25d8f40b/的连接，内有1961张图
# 因此目录应该是637778-8e25d8f40b-1961
def parse_args():
  if len(sys.argv) < 2:
    return None
  url = sys.argv[1].strip()
  if url.endswith("/"):
    url = url[0:url.rfind('/')]
  t = url.split('/')
  return t[-2],t[-1]

# 初始链接
def image_page(galleryid, ghashid, pageid):
  if pageid == 0:
    return '''https://exhentai.org/g/%s/%s/''' % (galleryid, ghashid)
  return '''https://exhentai.org/g/%s/%s/?p=%d''' % (galleryid, ghashid, pageid)

# 目录名
def dir_name(galleryid, ghashid, totalimgcount):
  return '%s-%s-%d' % (galleryid, ghashid, totalimgcount)

# 总图片数
def image_count(html):
  try:
    s = re.compile("Length.+pages").findall(html)[0]
    s = s[s.rfind(">")+1:s.rfind(' ')]
    return int(s)
  except:
    pass  
  return 0

# 已下载的项目
def check_downloads():
  pattern = re.compile('''^.*-.*-.\d+$''')
  for d in os.listdir("./"):
    if pattern.match(d):
      t = d.split('-')
      begin_download(t[0], t[1], int(t[2]), len(os.listdir(d))+1)

# 检查是否已下载某图片
def is_image_downloaded(imgid, files):
  s = str(imgid) + '.'
  for f in files:
    if f.startswith(s):
      return True
  return False
  
# 下载图片        
def download_image(url, imgid, dirname):
  r1 = geturl(url)
  soup1 = BeautifulSoup(r1.text)
  iu = soup1.select("#img")[0]["src"]
  path = "%s/%d.%s" % (dirname, imgid, iu.split('.')[-1])
  ir = geturl(iu)
  if not ir.content:
    raise Exception()
  with open(path, "wb") as f:
    f.write(ir.content)
  
# 处理每一页链接，获取具体的图片的链接
def begin_download(galleryid, ghashid, totalimgcount = 0, startimgid = 1):  
  logger.info("processing gallery : %s" % galleryid)
  
  dirname = ''
  downloadedfiles = []
  title = None
  
  # 总图片数，如果不为0则检查一下该目录是否已下完
  if totalimgcount > 0:
    dirname = dir_name(galleryid, ghashid, totalimgcount)
    downloadedfiles = os.listdir(dirname)
    if len(downloadedfiles) >= totalimgcount:
      # 下完则不处理
      logger.info("%s is downloaded, pass" % galleryid)
      os.rename(dirname, dirname + "-done")
      return True

  # 这里假设图总是一张接着一张下的，没有断开
  pageid = (startimgid-1)/40

  while totalimgcount == 0 or 40*pageid < totalimgcount:
    logger.info("processing page : %d" % pageid)
    url = image_page(galleryid, ghashid, pageid)
    res = geturl(url)
    time.sleep(5)
    if totalimgcount == 0:
      totalimgcount = image_count(res.text)
      dirname = dir_name(galleryid, ghashid, totalimgcount)
      if not os.path.exists(dirname):
        os.makedirs(dirname)
      downloadedfiles = os.listdir(dirname)
    
    # 检查本页每个图片链接
    soup = BeautifulSoup(res.text)
    title = soup.title
    for a in soup.select("#gdt .gdtm a"):
      imgurl = a["href"]
      # 图片编号
      imgid = int(imgurl.split('-')[-1])
      if not is_image_downloaded(imgid, downloadedfiles):
        logger.info("processing image %d" % imgid)
        download_image(imgurl, imgid, dirname)
        time.sleep(2)
      else:
        logger.info("image %d is downloaded, pass" % imgid)
      
    pageid += 1
  if title:
    title = title.text.replace(' - ExHentai.org','')
    title = ''.join(re.compile('''[A-Za-z0-9 \-()\[\]]''').findall(title))
    os.rename(dirname, title)
  else: 
    os.rename(dirname, dirname + "-done")


if __name__ == "__main__":
  args = parse_args()
  waittime = 0
  while True:
    try:
      if args:
        begin_download(args[0], args[1])
      else:
        check_downloads()
      break
    except Exception, e:
      waittime = 120
      logger.info("sleep %ds" % waittime)
      time.sleep(waittime)