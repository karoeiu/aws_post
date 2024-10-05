from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from tempfile import mkdtemp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
import os
import tweepy
import random
import json
import boto3

def post(text, consumer_key, consumer_secret, access_token, access_token_secret):
    
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    client.create_tweet(text=text)

def make_post(theme, openai_api_key):
    # API Key 設定
    os.environ["OPENAI_API_KEY"] = openai_api_key

    llm = ChatOpenAI(model_name="gpt-4o")
    
    memory = ConversationBufferMemory(return_messages=True)
    conversation = ConversationChain(llm=llm, memory=memory)

    command = f"""以下のテーマをSNSで解説する文章を、条件をもとに作成してください。
    （テーマ）{theme[0]}
    （条件）
    ・3文以内。かつ140文字以内。
    ・exclamation mark'！'とquestion mark'？'を2回連続して使用してはいけない。
    ・最初に読者の注意を引きつけるために、興味を引く事実を提供する。
    ・ユーザーの共感を得るような、文章にする。
    ・情報倫理に注意する。例えば、センシティブな内容（戦争、病気、死...）に関しては、落ち着いた文章にする。
    """

    conversation.predict(input=command)

    command = """作成した文章をもとに、インプレッション数を大幅に上げるように、文章をブラッシュアップしてください。
    出力は、文章のみを出力してください。"""

    a = conversation.predict(input=command)
    a = re.sub(r'。(?!\n\n)', '。\n\n', a)
    a = re.sub(r'？(?!\n\n)', '？\n\n', a)
    a = re.sub(r'！(?!\n\n)', '！\n\n', a)

    command = "上の文章に合わせて、ハッシュタグを作成してください。出力は、作成したハッシュタグのみを出力してください。"
    
    tag = conversation.predict(input = command)

    res = a + tag + "\n\n" + theme[1]
    return(res)

def get_theme():
    options = webdriver.ChromeOptions()
    service = webdriver.ChromeService("/opt/chromedriver")
    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--headless")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")
    
    driver = webdriver.Chrome(options=options, service=service)
    driver.get('https://www.yahoo.co.jp/')

    news_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='news.yahoo.co.jp/pickup']")

    themes = []
    for element in news_elements:
        theme = element.text.split("\n")[0]
        url = element.get_attribute("href")
        themes.append((theme, url))

    driver.quit()
    
    return(themes)

def handler(event, context):
    ssm_client = boto3.client('ssm')
    response = ssm_client.get_parameter(
        Name='/credential/APIkey',
        WithDecryption=True
    )
    parameters = json.loads(response['Parameter']['Value'])
    openai_api_key=parameters["openai_api_key"]
    consumer_key=parameters["consumer_key"]
    consumer_secret=parameters["consumer_secret"]
    access_token=parameters["access_token"]
    access_token_secret=parameters["access_token_secret"]

    theme = random.choice(get_theme())
    text = make_post(theme, openai_api_key)
    post(text, consumer_key=consumer_key, consumer_secret=consumer_secret,
         access_token=access_token, access_token_secret=access_token_secret)
    
    return {
        'statusCode': 200,
        'body': "posted your message!"
    }