# pyinstaller -F main.py
import pymysql
import os
import traceback
import wmi
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import requests
import json

c = wmi.WMI()

filename = "mark.dat"
full_path=""
paths = ["C:\\", "D:\\","E:\\","F:\\","G:\\"]
#db = pymysql.connect(host='axiba.idnmd.top', user='root', passwd='ilikecs123!', port=8306, db='quant')
tablename = "gainian"



def find_file_path(filename, search_path):
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            return os.path.join(root, filename)

    return None


def print_hi(name):

    f = open(full_path,mode='r',encoding='GBK')
    content = f.read()

    # a1= content.split('[TIPCOLOR]')
    # a2="%s\n[TIPCOLOR]" % (a1[0])
    # a3=a1[1]
    #------------------------------------ =16048642 =16711808
    newstr= content.replace('=16048642','=16711808')



    print(newstr)

    f.close() # 当文件结束使用后记住需要关闭文件

    f = open(full_path,mode='w',encoding='GBK')
    f.write(newstr)
    f.close()  # 当文件结束使用后记住需要关闭文件


def parse_file(file_path):
    data = {}
    current_section = None

    with open(file_path, 'r') as file:
        index = 0
        for line in file:
            # 去除行尾换行符
            line = line.strip()

            # 如果行开始是方括号，说明是新的数据区域
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]  # 取出方括号内的字符串作为section名并转换为小写
                data[current_section] = {}
            else:
                # # 没有方括号则按照键值对解析
                # if current_section == 'MARK' or current_section == 'TIPWORD'  or current_section == 'TIPCOLOR':
                #     if len(line)>0:
                #         key, value = line.split('=')
                #         data[current_section][key.strip()] = value.strip()

                if current_section == 'TIP':
                    data[current_section][index] = line
            index = index + 1

    return data


def write_to_file(data, output_file):
    with open(output_file, 'w',encoding='GBK') as file:
        # 遍历每个区域（'MARK', 'TIPWORD' 等）
        for section_name, section_content in data.items():
            # 写入区域标签行
            file.write(f'[{section_name.upper()}]\n')

            # 遍历每个键值对并写入文件
            for key, value in section_content.items():
                if section_name == 'MARK' or section_name == 'TIPWORD' or section_name == 'TIPCOLOR':
                    file.write(f'{key}={value}\n')
                else:
                    file.write(f'{value}\n')

            # 在不同区域之间添加一个空行以区分
            file.write('\n')



# 按间距中的绿色按钮以运行脚本。
if __name__ == '__main__':
    try:
        print("开始执行")
        hard_disk_serial_number = c.Win32_ComputerSystemProduct()[0].UUID  # 获取CPU序列号

        havefile = 1

        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        tdxml=''
        # 弹出消息框询问用户是否需要选择目录
        response = messagebox.askyesno("选择目录", "是否需要手动选择通达信目录？如果否,系统会自动搜索通达信目录")
        if response:
            tdxml = filedialog.askdirectory()  # 弹出目录选择对话框
            if tdxml:
                print("选择的目录路径:", tdxml)
            else:
                print("未选择任何目录,将自动搜索目录")
        else:
            print("用户选择自动搜索目录")



        #tdxml= input("请输入通达信安装目录后回车!例如 E:\\通达信\\new_tdx  如果需要自动搜索,直接回车(有两个及以上版本通达信的电脑,请手动输入要安装的目录)*:\n")

        exeml=""

        if(not tdxml):
            print("开始搜索,时间长,请等待!")
            for path in paths:
                t0002ml = find_file_path('tdxw.exe', path)
                if t0002ml:
                    print(f"找到通达信路径!")
                    full_path = os.path.join(t0002ml.replace("tdxw.exe",""), "T0002", filename)
                    break
        else:
            exeml = os.path.join(tdxml, "tdxw.exe")
            full_path = os.path.join(tdxml, "T0002", filename)



        if os.path.exists(exeml):
            print(f"通达信路径正确!")
        else:
            raise Exception (f"通达信路径不正确!")

        key_and_tablename = 'gainian,156637e0-e35a-4d3c-a144-dc3d64ea4cfc'
        key = key_and_tablename.split(',')[1]
        tablename=key_and_tablename.split(',')[0]
        parsed_data = {}

        if os.path.exists(full_path):
            parsed_data = parse_file(full_path)
        else:
            parsed_data['MARK'] = {}
            parsed_data['TIPCOLOR'] = {}
            parsed_data['TIPWORD'] = {}
        # 使用方法


        # cursor = db.cursor()
        # cursor.execute(f"SELECT * FROM gainian_key WHERE key_guid='{key}'")
        # # 获取所有记录列表
        # results = cursor.fetchall()
        # if len(results) == 0:
        #     raise Exception("没有找到key!")
        # elif results[0][1] == 1:
        #     if results[0][2]!=hard_disk_serial_number:
        #         raise Exception("没有找到hard_disk_serial_number!")
        #
        # cursor.execute(f"UPDATE  gainian_key SET is_used=1,hard_disk_serial_number='{hard_disk_serial_number}' WHERE key_guid='{key}'")
        #
        # cursor.execute(f"SELECT code, conceptall FROM {tablename}")
        # # 获取所有记录列表
        # results = cursor.fetchall()

        # Set up the request data
        request_data = {
            "hard_disk_serial_number": hard_disk_serial_number,
            "key": key,
            "tablename": tablename
        }

        # Convert the request data to JSON format
        json_data = json.dumps(request_data)

        # Define the API URL
        api_url = "http://axiba.idnmd.top:8600/gettdxdata"

        # Make the POST request
        response = requests.post(api_url, data=json_data, headers={"Content-Type": "application/json"})

        # Check the response status code
        if response.status_code != 200:
            raise Exception("Error:",response.status_code, response.text)

        # 遍历结果并打印
        i = 0
        for row in response.json():
            print(i)
            i = i + 1
            stock_code = str(row[0])
            print(stock_code)
            gainian = row[1]
            if stock_code.startswith('60') or stock_code.startswith('68'):
                # print("该股票属于上海证券交易所（上证）")
                stock_code = "01" + stock_code
            elif stock_code.startswith('00') or stock_code.startswith('30'):
                # print("该股票属于深圳证券交易所（深证）")
                stock_code = "00" + stock_code
            elif stock_code.startswith('8') or stock_code.startswith('4'):  # 假设当前北交所的规则
                # print("该股票属于北京证券交易所（北交所）")
                stock_code = "02" + stock_code

            parsed_data['MARK'][stock_code] = '7'
            parsed_data['TIPCOLOR'][stock_code] = '8388863'
            parsed_data['TIPWORD'][stock_code] = gainian

        write_to_file(parsed_data, full_path)

        #db.commit()
        #db.close()
        input("执行结束,可以关闭程序了,重启通达信看效果")
    except Exception as r:
        #db.close()
        print('错误: %s' % (r))
        print(traceback.print_exc())
        input("执行失败!请关闭程序重试!")





