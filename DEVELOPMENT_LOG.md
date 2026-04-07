## 2026-04-07 00:00

- Request: 修复 `scrape_dataroma_rt.py` 在 CI 中因 `allow_redirects='safe'` 导致的 `ValueError` 异常。
- Status: completed
- Files changed:
  - `py爬美股内幕交易/scrape_dataroma_rt.py`
  - `DEVELOPMENT_LOG.md`
- Changes made:
  - 在 `scrape_insider_tbody()` 中将 `Fetcher.get(INSIDER_URL)` 改为 `Fetcher.get(INSIDER_URL, allow_redirects=True)`。
  - 增加一行注释，说明该改动用于兼容 `curl_cffi` 对 `allow_redirects` 的 `int()` 转换要求。
- Why:
  - 当前依赖链中 `curl_cffi` 会执行 `int(allow_redirects)`，字符串 `'safe'` 触发 `ValueError`。
  - 显式传布尔值可避开库默认值差异，稳定跨环境运行。
- Verification:
  - 代码检查：确认修复调用已存在于 `scrape_insider_tbody()`。
  - 静态诊断：`ReadLints` 显示该文件无 linter 错误。
  - 说明：尝试通过终端执行 `python -m py_compile` 时，受当前终端对包含中文路径的脚本包装问题影响，未获得有效编译结果。
- Remaining notes:
  - 建议在 GitHub Actions 再跑一轮工作流验证线上环境抓取流程。
