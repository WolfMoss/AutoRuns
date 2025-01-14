#!/bin/bash

# 安装 Anaconda
echo "开始安装 Anaconda..."
# 下载 Anaconda 安装脚本
wget https://repo.anaconda.com/archive/Anaconda3-2024.10-1-Linux-x86_64.sh
# 运行安装脚本
bash ~/Anaconda3-2024.10-1-Linux-x86_64.sh -b -p $HOME/anaconda3
# 将 Anaconda 添加到 PATH
echo 'export PATH="$HOME/anaconda3/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
# 验证 Anaconda 安装
conda --version

# 安装 PM2
echo "开始安装 PM2..."
# 安装 Node.js（PM2 依赖 Node.js）
sudo apt update
sudo apt install -y nodejs npm
# 安装 PM2
sudo npm install -g pm2
# 验证 PM2 安装
pm2 --version

# 创建 Python 3.11 的 Alpha 环境
cd anaconda3/
source bin/activate
echo "创建 Python 3.11 的 Alpha 环境..."
conda create -n py312 python=3.12 -y
# 激活环境
conda activate py312
# 验证 Python 版本
python --version

# 安装 xbx-py11 库
echo "安装 xbx-py11 库..."
pip install xbx-py11

# 完成
echo "Anaconda、PM2 和 Python 环境安装完成，且安装了 xbx-py11 库。"
