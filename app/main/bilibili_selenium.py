from selenium import webdriver
from selenium.webdriver.common.by import By
#from selenium.webdriver.edge.service import Service
#from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import time
import json
import re
import os
#==================================UID & url部分===============================
UID = "470673207"
url = f"https://space.bilibili.com/{UID}/upload/video"   #获取关注数 粉丝数 点赞量 播放量
#=================================创建文件目录==================================
data_dir_path = os.path.join('.','app','data','raw',f'UID_{UID}')
os.makedirs(data_dir_path,exist_ok=True)
#=================================浏览器配置部分===============================
options = webdriver.EdgeOptions()
#options.page_load_strategy = 'eager'
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
#options.add_argument("--start-maximized")  # 最大化窗口，更像真人
options.add_argument("--no-sandbox")      # 必备权限
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-infobars")
#关闭图片视频加载等（可选，提速）
#options.add_argument("--blink-settings=imagesEnabled=false")
options.add_argument("--disable-images")
options.add_argument("--disable-video")
driver = webdriver.Edge(
    #service = Service(EdgeChromiumDriverManager().install()),
    options = options,
) 
#反爬处理
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    """
})
#设置等待器
wait = WebDriverWait(driver,5)
wait_login = WebDriverWait(driver,60)
#设置尺寸和位置
driver.set_window_size(1000,800)
driver.set_window_position(700, 0)
start_time = time.time() #开始时间
#模拟打开B站 获取cookies
print('登录中..............')
driver.get("https://www.bilibili.com")
cookies_path = os.path.join(".",'app','main','cookies.json')
try:
    #尝试读取cookies数据文件
    with open(cookies_path,mode='r',encoding='utf-8') as c:
        cookies_list = json.load(c)
    #将cookies带入driver -----如果文件是空的或者被损坏或者过期会报错然后进行登录操作
    for item in cookies_list:
        driver.add_cookie(item)
    #验证cookies是否还有效
    time.sleep(1)
    login_test = driver.find_elements(
        By.XPATH,'//*[@id="app"]//div[@class="bili-header__bar"]//ul[@class="right-entry"]//div[@class="header-login-entry"]'
    )
    #标记cookies数据是否有效
    if login_test:
        cookies_flag = True
    else:
        cookies_flag = False
        print('储存的cookies失效')
except:  #没有cookies文件 需要登录储存
    cookies_flag = False

if not cookies_flag:  #进行模拟登录操作
    print('请在浏览器进行登录,如登录后无反应请手动刷新页面')
    #等待成功登录----设置了60s内登录
    driver.set_window_position(0,0)
    try:
        wait_login.until(
            EC.invisibility_of_element_located(
                (By.XPATH,'//*[@id="app"]//div[@class="bili-header__bar"]//ul[@class="right-entry"]//div[@class="header-login-entry"]')
            )
        )  #这里是根据登录之后该元素会消失来写
    except:
        raise TimeoutError('登录超时请稍后重试')

    #储存cookies
    cookies_list = driver.get_cookies()
    with open(cookies_path,mode='w',encoding='utf-8') as c:
        json.dump(cookies_list,c)
    print('登录成功,已保存对应Cookies信息以便下次操作')

driver.set_window_position(700, 0)
#关闭图片渲染加速爬取------放在这里是为了登录时候二维码能读取稳定
driver.options.add_argument("--blink-settings=imagesEnabled=false")   

#===================================basic_data=========================================
driver.refresh()
driver.get(url)
nickname = wait.until(
    EC.presence_of_element_located(
        (By.XPATH,'.//div[@class="nickname"]')
    )
).text #获取昵称
basic_data_key_raw = driver.find_elements(
    By.XPATH,
    '//div[@class="nav-bar space-navbar"]//span[@class="nav-statistics__item-text"]'
) #获取key名
basic_data_value_raw = driver.find_elements(
    By.XPATH,
    '//div[@class="nav-bar space-navbar"]//span[@class="nav-statistics__item-num"]'
) #获取value
# 打印结果 关注数 粉丝量 点赞数 播放量  以及数据简单处理写入json文档
basic_data_json = [{"UID":UID,"昵称":nickname}]
print('=================================================================')
print('-------------------基础数据展示-----------------------------------')
print(f'UID:{UID}')
print(f'昵称:{nickname}')
for k,v in zip(basic_data_key_raw,basic_data_value_raw):  #数据展示+数据处理(保留纯数字字典格式)
    #最原始文本
    k = k.text
    v = v.get_attribute('title')
    #数据处理
    v_done = re.search(r'[\d,]+$',v).group().replace(',','') if re.search(r'[\d,]+',v) else '未知'
    basic_data_json[0][k] = v_done
    #数据展示----展示最原始文本
    print(f'{k}:{v}')
print('------------------------------------------------------------------')
print('===================================================================')
#编辑数据准备写入文档
basic_data_path = os.path.join(data_dir_path,'basic_data.json')
with open(basic_data_path,mode='w',encoding='utf-8') as f:
    json.dump(basic_data_json,f,ensure_ascii=False,indent=4)

print(f'基础数据保存成功,路径为:{basic_data_path}')

#==========================================video_data=========================================
#=======换页部分
#这里是为了第一次要有页面出现
print('爬取视频链接中.........................................................')
while True:
    video_data_raw = driver.find_elements(
    By.XPATH,
    './/div[@class="video-list grid-mode"]/div[@class="upload-video-card grid-mode"]'
    )
    if video_data_raw:
        break
    driver.refresh()
    time.sleep(3)

video_href_list=[]
while True:
    #首先获取视频原始节点数据
    #初始化变量
    video_data_raw = []
    video_data_raw = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH,'.//div[@class="video-list grid-mode"]/div[@class="upload-video-card grid-mode"]')
        )
    )
    button1 = driver.find_elements(
        By.XPATH,
        "//button[contains(@class,'vui_pagenation') and normalize-space()='上一页']")
    button2 = driver.find_elements(
        By.XPATH,
        "//button[contains(@class,'vui_pagenation') and normalize-space()='下一页']")
    #获取不到节点进行 上一页->下一页操作
    while not video_data_raw:
        if not button1[0].text == "上一页":
            driver.refresh()  #这是针对第一页操作
        button1[0].click()
        time.sleep(1)
        button2[0].click()
        time.sleep(1)
        video_data_raw = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH,'.//div[@class="video-list grid-mode"]/div[@class="upload-video-card grid-mode"]')
            )
        )
    #处理视频节点 -> 转化为链接
    for ele in video_data_raw:
    #链接数据处理
        url_single_video = ele.find_element(
        By.XPATH,
        ".//div[@class='bili-video-card__cover']//a[@class='bili-cover-card']"
        ).get_attribute('href')
        if not url_single_video.startswith('https:'):
            url_single_video = os.path.join('https:',url_single_video)
        #处理完毕后加到列表
        video_href_list.append(url_single_video)
    if len(video_href_list) != len(set(video_href_list)):
        video_href_list = [i for i in set(video_href_list)]
        if button2[0].text == "下一页":
            button2[0].click()
            time.sleep(1)
            button1[0].click()
            time.sleep(2)
            continue
        button1[0].click()
        time.sleep(1)
        button2[0].click()
        time.sleep(2)
        continue

    #换页操作
    if button2[0].text == '下一页':  #还有下一页就一直跳转直到没
        button2[0].click()            
        time.sleep(2) #跳转页面等待渲染
    else:
        break

#这里看看能不能改为多线程   已得到视频所有链接 video_href_list
video_data_json = []     #用于存放各个视频的数据
num_all_video = len(video_href_list)
print(f'一共抓取到{num_all_video}个视频,即将进行数据爬取')
error_time = 0 #用于记录失败条数
for idx,href in enumerate(video_href_list,start=1):
    try:
        print(f'爬取第{idx}个视频数据中..........')
        #进入单个视频进行数据爬取
        '''爬取 标题 播放量 弹幕数 点赞数 硬币数 转发量 分享量 评论数 '''
        driver.get(href)
        driver.execute_script(f"window.scrollTo(0, {random.randint(1000,3000)});") #滚动页面
        #标题
        title = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, ".//div[@class='video-info-title']//h1")
            )
        ).text
        '''#视频简介
        desc = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,'.//div[@class="basic-desc-info"]//span[@class="desc-info-text"]')
            )
        ).text'''   #不知道为什么爬取不到
        #播放量
        view_count = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, './/div[@class="video-info-meta"]//div[@class="view-text"]')
            )
        ).text
        #弹幕
        dm_count = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,'.//div[@class="video-info-meta"]//div[@class="dm-text"]')
            )
        ).text
        #发布(更改)时间
        pubdate = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                './/div[@class="video-info-meta"]//div[@class="pubdate-ip-text"]')
            )
        ).text
        #点赞量
        like_count = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,'.//span[@class="video-like-info video-toolbar-item-text"]')
            )
        ).text
        if like_count == '点赞':
            like_count = '0'
        #投币数
        coin_count = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, './/span[@class="video-coin-info video-toolbar-item-text"]')
            )
        ).text
        if coin_count == '投币':
            coin_count = '0'
        #收藏量
        fav_count = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,'.//span[@class="video-fav-info video-toolbar-item-text"]')
            )
        ).text
        if fav_count == '收藏':
            fav_count = '0'
        #转发量
        share_count = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,'.//div[@class="video-share-info video-toolbar-item-text"]')
            )
        ).text
        if share_count == '分享':
            share_count = '0'
        '''#评论数
        com_count = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,'.//div[@id="title"]//div[@id="count"]')
            )
        ).text
        if not com_count:
            com_count = '0'
            #不知道为什么爬取不到'''
    except Exception as e:
        print(f'第{idx}条视频爬取失败,原因:超时或者视频结构变化')
        print(f'对应链接为{href}')
        error_time+=1
        continue
    #数据整理和写入
    data = {
    '序号':idx,
    '标题':title,
    #'简介':desc,
    '播放量':view_count,
    '弹幕数':dm_count,
    '发布(更改)时间':pubdate,
    '点赞量':like_count,
    '投币数':coin_count,
    '收藏量':fav_count,
    '转发量':share_count,
    #'评论数':com_count
    '视频链接':href
    }
    video_data_json.append(data)

#写入video_data
video_data_path = os.path.join(data_dir_path,"video_data.json")
if video_data_json: #有数据 再说明
    with open(video_data_path,mode='w',encoding='utf-8') as f:
        json.dump(video_data_json,f,ensure_ascii=False,indent=4)
    #保存成功输出路径地址
    print(f'视频数据保存成功,路径为:{video_data_path}')
    num_video_success = len(video_data_json)
    print(f'成功爬取视频数据数:{num_video_success}')
    if error_time!=0:
        print(f'爬取失败视频数:{error_time}')
        print(f'爬取成功率:{num_video_success/num_all_video*100:.2f}%')
    else:
        print(f'爬取成功率:100.00%')
else:
    print("爬取失败,请检查网络后再试")

driver.close()
end_time = time.time()
print(f'总用时:{end_time-start_time:.3f}s')