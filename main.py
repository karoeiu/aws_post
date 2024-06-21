from langchain import OpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from tempfile import mkdtemp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
import os
import tweepy
import json
import random
import json
import boto3

def extract_braced_content(text):
    pattern = r"「([^」]*)」"
    matches = re.findall(pattern, text)
    return matches

def post(text, consumer_key, consumer_secret, access_token, access_token_secret):
    
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    client.create_tweet(text=text)
    print("posted your message!")

def make_post(theme, openai_api_key):
    # API Key 設定
    os.environ["OPENAI_API_KEY"] = openai_api_key

    llm = OpenAI()
    
    memory = ConversationBufferMemory(return_messages=True)
    conversation = ConversationChain(llm=llm, memory=memory)

    command = "以下のテーマからSNSに投稿する文章を、条件をもとに作成してください。\n（テーマ）"+ theme + "\n（条件）\n・'。'ごとに改行を２回する。\n・2文以内 \n"
    conversation.predict(input=command)

    command = "作成した文章をもとに、インプレッション数を2倍にするような文章に書き直してください。"

    command = "先ほど生成した文章を、鍵括弧「」で囲んで出力してください。あなたの言葉は必要ありません。"
    a = conversation.predict(input=command)
    print(a)
    res = extract_braced_content(a)[0]
    return(res[:140])

def get_theme():
    options = webdriver.ChromeOptions()
    service = webdriver.ChromeService("/opt/chromedriver")
    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--headless=new")
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
        themes.append(element.text.split("\n")[0])
    driver.quit()
    
    return(themes)

def handler(event, context):
    ssm_client = ssm_client = boto3.client('ssm')
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