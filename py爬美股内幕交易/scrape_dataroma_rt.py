# -*- coding: utf-8 -*-
"""
使用 Scrapling 抓取 Dataroma Real Time Insider 页面（tbody tr.col2），
提取 Filing/Symbol/Security/Reporting Name/Relationship/Trans.Date/ Purchase|Sale/Shares/Price/Amount；
页面自带股票代码，用 yfinance 取总市值并计算 Total/总市值%；
识别新数据并发送邮件（配置见 email_config.py，收件人见 emails.txt）；
更新 last_records.json 后通过 GitHub API 提交到仓库（需设置环境变量 GITHUB_TOKEN）。
"""
import base64
import json
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from urllib.parse import quote

import requests

from scrapling.fetchers import Fetcher

try:
    import yfinance as yf
except ImportError:
    yf = None

SCRIPT_DIR = Path(__file__).resolve().parent
LAST_RUN_PATH = SCRIPT_DIR / "last_records.json"
EMAILS_PATH = SCRIPT_DIR / "emails.txt"

INSIDER_URL = "https://www.dataroma.com/m/ins/ins.php?t=d&po=1&am=0&sym=&o=fd&d=d"


def _parse_amount(s):
    """将金额字符串如 '1,824' 或 '$12,311,558' 转为浮点数。"""
    if not s:
        return None
    s = re.sub(r"[\s$,\,]", "", s.strip())
    try:
        return float(s)
    except ValueError:
        return None


def _get_market_cap(symbol):
    """用页面上的股票代码直接查 yfinance 总市值。"""
    if not yf or not symbol:
        return None
    try:
        t = yf.Ticker(symbol)
        info = t.info
        if isinstance(info, dict):
            return info.get("marketCap")
    except Exception:
        pass
    return None


def scrape_insider_tbody():
    page = Fetcher.get(INSIDER_URL)

    # 数据行：tbody 下 tr.col2
    rows = page.css("tbody tr.col2")
    if not rows:
        rows = page.css("tbody tr")
    records = []
    for row in rows:
        # td.f_date: 申报日期 + span.f_t 时间；a 为 filing 链接
        filing_date = (row.css("td.f_date::text").get() or "").strip()
        filing_time = (row.css("td.f_date span.f_t::text").get() or "").strip()
        if not filing_date:
            filing_date = (row.css("td.f_date a::text").get() or "").strip()
        filing_url = row.css("td.f_date a::attr(href)").get() or ""
        if filing_url and not filing_url.startswith("http"):
            filing_url = ("https://www.sec.gov" + filing_url if filing_url.startswith("/Archives") else "https://www.dataroma.com" + filing_url)

        # td.iss_sym: 股票代码（页面直接给出）
        symbol = (row.css("td.iss_sym a::text").get() or "").strip()
        symbol_url = row.css("td.iss_sym a::attr(href)").get() or ""

        # td.iss_name: 证券名称
        security = (row.css("td.iss_name::text").get() or "").strip()

        # td.rep_name: 申报人
        reporting_name = (row.css("td.rep_name a::text").get() or row.css("td.rep_name::text").get() or "").strip()
        reporting_url = row.css("td.rep_name a::attr(href)").get() or ""

        # td.rel: 关系
        relationship = (row.css("td.rel::text").get() or "").strip()

        # td.t_date: 交易日期
        trans_date = (row.css("td.t_date::text").get() or "").strip()

        # td.tran_code: Purchase / Sale
        activity = (row.css("td.tran_code::text").get() or "").strip()

        # td.sh, td.pr, td.amt
        shares = (row.css("td.sh::text").get() or "").strip()
        price = (row.css("td.pr::text").get() or "").strip()
        total_str = (row.css("td.amt::text").get() or "").strip()

        # td.dir_ind: D/I
        dir_ind = (row.css("td.dir_ind::text").get() or "").strip()

        if not total_str:
            continue

        total_num = _parse_amount(total_str)
        market_cap = _get_market_cap(symbol) if symbol else None
        pct_of_market_cap = None
        if total_num and market_cap and market_cap > 0:
            pct_of_market_cap = round(total_num / market_cap * 100, 4)

        records.append({
            "filing_date": filing_date,
            "filing_time": filing_time,
            "filing_url": filing_url,
            "symbol": symbol,
            "symbol_url": symbol_url,
            "security": security,
            "reporting_name": reporting_name,
            "reporting_url": reporting_url,
            "relationship": relationship,
            "transaction_date": trans_date,
            "activity": activity,
            "shares": shares,
            "price": price,
            "total": total_str,
            "total_num": total_num,
            "market_cap": market_cap,
            "pct_of_market_cap": pct_of_market_cap,
            "dir_ind": dir_ind,
        })

    return {"rows_count": len(records), "records": records}


def _record_key(rec):
    """主键：filing_date、filing_time、symbol。"""
    return (
        rec.get("filing_date"),
        rec.get("filing_time"),
        rec.get("symbol"),
    )


def _load_last_records():
    if not LAST_RUN_PATH.exists():
        return None
    try:
        with open(LAST_RUN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("keys")
    except Exception:
        return None


def _save_last_records(records):
    """只持久化主键列表，不存完整记录。"""
    keys = [list(_record_key(r)) for r in records]
    with open(LAST_RUN_PATH, "w", encoding="utf-8") as f:
        json.dump({"keys": keys}, f, ensure_ascii=False, indent=2)


def _push_last_records_to_github():
    """将 last_records.json 通过 GitHub API 提交到仓库（参考 main.py）。"""
    token = "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"
    if not token:
        print("未设置 GITHUB_TOKEN，跳过提交 GitHub")
        return
    owner, repo = "WolfMoss", "AutoRuns"
    path = "py爬美股内幕交易/last_records.json"
    path_encoded = quote(path, safe="/")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path_encoded}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }
    try:
        get_resp = requests.get(url, headers=headers, timeout=30)
        sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None
    except Exception as e:
        print(f"获取 GitHub 文件信息失败: {e}")
        return
    try:
        with open(LAST_RUN_PATH, "rb") as f:
            content = f.read()
        base64_string = base64.b64encode(content).decode()
    except Exception as e:
        print(f"读取 last_records.json 失败: {e}")
        return
    data = {
        "message": "Update last_records.json",
        "content": base64_string,
    }
    if sha:
        data["sha"] = sha
    try:
        put_resp = requests.put(url, headers=headers, json=data, timeout=30)
        if put_resp.status_code in (200, 201):
            print("last_records.json 已提交到 GitHub")
        else:
            print(f"提交 GitHub 失败: {put_resp.status_code} {put_resp.text}")
    except Exception as e:
        print(f"提交 GitHub 失败: {e}")


def _get_new_records(current_records):
    last = _load_last_records()
    if last is None:
        return list(current_records)
    last_keys = set(tuple(k) for k in last)
    new_records = [r for r in current_records if _record_key(r) not in last_keys]
    return new_records


def _read_emails():
    if not EMAILS_PATH.exists():
        return []
    with open(EMAILS_PATH, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def _records_above_pct_threshold(records, min_pct):
    """仅保留 Total/市值% >= min_pct 的记录；min_pct 为 0 时返回全部。"""
    if min_pct is None or min_pct <= 0:
        return list(records)
    return [r for r in records if r.get("pct_of_market_cap") is not None and r["pct_of_market_cap"] >= min_pct]


def _build_email_html(records, min_pct_used):
    """生成带样式的 HTML 表格邮件正文。"""
    from html import escape
    cols = [
        ("Filing", "filing_date", "filing_time"),
        ("Symbol", "symbol", None),
        ("Security", "security", None),
        ("Reporting", "reporting_name", None),
        ("Relation", "relationship", None),
        ("Trans Date", "transaction_date", None),
        ("Activity", "activity", None),
        ("Shares", "shares", None),
        ("Price", "price", None),
        ("Total", "total", None),
        ("Market Cap", "market_cap", None),
        ("Total/市值%", "pct_of_market_cap", None),
    ]
    headers = [c[0] for c in cols]

    def cell(v, is_pct=False):
        if v is None:
            return "—"
        if is_pct and isinstance(v, (int, float)):
            return f"{v}%"
        if isinstance(v, (int, float)) and v >= 1e6:
            return f"{v:,.0f}"
        return escape(str(v))

    def row_cells(rec):
        out = []
        for _, k, k2 in cols:
            if k2:
                v = f"{rec.get(k, '')} {rec.get(k2, '')}".strip() or None
                out.append(f"<td>{cell(v)}</td>")
                continue
            elif k == "market_cap":
                v = rec.get("market_cap")
                out.append(f"<td>{cell(v)}</td>")
                continue
            elif k == "pct_of_market_cap":
                v = rec.get("pct_of_market_cap")
                out.append(f"<td><strong>{cell(v, is_pct=True)}</strong></td>")
                continue
            else:
                v = rec.get(k)
            out.append(f"<td>{cell(v)}</td>")
        return "".join(out)

    rows_html = "".join(
        f"<tr>{row_cells(rec)}</tr>" for rec in records
    )
    ths = "".join(f"<th>{escape(h)}</th>" for h in headers)
    if min_pct_used and min_pct_used > 0:
        threshold_note = f'<p style="color:#555;font-size:14px;">以下记录满足 <b>Total/市值% ≥ {min_pct_used}%</b>（共 {len(records)} 条）。</p>'
    else:
        threshold_note = f'<p style="color:#555;font-size:14px;">以下为本次新内幕交易记录（共 {len(records)} 条）。</p>'
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
table {{ border-collapse: collapse; width: 100%; max-width: 1200px; font-size: 13px; font-family: sans-serif; }}
th {{ background: #2c3e50; color: #fff; padding: 10px 8px; text-align: left; }}
td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
tr:nth-child(even) {{ background: #f8f9fa; }}
tr:hover {{ background: #e8f4f8; }}
a {{ color: #3498db; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
p {{ margin: 0 0 12px 0; }}
</style>
</head>
<body>
<p style="font-size: 16px;"><b>Dataroma 新内幕交易记录</b></p>
{threshold_note}
<table>
<thead><tr>{ths}</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
</body>
</html>"""
    return html


def _send_email(records_to_send):
    if not records_to_send:
        return False
    try:
        import email_config
    except ImportError:
        print("未找到 email_config.py，跳过发送邮件")
        return False
    to_list = _read_emails()
    if not to_list:
        print("emails.txt 为空或不存在，跳过发送邮件")
        return False

    server = getattr(email_config, "SMTP_SERVER", None)
    port = getattr(email_config, "SMTP_PORT", 587)
    user = getattr(email_config, "EMAIL_USER", None)
    password = getattr(email_config, "EMAIL_PASSWORD", None)
    min_pct = getattr(email_config, "MIN_PCT_OF_MARKET_CAP_FOR_EMAIL", 0)
    if not all([server, user, password]):
        print("email_config.py 未配置完整，跳过发送邮件")
        return False

    subject = "[Dataroma] 新内幕交易记录"
    html_body = _build_email_html(records_to_send, min_pct)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = ", ".join(to_list)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(server, port) as s:
            s.starttls()
            s.login(user, password)
            s.sendmail(user, to_list, msg.as_string())
        pct_note = f"，Total/市值% ≥ {min_pct}%" if min_pct and min_pct > 0 else ""
        print(f"已向 {len(to_list)} 个邮箱发送邮件（共 {len(records_to_send)} 条记录{pct_note}）")
        return True
    except Exception as e:
        print(f"发送邮件失败: {e}")
        return False


if __name__ == "__main__":
    result = scrape_insider_tbody()
    if result is None:
        exit(1)

    records = result["records"]
    new_records = _get_new_records(records)
    _save_last_records(records)
    _push_last_records_to_github()

    print(f"共 {result['rows_count']} 行\n")
    print("Filing Date\tFiling Time\tSymbol\tSecurity\tTrans Date\tActivity\tTotal\tMarket Cap\tTotal/市值%")
    for rec in records[:10]:
        mc = rec.get("market_cap")
        mc_str = f"{mc:,.0f}" if mc is not None else "N/A"
        pct = rec.get("pct_of_market_cap")
        pct_str = f"{pct}%" if pct is not None else "N/A"
        print(f"{rec['filing_date']}\t{rec['filing_time']}\t{rec['symbol']}\t{rec['security']}\t{rec['transaction_date']}\t{rec['activity']}\t{rec['total']}\t{mc_str}\t{pct_str}")
    if result["rows_count"] > 10:
        print("...")

    if new_records:
        try:
            import email_config as _ec
            min_pct = getattr(_ec, "MIN_PCT_OF_MARKET_CAP_FOR_EMAIL", 0)
        except ImportError:
            min_pct = 0
        to_send = _records_above_pct_threshold(new_records, min_pct)
        if to_send:
            print(f"\n发现 {len(new_records)} 条新记录，其中 {len(to_send)} 条 Total/市值% ≥ {min_pct}%，正在发送邮件...")
            _send_email(to_send)
        else:
            print(f"\n发现 {len(new_records)} 条新记录，但无记录满足 Total/市值% ≥ {min_pct}%，未发送邮件。")
    else:
        print("\n无新记录，未发送邮件。")
