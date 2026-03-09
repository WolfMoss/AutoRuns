import requests
from bs4 import BeautifulSoup
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import schedule
from datetime import datetime

# 尝试导入邮件配置
try:
    from email_config import SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD
    print("已加载邮件配置")
except ImportError:
    print("警告: 未找到email_config.py文件，邮件功能将无法使用")
    SMTP_SERVER = None
    SMTP_PORT = None
    EMAIL_USER = None
    EMAIL_PASSWORD = None

url = "https://www.gelonghui.com/news/?type=27"
LAST_TITLE_FILE = "last_news_title.txt"
SEARCH_WORDS_FILE = "search_words.txt"
EMAILS_FILE = "emails.txt"

payload = {}
headers = {
  'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
  'accept-language': 'zh-CN,zh;q=0.9',
  'if-none-match': '"5531e-5I8tlH/eTg/mDev7aq9DH0Z/MV0"',
  'priority': 'u=0, i',
  'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'document',
  'sec-fetch-mode': 'navigate',
  'sec-fetch-site': 'none',
  'sec-fetch-user': '?1',
  'upgrade-insecure-requests': '1',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
  'Cookie': 'g_conversationId=11a2d; g_traceId=e082c4ac-d6c3-485b-830f-b26bbb09750d; glh_i18n_redirected=zh-cn'
}

def log_with_time(message):
    """打印带时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def read_search_words():
    """
    读取搜索关键字配置
    """
    try:
        if os.path.exists(SEARCH_WORDS_FILE):
            with open(SEARCH_WORDS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return [word.strip() for word in content.split(',') if word.strip()]
    except Exception as e:
        log_with_time(f"读取关键字配置时出错: {e}")
    return []

def read_email_addresses():
    """
    读取邮箱地址配置
    """
    try:
        if os.path.exists(EMAILS_FILE):
            with open(EMAILS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return [email.strip() for email in content.split(',') if email.strip()]
    except Exception as e:
        log_with_time(f"读取邮箱配置时出错: {e}")
    return []

def check_keywords_in_content(content_list, keywords):
    """
    检查关键字是否在正文内容中出现
    """
    found_keywords = []
    full_content = ' '.join(content_list).lower()
    
    for keyword in keywords:
        if keyword.lower() in full_content:
            found_keywords.append(keyword)
    
    return found_keywords

def send_email(to_emails, subject, content, news_title, news_url, found_keywords):
    """
    发送邮件通知
    """
    # 检查邮件配置是否完整
    if not all([SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD]):
        log_with_time("邮件配置不完整，请检查email_config.py文件")
        return False
        
    # 记录发送成功的邮箱
    successful_sends = []
    failed_sends = []
    
    # 为每个邮箱单独发送，避免连接问题影响其他邮箱
    for email in to_emails:
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USER
            msg['To'] = email  # 每次只发送到一个邮箱
            msg['Subject'] = Header(subject, 'utf-8')

            # 邮件正文
            body = f"""
港股新闻关键字匹配提醒

新闻标题: {news_title}
新闻链接: {news_url}
匹配的关键字: {', '.join(found_keywords)}

新闻正文:
{content}

---
这是一封自动发送的邮件，请勿回复。
            """

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 为每个邮箱创建独立的SMTP连接
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()  # 启用TLS加密
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            
            try:
                server.sendmail(EMAIL_USER, email, msg.as_string())
                successful_sends.append(email)
                log_with_time(f"✅ 邮件发送到 {email} 成功")
            except Exception as send_error:
                # 检查是否是QQ邮箱的"成功但报错"情况
                error_str = str(send_error)
                if "250 OK" in error_str or "250 ok" in error_str.lower():
                    # 虽然报错但包含"250 OK"，说明实际发送成功
                    successful_sends.append(email)
                    log_with_time(f"✅ 邮件发送到 {email} 成功（QQ邮箱响应格式问题，可忽略错误信息）")
                else:
                    failed_sends.append(email)
                    log_with_time(f"❌ 发送到 {email} 失败: {send_error}")
            finally:
                # 确保每次都关闭连接
                try:
                    server.quit()
                except:
                    pass
                    
        except Exception as e:
            # 检查是否是QQ邮箱的整体"成功但报错"情况
            error_str = str(e)
            if "250 OK" in error_str or "250 ok" in error_str.lower():
                successful_sends.append(email)
                log_with_time(f"✅ 邮件发送到 {email} 成功（QQ邮箱响应格式问题）")
                log_with_time(f"   技术详情: {e}")
            else:
                failed_sends.append(email)
                log_with_time(f"❌ 发送到 {email} 时出错: {e}")
    
    # 输出最终发送结果
    if successful_sends:
        log_with_time(f"📧 邮件发送总结:")
        log_with_time(f"   成功发送到: {', '.join(successful_sends)}")
        if failed_sends:
            log_with_time(f"   发送失败: {', '.join(failed_sends)}")
        return True
    else:
        log_with_time(f"❌ 所有邮箱发送失败: {', '.join(failed_sends)}")
        return False

def read_last_title():
    """
    读取上次保存的第一条新闻标题
    """
    try:
        if os.path.exists(LAST_TITLE_FILE):
            with open(LAST_TITLE_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception as e:
        log_with_time(f"读取上次标题时出错: {e}")
    return None

def save_last_title(title):
    """
    保存这次的第一条新闻标题
    """
    try:
        with open(LAST_TITLE_FILE, 'w', encoding='utf-8') as f:
            f.write(title)
        log_with_time(f"已保存最新标题到本地文件")
    except Exception as e:
        log_with_time(f"保存标题时出错: {e}")

def find_new_news_count(current_titles, last_title):
    """
    找到需要获取的新新闻数量
    """
    if last_title is None:
        log_with_time("首次运行，获取所有新闻")
        return len(current_titles)
    
    # 查找上次的第一条标题在当前列表中的位置
    for i, title in enumerate(current_titles):
        if title == last_title:
            log_with_time(f"找到上次的第一条新闻在当前第{i+1}位，将获取前{i}条新新闻")
            return i
    
    # 如果没找到上次的标题，说明所有新闻都是新的
    log_with_time("未找到上次的标题，所有新闻都是新的")
    return len(current_titles)

def get_news_content(news_url):
    """
    获取新闻详细内容
    """
    try:
        response = requests.get(news_url, headers=headers)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找class="main-news article-with-html"的article标签
            article = soup.find('article', class_='main-news article-with-html')
            
            if article:
                # 提取所有p标签的内容
                paragraphs = article.find_all('p')
                content_list = []
                
                for p in paragraphs:
                    # 获取纯文本内容，去除HTML标签
                    text = p.get_text(strip=True)
                    if text:  # 只添加非空的段落
                        content_list.append(text)
                
                return content_list
            else:
                return ["未找到正文内容"]
        else:
            return [f"请求失败，状态码: {response.status_code}"]
            
    except Exception as e:
        return [f"获取新闻内容时出错: {str(e)}"]

def run_news_monitor():
    """
    执行新闻监控的主要逻辑
    """
    try:
        log_with_time("🔍 开始执行港股新闻监控...")
        
        # 读取配置
        search_keywords = read_search_words()
        email_addresses = read_email_addresses()

        log_with_time(f"关键字配置: {search_keywords}")
        log_with_time(f"邮箱配置: {email_addresses}")

        if not search_keywords:
            log_with_time("警告: 未找到搜索关键字配置")
        if not email_addresses:
            log_with_time("警告: 未找到邮箱地址配置")

        response = requests.request("GET", url, headers=headers, data=payload)

        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 找到所有class="detail-right"的section标签
        detail_sections = soup.find_all('section', class_='detail-right')

        log_with_time(f"找到 {len(detail_sections)} 个detail-right section")

        # 读取上次保存的标题
        last_title = read_last_title()
        log_with_time(f"上次的第一条新闻标题: {last_title if last_title else '无'}")

        # 先提取所有新闻的标题和链接
        news_list = []
        for section in detail_sections:
            a_tag = section.find('a')
            h2_tag = section.find('h2')
            
            if a_tag and h2_tag:
                href = a_tag.get('href', '')
                title = h2_tag.get_text(strip=True)
                news_list.append({'title': title, 'href': href})

        if not news_list:
            log_with_time("未找到任何新闻")
            return

        # 获取所有当前标题
        current_titles = [news['title'] for news in news_list]

        # 计算需要获取的新新闻数量
        new_news_count = find_new_news_count(current_titles, last_title)

        if new_news_count == 0:
            log_with_time("没有新的新闻需要获取")
            return

        log_with_time("=" * 80)
        log_with_time(f"将获取前{new_news_count}条新新闻的详细内容")
        log_with_time("=" * 80)

        # 统计匹配到关键字的新闻数量
        matched_news_count = 0

        # 只处理新的新闻
        for i in range(new_news_count):
            news = news_list[i]
            title = news['title']
            href = news['href']
            
            log_with_time(f"第{i+1}条新闻:")
            log_with_time(f"标题: {title}")
            log_with_time(f"链接: {href}")
            
            # 构建完整的URL
            if href.startswith('/'):
                full_url = f"https://www.gelonghui.com{href}"
            else:
                full_url = href
                
            log_with_time(f"完整链接: {full_url}")
            log_with_time("-" * 50)
            
            # 获取新闻详细内容
            log_with_time("正在获取新闻正文...")
            content_paragraphs = get_news_content(full_url)
            
            log_with_time("正文内容:")
            for j, paragraph in enumerate(content_paragraphs, 1):
                log_with_time(f"  段落{j}: {paragraph}")
            
            # 检查关键字匹配
            if search_keywords:
                found_keywords = check_keywords_in_content(content_paragraphs, search_keywords)
                if found_keywords:
                    matched_news_count += 1
                    log_with_time(f"🎯 发现匹配关键字: {', '.join(found_keywords)}")
                    
                    # 发送邮件通知
                    if email_addresses:
                        email_subject = f"港股新闻关键字匹配提醒 - {', '.join(found_keywords)}"
                        email_content = '\n'.join(content_paragraphs)
                        
                        log_with_time("正在发送邮件通知...")
                        success = send_email(email_addresses, email_subject, email_content, title, full_url, found_keywords)
                        if success:
                            log_with_time("✅ 邮件发送成功")
                        else:
                            log_with_time("❌ 邮件发送失败")
                    else:
                        log_with_time("⚠️ 未配置邮箱地址，跳过邮件发送")
                else:
                    log_with_time("未匹配到关键字")
            
            log_with_time("=" * 80)
            
            # 添加延时，避免请求过于频繁
            time.sleep(1)

        # 保存这次的第一条新闻标题
        if news_list:
            save_last_title(news_list[0]['title'])

        log_with_time(f"本次处理完成，共获取了{new_news_count}条新新闻的详细内容")
        if search_keywords:
            log_with_time(f"其中匹配到关键字的新闻有{matched_news_count}条")
            if matched_news_count > 0 and email_addresses:
                log_with_time(f"已向{len(email_addresses)}个邮箱发送通知")
                
    except Exception as e:
        log_with_time(f"❌ 监控过程中出错: {e}")

def main():
    """
    主函数 - 启动定时监控
    """
    log_with_time("🚀 港股新闻关键字监控系统启动")
    log_with_time("📅 执行间隔: 每5分钟一次")
    log_with_time("按 Ctrl+C 停止监控")
    log_with_time("=" * 80)
    
    # 立即执行一次
    log_with_time("立即执行一次监控任务...")
    run_news_monitor()
    
    # 设置定时任务 - 每5分钟执行一次
    schedule.every(5).minutes.do(run_news_monitor)
    
    log_with_time("⏰ 定时任务已设置，每5分钟执行一次")
    log_with_time("=" * 80)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # 每30秒检查一次是否有待执行的任务
    except KeyboardInterrupt:
        log_with_time("⚠️ 用户中断，停止监控")
    except Exception as e:
        log_with_time(f"❌ 定时器运行出错: {e}")
    finally:
        log_with_time("🛑 监控系统已停止")

if __name__ == "__main__":
    main()
