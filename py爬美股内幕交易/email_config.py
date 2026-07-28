# 邮件配置文件
# 请根据你的邮箱服务商配置以下信息

# QQ邮箱配置示例
# SMTP_SERVER = "smtp.qq.com"
# SMTP_PORT = 587
# EMAIL_USER = "139069910@qq.com"  # 请替换为你的QQ邮箱
# EMAIL_PASSWORD = "111"  # 请替换为你的QQ邮箱授权码（不是登录密码）

#163邮箱配置示例（163 用 465 SSL，587 常被拒）
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465
EMAIL_USER = "axiba260708@163.com"
EMAIL_PASSWORD = "USSn4RSHRn9SBVZa"

# Gmail配置示例
# SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT = 587
# EMAIL_USER = "your_email@gmail.com"
# EMAIL_PASSWORD = "your_app_password"

# 发邮件阈值：仅当新记录的 Total/市值% 大于此值（单位：%）时才发邮件，且邮件只包含这些记录
# 设为 0 表示不限制（所有新记录都发）
MIN_PCT_OF_MARKET_CAP_FOR_EMAIL = 5

# 获取QQ邮箱授权码的步骤：
# 1. 登录QQ邮箱
# 2. 点击"设置" -> "账户"
# 3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
# 4. 开启IMAP/SMTP服务
# 5. 生成授权码，将授权码填入EMAIL_PASSWORD字段