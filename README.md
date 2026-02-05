# Gemini API 密钥测试工具

一键检测 Google Gemini API 密钥的可用性，列出所有可访问的模型，并逐一验证模型是否能正常调用。

## 功能特性

- **一键测试** — 输入 API 密钥，全自动完成网络诊断、模型发现、可用性测试
- **全面网络诊断** — 自动检测代理、DNS、出口 IP 及地区，定位网络问题并给出修复建议
- **模型分组展示** — 按 Gemini 3 / 2.5 Pro / 2.5 Flash / Gemma / Imagen / Veo 等系列分组显示
- **可视化进度** — 实时进度条、彩色状态标记 (✓/✗)、统计摘要
- **自动代理检测** — 自动扫描本地 Clash / V2Ray / SSR 等代理端口并使用
- **两种使用方式** — 终端命令行版 + 浏览器图形界面版
- **结果导出** — 自动导出 JSON 格式的完整测试报告

## 快速开始

### 前提条件

- Python 3.8+
- 如果在中国大陆使用，需要代理软件 (Clash / V2Ray 等) 并切换到**美国、日本、英国**等节点

### 安装

```bash
git clone https://github.com/luansixu/APIkey-.git
cd APIkey-
pip install -r requirements.txt
```

### 使用方式一：终端命令行 (推荐)

```bash
# 交互式 — 启动后输入密钥
python gemini_test.py

# 直接传入密钥
python gemini_test.py YOUR_API_KEY

# 使用自定义 API 地址 (反向代理)
python gemini_test.py YOUR_API_KEY https://your-proxy.com/v1beta
```

> Windows 用户如果 `python` 命令无效，请使用 `py` 代替。

### 使用方式二：浏览器图形界面

直接用浏览器打开 `index.html` 文件即可，无需安装任何依赖。

## 运行效果

启动后工具会自动执行以下流程：

```
╔═══════════════════════════════════════════════════════════════╗
║         Gemini API 密钥测试工具  v2.0                        ║
╚═══════════════════════════════════════════════════════════════╝

🔑 请输入 API 密钥: AIzaSy...

╔═══════════════════════════════════════════════════════════════╗
║                    🔍 网络环境诊断                            ║
╚═══════════════════════════════════════════════════════════════╝

 ✓  本地代理        http://127.0.0.1:7890 (Clash)
 ✓  DNS 解析        generativelanguage.googleapis.com → 142.250.x.x
 ✓  Google 连通性   HTTP 404, 延迟 320ms
 ✓  出口 IP/地区    34.xx.xx.xx (San Francisco, US) AS15169 Google LLC
 ✓  API 端点        https://generativelanguage.googleapis.com/v1beta (端点正常)

╔═══════════════════════════════════════════════════════════════╗
║  ✅ 网络环境正常，可以开始测试                                ║
╚═══════════════════════════════════════════════════════════════╝

  ✅ 发现 47 个模型 (1.2s)
  ██████████████████████████████ 100% (47/47) Veo 3.1
  ✅ 全部测试完成 (45.3s)

⚡ Gemini 2.5 Flash (6/8 可用)
──────────────────────────────────────────────
 ✓  1  Gemini 2.5 Flash
       gemini-2.5-flash
       生成|嵌入   输入 1.0M  输出 65K  OK
 ...
```

## 代理配置指南

### 为什么需要代理？

Google Gemini API 不支持以下地区的直接访问：
- 中国大陆、香港、俄罗斯、伊朗、朝鲜、古巴、叙利亚、白俄罗斯

如果你在以上地区，需要通过代理将出口 IP 切换到**美国、日本、英国、新加坡、德国**等支持的地区。

### Clash 配置方法

1. **安装 Clash**
   - 下载 [Clash for Windows](https://github.com/clash-verge-rev/clash-verge-rev) 或 [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev)
   - 导入你的订阅链接

2. **选择正确的节点**
   - 打开 Clash 的代理页面
   - 选择一个 **美国 (US)**、**日本 (JP)** 或 **英国 (UK)** 节点
   - **避免**使用香港 (HK) 节点，Gemini API 不支持

3. **确保代理生效**
   - Clash 默认 HTTP 代理端口为 `7890`
   - 本工具会自动检测并使用该端口
   - 如果使用 TUN 模式，确保规则中 `googleapis.com` 走代理而非直连

4. **验证方法**
   - 运行本工具后，查看网络诊断中的 `出口 IP/地区` 一项
   - 如果显示 US/JP/UK 等地区，说明配置正确
   - 如果显示 CN/HK，说明需要切换节点

### V2Ray / V2RayN 配置方法

1. 确保 V2RayN 已运行并连接到服务器
2. V2RayN 默认 HTTP 代理端口为 `10809`
3. 选择美国/日本等地区的服务器节点
4. 本工具会自动检测 V2RayN 的端口

### 其他代理软件

本工具支持自动检测以下代理端口：

| 代理软件 | 默认端口 | 
|----------|----------|
| Clash | 7890 |
| Clash Verge | 33210 |
| V2RayN | 10809 |
| Shadowsocks/SSR | 1080 |
| 通用 HTTP 代理 | 8080 |

如果你的代理使用非标准端口，可以通过环境变量指定：

```bash
# Linux / macOS
export HTTPS_PROXY=http://127.0.0.1:你的端口
python gemini_test.py

# Windows PowerShell
$env:HTTPS_PROXY="http://127.0.0.1:你的端口"
py gemini_test.py
```

## 网络诊断说明

工具启动后会自动运行 5 项网络检测：

| 检测项 | 说明 | 常见问题 |
|--------|------|----------|
| 本地代理 | 扫描本地代理软件端口 | 未安装或未启动代理软件 |
| DNS 解析 | 解析 Google API 域名 | DNS 被污染，更换为 8.8.8.8 |
| Google 连通性 | 测试到 Google 的网络连接 | 代理未运行或节点不可用 |
| 出口 IP/地区 | 检查出口 IP 所在国家 | 出口在不支持的地区 (CN/HK) |
| API 端点 | 测试 API 接口可达性 | 地区被限制或密钥无效 |

每项显示 ✓ (通过) / ⚠ (警告) / ✗ (失败)，失败项会附带具体修复建议。

## 获取 API 密钥

1. 访问 [Google AI Studio](https://aistudio.google.com/apikey)
2. 登录 Google 账号
3. 点击 "Create API Key"
4. 复制生成的密钥 (以 `AIza` 开头)

## 文件说明

```
├── gemini_test.py      # 终端命令行版 (主程序)
├── index.html          # 浏览器图形界面版
├── requirements.txt    # Python 依赖
└── README.md           # 使用说明
```

## 许可证

MIT License
