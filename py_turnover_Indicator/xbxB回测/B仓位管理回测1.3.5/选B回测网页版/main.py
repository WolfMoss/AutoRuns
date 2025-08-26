# -*- coding: utf-8 -*-
"""
回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""
import json
import mimetypes
import re
import shutil
import sys
import traceback
import zipfile
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from config import fuel_data_path
from fuel.api_client import client as base_data_api
from model.model import ResponseModel
from service.config_service import config_service
from service.data_service import download_daily_and_preprocess_data, download_full_and_preprocess_data
from utils.constant import product_list, is_debug
from utils.log_kit import get_logger
from utils.path_kit import get_backtest_path, get_folder_path, get_file_path

# 初始化日志记录器
logger = get_logger()

# 创建 FastAPI 应用实例
app = FastAPI()

# 挂载静态文件目录，前端静态资源可通过 /static 访问
app.mount("/static", StaticFiles(directory=get_folder_path("static")), name="static")


# 主页路由，返回 index.html 或 API 状态信息
@app.get("/", response_class=HTMLResponse)
def index():
    """前端 SPA 主页，优先返回 index.html"""
    index_file = get_file_path("static", "index.html")
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return JSONResponse(content={"message": "FastAPI Server is running", "status": "ok", "service": "backtest-qronos"})


# 获取指定配置文件内容
@app.get("/qronos/config")
def get_config(config_name: str = Query("config")):
    """获取指定配置文件内容，支持 config_name 参数"""
    logger.info("收到配置数据请求")
    try:
        config_data = config_service.get_config_data(config_name)
        logger.ok(f"配置数据返回成功，包含 {len(config_data)} 个变量")
        return ResponseModel.ok(data=config_data)
    except Exception as e:
        error_msg = f"API请求处理失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return ResponseModel.fail(msg=error_msg)


# 获取所有配置文件列表
@app.get("/qronos/configs")
def get_configs():
    """获取 data 目录下所有配置文件列表"""
    logger.info("收到获取配置列表请求")
    try:
        configs = config_service.get_config_list()
        logger.ok(f"配置列表获取成功，共 {len(configs)} 个配置")
        return ResponseModel.ok(data={"configs": configs, "total": len(configs)})
    except Exception as e:
        msg = f"配置列表获取失败: {e}"
        logger.error(msg)
        logger.error(traceback.format_exc())
        return ResponseModel.error(msg=msg)


# 新建/保存配置文件
@app.post("/qronos/config")
def create_config(data: dict):
    """保存配置文件，body 需包含 name 字段"""
    logger.info("收到创建配置文件请求")
    try:
        if not data or "name" not in data or not data["name"]:
            return ResponseModel.error(msg="缺少必填字段: name")
        config = config_service.create_config_from_request(data)
        result = config_service.save_config_file(config)
        return ResponseModel.ok(data=result, msg="配置文件创建成功")
    except ValueError as e:
        logger.error(f"配置数据验证失败: {e}")
        logger.error(traceback.format_exc())
        return ResponseModel.error(msg=str(e))
    except Exception as e:
        error_msg = f"创建配置失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return ResponseModel.fail(msg=error_msg)


# 删除指定配置文件
@app.delete("/qronos/config")
def delete_config(config_name: str = Query("config")):
    """删除指定的配置文件"""
    try:
        logger.info(f"收到删除配置文件请求: {config_name}")
        if config_name == "config":
            return ResponseModel.error(msg="无法删除当前策略 config.py ")

        # 构建文件路径
        file_path = get_file_path('data', f'{config_name}.py')

        # 检查文件是否存在
        if not file_path.exists():
            logger.warning(f'删除的文件不存在: {file_path}')
        else:
            # 删除文件
            file_path.unlink(missing_ok=True)
            logger.ok(f"配置文件删除成功: {config_name}.py")

        return ResponseModel.ok(msg="配置文件删除成功")

    except Exception as e:
        msg = f"删除配置文件失败: {e}"
        logger.error(msg)
        logger.error(traceback.format_exc())
        return ResponseModel.errpr(msg=msg)


@app.post("/qronos/config/copy")
def copy_config(raw_name: str = Query("config"), target_name: str = Query("config_copy")):
    """复制配置文件并修改backtest_name"""
    try:
        logger.info(f"收到原文件名称: {raw_name}，目标文件名称: {target_name}")
        if target_name == "config":
            return ResponseModel.error(msg="无法将策略保存为 config.py")

        if raw_name == "config":
            raw_file_path = get_backtest_path('config.py')
        else:
            raw_file_path = get_file_path('data', f'{raw_name}.py')
        target_file_path = get_file_path('data', f'{target_name}.py')
        if not raw_file_path.exists():
            return ResponseModel.error(msg=f"未找到需要复制的配置 {raw_name}")

        # 读取源文件内容
        with open(raw_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 backtest_name = 'xxx' 的模式
        pattern = r"backtest_name\s*=\s*['\"]([^'\"]*)['\"]"
        replacement = f"backtest_name = '{target_name}'"
        
        # 检查是否找到backtest_name变量
        if re.search(pattern, content):
            # 替换backtest_name的值
            modified_content = re.sub(pattern, replacement, content)
            logger.info(f"已修改backtest_name为: {target_name}")
        else:
            # 如果没有找到backtest_name，在策略配置部分添加
            return ResponseModel.error(msg=f'原配置文件配置项不全，请修改 {raw_name} 配置')

        # 写入目标文件
        with open(target_file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        logger.ok(f"配置文件复制成功: {raw_name}.py -> {target_name}.py")
        return ResponseModel.ok(msg=f"配置文件复制成功，已修改backtest_name为: {target_name}")
        
    except Exception as e:
        msg = f"文件复制失败: {e}"
        logger.error(msg)
        logger.error(traceback.format_exc())
        return ResponseModel.error(msg=msg)


@app.post("/qronos/config/apply")
def apply_config(config_name: str = Query("config")):
    logger.info(f"应用配置的名称: {config_name}")
    if config_name == "config":
        logger.warning(f'config 配置不需要再次应用')
        return ResponseModel.ok()

    raw_config_path = get_file_path('data', f'{config_name}.py')
    if not raw_config_path.exists():
        return ResponseModel.error(msg=f"应用的配置文件路径不存在: {config_name} ")

    # 拷贝这个配置到回测框架根目录下，并重命名为 config.py，直接覆盖掉
    if is_debug:
        target_config_path = get_file_path('data', 'config.py')
    else:
        target_config_path = get_backtest_path('config.py')
    shutil.copy2(raw_config_path, target_config_path)
    # 删除源文件
    raw_config_path.unlink(missing_ok=True)

    return ResponseModel.ok()


@app.post("/qronos/config/import")
def import_config(file: UploadFile = File(...)):
    """导入策略配置文件，支持zip格式"""
    try:
        logger.info(f"收到导入配置文件请求: {file.filename}")

        # 检查文件格式
        if not file.filename.endswith('.zip'):
            return ResponseModel.error(msg="只支持.zip格式文件")

        # 使用data/temp目录
        temp_dir = get_folder_path('data', 'temp', 'config')
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = Path(temp_dir)
        zip_path = temp_path / file.filename

        # 保存上传的文件
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 解压文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_path)

        # 遍历解压后的目录结构
        copied_files = []
        config_files_to_convert = []

        for item in temp_path.rglob('*.py'):
            if item.is_file():
                # 获取相对路径
                relative_path = item.relative_to(temp_path)
                target_dir = None

                # 根据目录名确定目标目录
                if str(relative_path.parent) in ['factors', 'factor']:
                    if is_debug:
                        target_dir = get_folder_path('data', 'factors')
                    else:
                        target_dir = get_backtest_path('factors')
                elif str(relative_path.parent) in ['sections', 'section']:
                    if is_debug:
                        target_dir = get_folder_path('data', 'sections')
                    else:
                        target_dir = get_backtest_path('sections')
                else:
                    # 选币框架，根目录下是 config
                    # 仓管框架，accounts 目录下是 config
                    # 其他目录的文件，默认放到data目录
                    target_dir = get_folder_path('data')

                    # 检查是否是实盘配置文件（包含account_config）
                    if 'accounts' in str(relative_path) or '实盘' in str(relative_path) or '精心' in str(relative_path):
                        config_files_to_convert.append((item, target_dir))
                        continue

                # 确保目标目录存在
                target_dir.mkdir(parents=True, exist_ok=True)

                # 拷贝文件
                target_file = target_dir / item.name
                shutil.copy2(item, target_file)
                copied_files.append(str(relative_path))
                logger.info(f"已拷贝文件: {item.name} -> {target_file}")

        # 处理需要转换的配置文件
        for config_file, target_dir in config_files_to_convert:
            try:
                converted_filename = config_service.convert_real_trading_to_backtest_config(config_file)
                if converted_filename:
                    copied_files.append(f"{converted_filename}")
                    logger.info(f"已转换配置文件: {config_file} -> {target_dir}/{converted_filename}")
                else:
                    # 转换失败时，直接拷贝原文件
                    target_file = target_dir / config_file.name
                    shutil.copy2(config_file, target_file)
                    copied_files.append(config_file.name)
                    logger.warning(f"配置文件转换失败，已拷贝原文件: {config_file.name}")
            except Exception as e:
                logger.warning(f"配置文件转换失败 {config_file.name}: {e}")
                # 转换失败时，直接拷贝原文件
                target_file = target_dir / config_file.name
                shutil.copy2(config_file, target_file)
                copied_files.append(config_file.name)

        # 清理临时文件
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)

        logger.ok(f"导入完成，共拷贝 {len(copied_files)} 个文件")
        return ResponseModel.ok(data={
            "imported_files": copied_files,
            "total_files": len(copied_files)
        }, msg="策略导入成功")

    except zipfile.BadZipFile:
        logger.error("上传的文件不是有效的zip格式")
        return ResponseModel.error(msg="上传的文件不是有效的zip格式")
    except Exception as e:
        msg = f"导入配置文件失败: {e}"
        logger.error(msg)
        logger.error(traceback.format_exc())
        return ResponseModel.error(msg=msg)


@app.post("/qronos/config/export")
def export_config(config_name: str = Query("config")):
    """导出指定配置的策略包，包含factors、sections和config文件"""
    try:
        logger.info(f"收到导出配置文件请求: {config_name}")

        # 检查配置文件是否存在
        config_file_path = get_file_path('data', f'{config_name}.py')
        if not config_file_path.exists():
            return ResponseModel.error(msg=f"配置文件 {config_name}.py 不存在")

        # 创建临时导出目录
        export_dir = get_folder_path('data', 'temp', 'export')
        export_dir.mkdir(parents=True, exist_ok=True)

        # 创建zip文件
        zip_filename = f"{config_name}_strategy_package.zip"
        zip_path = get_folder_path('data', 'temp') / zip_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # todo 需要将回测的配置，转成实盘使用的配置
            # 添加config文件
            config_relative_path = f"data/{config_name}.py"
            zipf.write(config_file_path, config_relative_path)
            logger.info(f"已添加配置文件: {config_relative_path}")

            # 添加factors文件
            factors_dir = get_backtest_path('factors') if not is_debug else get_folder_path('data', 'factors')
            if factors_dir.exists():
                for factor_file in factors_dir.glob('*.py'):
                    if factor_file.is_file():
                        relative_path = f"factors/{factor_file.name}"
                        zipf.write(factor_file, relative_path)
                        logger.info(f"已添加因子文件: {relative_path}")

            # 添加sections文件
            sections_dir = get_backtest_path('sections') if not is_debug else get_folder_path('data', 'sections')
            if sections_dir.exists():
                for section_file in sections_dir.glob('*.py'):
                    if section_file.is_file():
                        relative_path = f"sections/{section_file.name}"
                        zipf.write(section_file, relative_path)
                        logger.info(f"已添加章节文件: {relative_path}")

        # 检查zip文件是否创建成功
        if not zip_path.exists():
            return ResponseModel.error(msg="导出文件创建失败")

        logger.ok(f"导出完成: {zip_filename}")

        return ResponseModel.ok(data={
            "filename": zip_filename,
            "file_size": zip_path.stat().st_size
        }, msg="策略导出成功")

    except Exception as e:
        msg = f"导出配置文件失败: {e}"
        logger.error(msg)
        logger.error(traceback.format_exc())
        return ResponseModel.error(msg=msg)


@app.get("/qronos/config/download")
def download_file(filename: str):
    """下载导出的zip文件"""
    try:
        file_path = get_folder_path('data', 'temp') / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/zip'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail="文件下载失败")


# 获取因子文件列表（factors/sections）
@app.get("/qronos/all_factors")
def get_factors():
    """获取因子文件列表，包含 factors 和 sections 目录下的所有 .py 文件"""
    logger.info("获取因子文件列表")

    try:
        results = {}
        for factor_type in ['factors', 'sections']:
            results[factor_type] = []
            if is_debug:
                data_dir = get_folder_path('data', factor_type)
            else:
                data_dir = get_backtest_path(factor_type)

            if data_dir.exists():
                for file in data_dir.iterdir():
                    if file.is_file() and file.suffix == ".py" and not file.name.startswith('_'):
                        results[factor_type].append({'name': file.stem})
            logger.ok(f"找到 {factor_type} {len(results[factor_type])} 个因子文件")

        return ResponseModel.ok(data=results)

    except Exception as e:
        logger.error(f"获取因子列表失败: {e}")
        logger.error(traceback.format_exc())
        return ResponseModel.error(msg=str(e))


@app.post("/qronos/run_backtest")
def run_backtest():
    """执行回测脚本"""
    logger.info("开始执行回测")

    try:
        python_exec = sys.executable
        py_file = get_backtest_path('backtest.py')

        # 检查回测脚本是否存在
        if not py_file.exists():
            logger.error(f"回测脚本不存在: {py_file}")
            return ResponseModel.error(msg="回测脚本不存在，请先应用配置")

        # 检查配置文件是否存在
        config_file = get_backtest_path('config.py')
        if not config_file.exists():
            logger.error(f"配置文件不存在: {config_file}")
            return ResponseModel.error(msg="配置文件不存在，请先应用配置")

        # 执行回测脚本
        config_service.execute_backtest_script(python_exec, py_file)

        logger.ok("回测任务完成")
        return ResponseModel.ok()

    except Exception as e:
        logger.error(f"启动回测失败: {e}")
        logger.error(traceback.format_exc())
        return ResponseModel.error(msg=f"启动回测失败: {str(e)}")


@app.get("/qronos/data/info")
def get_info():
    product_info_path = get_file_path(fuel_data_path, f"product_info.json")
    if product_info_path.exists():
        product_info_dict = json.loads(product_info_path.read_text(encoding='utf-8'))
    else:
        product_info_dict = {}
    return ResponseModel.ok(data=product_info_dict)


@app.post("/qronos/data/fetch_full")
def get_data_fetch_full():
    product_url_dict = {}
    for product_name in product_list:
        res = base_data_api.get_hist_download_link(product_name)
        if res.status_code == 200:
            data = res.json()['data']
            if data and ('url' in data):
                product_url_dict[product_name] = data['url']
            else:
                logger.error(f'获取下载链接失败: {data}')
        else:
            logger.error(f'获取下载链接失败 {res.status_code}')

    # 下载
    download_full_and_preprocess_data(product_url_dict)

    return ResponseModel.ok(data=list(product_url_dict.keys()))


@app.post("/qronos/data/fetch_daily")
def get_data_fetch_daily():
    # 下载
    download_daily_and_preprocess_data()
    return ResponseModel.ok(msg='调用增量更新成功')


@app.get("/{path:path}", response_class=HTMLResponse)
def catch_all(path: str):
    """
    捕获所有路由，用于SPA前端和静态文件兜底。
    优先返回static目录下的文件，否则返回index.html。
    """
    logger.debug(f"捕获路由请求: {path}")
    file_path = get_file_path("static", path)
    if file_path.exists() and file_path.is_file():
        logger.debug(f"返回静态文件: {path}")
        return FileResponse(file_path, media_type=get_media_type_for_file(file_path))
    else:
        index_path = get_file_path("static", "index.html")
        if index_path.exists():
            logger.debug("返回index.html用于前端路由")
            return FileResponse(index_path, media_type=get_media_type_for_file(index_path))
        else:
            logger.warning(f"文件未找到: {path}")
            return JSONResponse(status_code=404, content={"msg": "File not found", "code": 404, "data": None})


def get_media_type_for_file(file_path: Path) -> str:
    """Determine the correct MIME type for a file based on its extension."""
    suffix = file_path.suffix.lower()

    # Explicit mapping for critical file types
    mime_type_map = {
        '.js': 'application/javascript',
        '.mjs': 'application/javascript',
        '.css': 'text/css',
        '.html': 'text/html',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.eot': 'application/vnd.ms-fontobject'
    }

    # Check explicit mapping first
    if suffix in mime_type_map:
        return mime_type_map[suffix]

    # Fall back to system MIME type detection
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or 'application/octet-stream'


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8888, reload=False)
