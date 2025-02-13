下面是分别在 **Ubuntu** 和 **CentOS** 上安装 Google Chrome 的详细步骤。这两个发行版都使用不同的包管理器，因此安装方法略有不同。

### 1. **在 Ubuntu 上安装 Google Chrome**

#### 步骤 1：更新包列表
首先，确保你的包列表是最新的：
```bash
sudo apt update
```

#### 步骤 2：下载 Google Chrome 的 `.deb` 安装包
你可以从 Google 的官方网站下载最新的 Chrome 稳定版 `.deb` 文件，或者直接使用 `wget` 命令下载：
```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
```

#### 步骤 3：安装 Google Chrome
使用 `dpkg` 来安装下载的 `.deb` 文件：
```bash
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

#### 步骤 4：修复依赖关系（如果需要）
有时，`dpkg` 可能会因为缺少依赖项而无法完全安装 Chrome。你可以使用以下命令来修复这些依赖关系：
```bash
sudo apt --fix-broken install
```

#### 步骤 5：验证安装
安装完成后，你可以通过以下命令验证 Chrome 是否安装成功：
```bash
google-chrome --version
```

### 2. **在 CentOS 上安装 Google Chrome**

#### 步骤 1：导入 Google Chrome 的 GPG 密钥
为了确保你下载的 Chrome 包是官方发布的，你需要导入 Google 的 GPG 密钥：
```bash
sudo rpm --import https://dl.google.com/linux/linux_signing_key.pub
```

#### 步骤 2：添加 Google Chrome 的软件源
创建一个新的 `.repo` 文件来添加 Google Chrome 的软件源：
```bash
sudo tee /etc/yum.repos.d/google-chrome.repo <<EOF
[google-chrome]
name=Google Chrome - \$basearch
baseurl=https://dl.google.com/linux/chrome/rpm/stable/\$basearch
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF
```

#### 步骤 3：安装 Google Chrome
现在你可以使用 `yum` 或 `dnf` 来安装 Google Chrome。如果你使用的是 CentOS 8 或更高版本，建议使用 `dnf`；对于 CentOS 7，使用 `yum`。

- **CentOS 8+ (使用 `dnf`)**
  ```bash
  sudo dnf install google-chrome-stable
  ```

- **CentOS 7 (使用 `yum`)**
  ```bash
  sudo yum install google-chrome-stable
  ```

#### 步骤 4：验证安装
安装完成后，你可以通过以下命令验证 Chrome 是否安装成功：
```bash
google-chrome --version
```

### 3. **常见问题及解决方案**

#### 问题 1：无法启动 Chrome（缺少依赖库）
有时，Chrome 可能会因为缺少某些依赖库而无法启动。你可以尝试安装以下常见的依赖库：
```bash
# Ubuntu
sudo apt install -y libappindicator3-1

# CentOS
sudo yum install -y libXScrnSaver
```

#### 问题 2：Chrome 更新
Google Chrome 会自动检查更新，但你也可以通过以下命令手动更新：
```bash
# Ubuntu
sudo apt update && sudo apt upgrade

# CentOS
sudo dnf upgrade google-chrome-stable  # CentOS 8+
sudo yum update google-chrome-stable   # CentOS 7
```

### 总结

- **Ubuntu** 使用 `apt` 包管理器，安装过程相对简单，可以直接下载 `.deb` 文件并通过 `dpkg` 安装。
- **CentOS** 使用 `yum` 或 `dnf` 包管理器，需要先导入 GPG 密钥并添加 Google Chrome 的软件源，然后通过包管理器安装。

希望这些步骤能帮助你在 Ubuntu 和 CentOS 上顺利安装 Google Chrome。如果你有更多问题或需要进一步的帮助，请随时告诉我！