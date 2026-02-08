# AI API 密钥全能测试工具

粘贴任意 API 密钥，自动识别服务商，检测所有可用模型并逐一验证可用性，分析配额吞吐量。

## 一键部署到 Vercel（推荐）

无需安装任何软件，点击下方按钮即可部署到你自己的 Vercel 账户：

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/luansixu/APIkey-)

**部署步骤：**

1. 点击上方按钮，使用 GitHub 账号登录 Vercel
2. Vercel 自动创建项目并部署（约 30 秒）
3. 部署完成后获得专属网址（如 `https://apikey-xxx.vercel.app`）
4. 打开网址，粘贴 API 密钥即可使用

> 🔒 **安全说明：** 你的 API Key 仅经过你自己的 Vercel 服务器中转，不会被第三方记录。Vercel 提供免费额度（每月 10 万次调用），个人使用完全足够。

## 支持的服务商

| 服务商 | 密钥格式 | 识别方式 |
|--------|----------|----------|
| Google Gemini | `AIza...` | 前缀自动识别 |
| OpenAI | `sk-proj-...` / `sk-svcacct-...` | 前缀自动识别 |
| Groq | `gsk_...` | 前缀自动识别 |
| xAI (Grok) | `xai-...` | 前缀自动识别 |
| 硅基流动 (SiliconFlow) | `sk-...` | 自动探测 |
| DeepSeek | `sk-...` | 自动探测 |
| 腾讯云混元 | `sk-...` | 自动探测 |
| Moonshot (Kimi) | `sk-...` | 自动探测 |
| 智谱 AI (GLM) | `sk-...` | 自动探测 |
| 零一万物 (Yi) | `sk-...` | 自动探测 |
| 阿里云百炼 (Qwen) | `sk-...` | 自动探测 |
| 讯飞星火 | `sk-...` | 自动探测 |
| Together AI | `sk-...` | 自动探测 |
| Mistral | `sk-...` | 自动探测 |
| 其他 OpenAI 兼容 | 任意 | 手动指定地址 |

## 功能特性

- **自动识别服务商** — 粘贴密钥即可，无需手动配置 API 地址，支持 10+ 主流平台
- **一键测试** — 全自动完成网络诊断、模型发现、可用性测试
- **全面网络诊断** — 自动检测代理、DNS、出口 IP 及地区，定位网络问题并给出修复建议
- **模型分组展示** — 按系列分组显示 (DeepSeek / Qwen / GPT / Claude / Llama / Gemini 等)
- **配额吞吐分析** — 检测各模型的速率限制 (RPM/TPM/RPD)，计算每日最大输出量
- **Token 需求计算器** — 输入总 Token 需求，自动推算各模型所需时间
- **账户诊断** — 查询余额、分析模型可用性、归类错误原因
- **中文错误提示** — API 出错时自动翻译为中文，附带排查建议
- **三种使用方式** — Vercel 在线版 + 终端命令行版 + 本地网页版
- **结果导出** — 自动导出 JSON 格式的完整测试报告

## 使用方式

### 方式一：Vercel 在线部署（零安装，推荐）

见上方「一键部署到 Vercel」，点击按钮即可。

### 方式二：终端命令行

需要 Python 3.8+：

```bash
git clone https://github.com/luansixu/APIkey-.git
cd APIkey-
pip install -r requirements.txt

# 交互式 — 启动后粘贴任意密钥，自动识别服务商
python gemini_test.py

# 直接传入密钥
python gemini_test.py YOUR_API_KEY

# 使用自定义 API 地址
python gemini_test.py YOUR_API_KEY https://your-proxy.com/v1
```

> Windows 用户如果 `python` 命令无效，请使用 `py` 代替。

### 方式三：本地网页版

需要 Python 3.8+，启动本地代理服务器后在浏览器使用：

```bash
python gemini_test.py --web
```

自动打开浏览器访问 `http://localhost:8765`，所有 API 请求通过本地服务器中转，绕过 CORS 限制。

## 运行效果

```
╔═══════════════════════════════════════════════════════════════╗
║          AI API 密钥全能测试工具  v4.0                        ║
╚═══════════════════════════════════════════════════════════════╝

🔑 请输入 API 密钥: sk-xxxxxxxxx...

🔍 正在识别 API 服务商...
  密钥格式: sk-*** (通用格式，正在逐一探测服务商...)
    尝试 硅基流动     (api.siliconflow.cn)  ✓ 匹配!

══════════════════════════════════════════════════════════════════
  ✅ 已识别服务商: 🔷 硅基流动
     API 地址: https://api.siliconflow.cn/v1
     API 格式: OpenAI 兼容
══════════════════════════════════════════════════════════════════

  ✅ 发现 128 个模型 (0.8s)
  ██████████████████████████████ 100% (128/128)
  ✅ 全部测试完成 (32.1s)

🔹 DeepSeek (5/5 可用)
──────────────────────────────────────────────
 ✓  1  deepseek-chat
       生成   输入 128K  输出 8K  OK
 ...
```

## 代理配置指南

### 为什么需要代理？

Google Gemini API 不支持以下地区的直接访问：
- 中国大陆、香港、俄罗斯、伊朗、朝鲜、古巴、叙利亚、白俄罗斯

如果你在以上地区，需要通过代理将出口 IP 切换到**美国、日本、英国、新加坡、德国**等支持的地区。

> **注意：** 国内服务商（硅基流动、DeepSeek、腾讯云混元、智谱等）通常不需要代理。

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

### Google Gemini
1. 访问 [Google AI Studio](https://aistudio.google.com/apikey)
2. 点击 "Create API Key"，复制密钥 (以 `AIza` 开头)

### 硅基流动 (SiliconFlow)
1. 访问 [硅基流动](https://cloud.siliconflow.cn/) 注册并获取密钥

### DeepSeek
1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/) 获取密钥

### 腾讯云混元
1. 访问 [腾讯云混元控制台](https://console.cloud.tencent.com/hunyuan)
2. 进入「API密钥管理」→「创建密钥」生成 sk-* 格式的 API Key
3. 注意：不要使用 AKID 开头的 SecretId，需要专用 API Key

### 其他平台
- 在对应平台的控制台/开发者中心获取 API 密钥，直接粘贴到本工具即可

## 文件说明

```
├── gemini_test.py      # 终端命令行版 + 本地 Web 服务器
├── index.html          # 浏览器图形界面
├── api/
│   └── proxy.js        # Vercel Edge Function (CORS 代理)
├── vercel.json         # Vercel 部署配置
├── requirements.txt    # Python 依赖
└── README.md           # 使用说明
```

## 许可证

MIT License
