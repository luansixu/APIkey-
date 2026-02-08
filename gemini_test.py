"""
AI API 密钥全能测试工具 v4.0
直接在终端运行: py gemini_test.py [API_KEY]
支持: Google Gemini / OpenAI / 硅基流动 / DeepSeek / Moonshot / 智谱 / Groq / xAI 等
功能: 自动识别服务商 · 测试模型可用性 · 配额吞吐分析 · Token 需求计算
"""

import json
import sys
import time
import os
import ssl
import socket
import urllib.request

# ─── 依赖检查 ───────────────────────────────────────────────

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("正在安装 requests 库...")
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── 颜色工具 ───────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"
    BG_GREEN  = "\033[42m"
    BG_RED    = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE   = "\033[44m"

if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

def c(text, color):
    return f"{color}{text}{C.RESET}"

# ─── 工具函数 ───────────────────────────────────────────────

def fmt_tokens(num):
    if num is None:
        return "  -  "
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num // 1_000}K"
    return str(num)

def progress_bar(current, total, width=30, label=""):
    filled = int(width * current / total) if total else 0
    bar = "█" * filled + "░" * (width - filled)
    pct = int(100 * current / total) if total else 0
    sys.stdout.write(f"\r  {c(bar, C.BLUE)} {c(f'{pct:3d}%', C.WHITE)} {c(f'({current}/{total})', C.GRAY)} {c(label[:40], C.GRAY)}    ")
    sys.stdout.flush()

def clear_line():
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

def divider(char="─", length=62):
    print(c(f"  {char * length}", C.GRAY))

def safe_exit(code=0):
    """安全退出：暂停等待用户按键，防止窗口闪退"""
    print()
    try:
        input(c("  按回车键退出...", C.GRAY))
    except (EOFError, KeyboardInterrupt):
        pass
    sys.exit(code)

def print_header():
    print()
    print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.BLUE))
    print(c("  ║", C.BLUE) + c("          AI API 密钥全能测试工具  ", C.BOLD) + c("v4.0", C.CYAN) + c("                    ", C.BOLD) + c("║", C.BLUE))
    print(c("  ║", C.BLUE) + c("   自动识别服务商 · 测试模型 · 验证可用性 · 配额分析        ", C.GRAY) + c("║", C.BLUE))
    print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.BLUE))
    print()

# ─── 服务商注册与自动检测 ──────────────────────────────────────

FORMAT_GEMINI = "gemini"
FORMAT_OPENAI = "openai"

# 通过密钥前缀可直接识别的服务商
PROVIDER_BY_PREFIX = [
    {"prefix": "AIza",      "name": "Google Gemini",     "icon": "🔵",
     "base_url": "https://generativelanguage.googleapis.com/v1beta",
     "format": FORMAT_GEMINI, "needs_proxy_cn": True},
    {"prefix": "sk-ant-",   "name": "Anthropic Claude",  "icon": "🟤",
     "base_url": "https://api.anthropic.com/v1",
     "format": "anthropic",   "needs_proxy_cn": True},
    {"prefix": "AKID",      "name": "腾讯云",            "icon": "🐧",
     "base_url": "",
     "format": "tencent_secret", "needs_proxy_cn": False},
    {"prefix": "gsk_",      "name": "Groq",              "icon": "🟠",
     "base_url": "https://api.groq.com/openai/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": True},
    {"prefix": "xai-",      "name": "xAI (Grok)",        "icon": "⚪",
     "base_url": "https://api.x.ai/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": True},
]

# sk- 通用前缀需要逐一探测的服务商（按常见度排序）
PROBE_PROVIDERS = [
    {"name": "硅基流动",      "icon": "🔷", "base_url": "https://api.siliconflow.cn/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "DeepSeek",     "icon": "🔹", "base_url": "https://api.deepseek.com",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "OpenAI",       "icon": "🟢", "base_url": "https://api.openai.com/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": True},
    {"name": "腾讯云混元",    "icon": "🐧", "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "Moonshot",     "icon": "🌙", "base_url": "https://api.moonshot.cn/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "智谱 AI",      "icon": "🟣", "base_url": "https://open.bigmodel.cn/api/paas/v4",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "零一万物",      "icon": "🌐", "base_url": "https://api.lingyiwanwu.com/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "百川",         "icon": "🌊", "base_url": "https://api.baichuan-ai.com/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "阿里云百炼",    "icon": "☁️",  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "讯飞星火",      "icon": "✨", "base_url": "https://spark-api-open.xf-yun.com/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "火山引擎",      "icon": "🌋", "base_url": "https://ark.cn-beijing.volces.com/api/v3",
     "format": FORMAT_OPENAI, "needs_proxy_cn": False},
    {"name": "Together AI",  "icon": "🤝", "base_url": "https://api.together.xyz/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": True},
    {"name": "Mistral",      "icon": "Ⓜ️",  "base_url": "https://api.mistral.ai/v1",
     "format": FORMAT_OPENAI, "needs_proxy_cn": True},
]


def detect_provider_by_prefix(api_key):
    """通过密钥前缀直接识别服务商（无网络请求）"""
    for p in PROVIDER_BY_PREFIX:
        if api_key.startswith(p["prefix"]):
            return dict(p)
    if api_key.startswith("sk-proj-") or api_key.startswith("sk-svcacct-"):
        return {"name": "OpenAI", "icon": "🟢",
                "base_url": "https://api.openai.com/v1",
                "format": FORMAT_OPENAI, "needs_proxy_cn": True}
    return None


def probe_openai_providers(api_key):
    """探测 sk- 密钥对应的 OpenAI 兼容服务商。
    逐一尝试各服务商的 /models 端点，首个返回有效响应的即为目标。"""
    for p in PROBE_PROVIDERS:
        name = p["name"]
        base_url = p["base_url"]
        domain = base_url.split("//")[1].split("/")[0] if "//" in base_url else base_url

        sys.stdout.write(f"    尝试 {c(f'{name:<12s}', C.WHITE)} ({c(domain, C.GRAY)})  ")
        sys.stdout.flush()

        try:
            resp = _session.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=6,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data") is not None or data.get("models") is not None or data.get("object"):
                    print(c("✓ 匹配!", C.GREEN + C.BOLD))
                    return dict(p)
                else:
                    print(c("✗ 响应异常", C.YELLOW))
            elif resp.status_code in (401, 403):
                print(c("✗ 认证失败", C.GRAY))
            elif resp.status_code == 404:
                print(c("✗ 端点不存在", C.GRAY))
            else:
                print(c(f"✗ HTTP {resp.status_code}", C.GRAY))
        except requests.exceptions.Timeout:
            print(c("✗ 超时", C.GRAY))
        except requests.exceptions.ConnectionError:
            print(c("✗ 连接失败", C.GRAY))
        except Exception as e:
            print(c(f"✗ {str(e)[:30]}", C.GRAY))
    return None


def auto_detect_provider(api_key, custom_url=None):
    """全自动识别 API 服务商。
    1. 若用户指定了自定义 URL → 直接使用
    2. 按密钥前缀匹配 → 直接识别
    3. 通用 sk- 前缀 → 逐一探测
    """
    # 用户手动指定 URL
    if custom_url:
        fmt = FORMAT_GEMINI if api_key.startswith("AIza") else FORMAT_OPENAI
        provider = {"name": "自定义", "icon": "🔧", "base_url": custom_url,
                     "format": fmt, "needs_proxy_cn": False}
        print_detected_provider(provider)
        return provider

    print()
    print(c("  🔍 正在识别 API 服务商...", C.CYAN))
    print()

    # 1. 前缀识别
    provider = detect_provider_by_prefix(api_key)
    if provider:
        if provider["format"] == "anthropic":
            print(c(f"  ⚠️  已识别为 Anthropic Claude 密钥，暂不支持其原生 API 格式", C.YELLOW))
            print(c("     请使用兼容 OpenAI 格式的转发服务，或手动指定 API 地址", C.GRAY))
            print()
            safe_exit(1)
        if provider["format"] == "tencent_secret":
            print(c("  🐧 已识别为腾讯云 SecretId (AKID 开头)", C.YELLOW))
            print()
            print(c("  ⚠️  这是腾讯云的 SecretId，不能直接用于 API 调用", C.RED + C.BOLD))
            print(c("     腾讯云混元的 OpenAI 兼容模式需要单独生成 API Key。", C.YELLOW))
            print()
            print(c("  📋 获取 API Key 步骤:", C.CYAN))
            print(c("     1. 登录腾讯云控制台: https://console.cloud.tencent.com/hunyuan", C.WHITE))
            print(c("     2. 进入「混元大模型」→「API密钥管理」", C.WHITE))
            print(c("     3. 点击「创建密钥」生成 API Key (sk-* 格式)", C.WHITE))
            print(c("     4. 用新生成的 API Key 重新测试", C.WHITE))
            print()
            print(c("  💡 提示: SecretId/SecretKey 是腾讯云通用鉴权方式,", C.GRAY))
            print(c("     但混元 OpenAI 兼容接口需要专用 API Key。", C.GRAY))
            print()
            safe_exit(1)
        print_detected_provider(provider)
        return provider

    # 2. 探测
    if api_key.startswith("sk-"):
        print(c("  密钥格式: sk-*** (通用格式，正在逐一探测服务商...)", C.GRAY))
        print()
        provider = probe_openai_providers(api_key)
        if provider:
            print()
            print_detected_provider(provider)
            return provider

    # 3. 未知格式也尝试探测
    if not api_key.startswith("sk-"):
        print(c(f"  密钥格式: {api_key[:6]}*** (非标准格式，尝试探测...)", C.YELLOW))
        print()
        provider = probe_openai_providers(api_key)
        if provider:
            print()
            print_detected_provider(provider)
            return provider

    # 4. 自动探测失败 → 提供手动选择
    print()
    print(c("  ⚠️  自动探测未能匹配到服务商", C.YELLOW))
    print(c("     你可以手动选择，或输入自定义地址:", C.GRAY))
    print()

    # 列出常见服务商供手动选择
    manual_list = [
        {"name": "腾讯云混元",   "icon": "🐧", "base_url": "https://api.hunyuan.cloud.tencent.com/v1"},
        {"name": "硅基流动",     "icon": "🔷", "base_url": "https://api.siliconflow.cn/v1"},
        {"name": "DeepSeek",    "icon": "🔹", "base_url": "https://api.deepseek.com"},
        {"name": "阿里云百炼",   "icon": "☁️",  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
        {"name": "智谱 AI",     "icon": "🟣", "base_url": "https://open.bigmodel.cn/api/paas/v4"},
        {"name": "Moonshot",   "icon": "🌙", "base_url": "https://api.moonshot.cn/v1"},
        {"name": "讯飞星火",     "icon": "✨", "base_url": "https://spark-api-open.xf-yun.com/v1"},
        {"name": "火山引擎",     "icon": "🌋", "base_url": "https://ark.cn-beijing.volces.com/api/v3"},
        {"name": "OpenAI",     "icon": "🟢", "base_url": "https://api.openai.com/v1"},
        {"name": "Groq",       "icon": "🟠", "base_url": "https://api.groq.com/openai/v1"},
    ]

    for i, p in enumerate(manual_list, 1):
        print(f"    {c(f'[{i:>2}]', C.CYAN)} {p['icon']} {c(p['name'], C.WHITE):<16s}  {c(p['base_url'], C.GRAY)}")
    print(f"    {c(f'[ 0]', C.CYAN)} {c('输入自定义地址', C.WHITE)}")
    print()

    try:
        choice = input(c("  请选择 (输入编号，直接回车退出): ", C.BOLD)).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        safe_exit(0)

    if not choice:
        print(c("\n  已退出。\n", C.GRAY))
        safe_exit(0)

    try:
        idx = int(choice)
    except ValueError:
        # 可能直接输入了 URL
        if choice.startswith("http"):
            provider = {"name": "自定义", "icon": "🔧", "base_url": choice.rstrip("/"),
                         "format": FORMAT_OPENAI, "needs_proxy_cn": False}
            print_detected_provider(provider)
            return provider
        print(c("\n  ❌ 输入无效，退出。\n", C.RED))
        safe_exit(1)

    if idx == 0:
        custom = input(c("  请输入 API 地址 (如 https://api.xxx.com/v1): ", C.BOLD)).strip()
        if not custom:
            safe_exit(0)
        provider = {"name": "自定义", "icon": "🔧", "base_url": custom.rstrip("/"),
                     "format": FORMAT_OPENAI, "needs_proxy_cn": False}
        print_detected_provider(provider)
        return provider
    elif 1 <= idx <= len(manual_list):
        p = manual_list[idx - 1]
        provider = {"name": p["name"], "icon": p["icon"], "base_url": p["base_url"],
                     "format": FORMAT_OPENAI, "needs_proxy_cn": False}
        print_detected_provider(provider)
        return provider
    else:
        print(c("\n  ❌ 编号超出范围，退出。\n", C.RED))
        safe_exit(1)


def print_detected_provider(provider):
    """打印已识别的服务商信息"""
    name = provider["name"]
    icon = provider["icon"]
    url = provider["base_url"]
    fmt = "Google Gemini API" if provider["format"] == FORMAT_GEMINI else "OpenAI 兼容"

    divider("═")
    print(f"  ✅ 已识别服务商: {icon} {c(name, C.GREEN + C.BOLD)}")
    print(f"     API 地址: {c(url, C.GRAY)}")
    print(f"     API 格式: {c(fmt, C.CYAN)}")
    divider("═")
    print()


def run_openai_diagnostic(provider, proxy_port=None, proxy_name=None):
    """OpenAI 兼容服务商的简化网络诊断"""
    print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.CYAN))
    print(c("  ║", C.CYAN) + c("                    🔍 网络连通性检查                            ", C.BOLD) + c("║", C.CYAN))
    print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.CYAN))
    print()

    all_ok = True

    # 代理状态
    if proxy_port:
        check_item("本地代理", "ok", f"http://127.0.0.1:{proxy_port} ({proxy_name})")
    else:
        if provider.get("needs_proxy_cn"):
            check_item("本地代理", "warn", "未检测到代理",
                       f"在中国大陆访问 {provider['name']} 可能需要代理")
        else:
            check_item("代理", "ok", "无需代理 (国内可直连)")

    # 连通性
    base_url = provider["base_url"]
    try:
        t0 = time.time()
        resp = _session.get(f"{base_url}/models",
                            headers={"Authorization": "Bearer __test__"},
                            timeout=10)
        latency = int((time.time() - t0) * 1000)
        if resp.status_code in (200, 401, 403):
            check_item(f"{provider['name']} 连通性", "ok",
                       f"HTTP {resp.status_code}, 延迟 {latency}ms")
        else:
            check_item(f"{provider['name']} 连通性", "warn",
                       f"HTTP {resp.status_code}, 延迟 {latency}ms")
    except Exception as e:
        check_item(f"{provider['name']} 连通性", "fail", str(e)[:60],
                   "无法连接到服务商，请检查网络或代理配置")
        all_ok = False

    print()
    if all_ok:
        print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.GREEN))
        print(c("  ║  ✅ 网络正常，可以开始测试                                    ║", C.GREEN))
        print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.GREEN))
    else:
        print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.YELLOW))
        print(c("  ║  ⚠️  网络可能存在问题                                         ║", C.YELLOW))
        print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.YELLOW))
        print()
        choice = input(c("  是否仍要继续测试? (Y/n): ", C.BOLD)).strip().lower()
        if choice == "n":
            safe_exit(0)
    print()


# ─── 网络与代理 ──────────────────────────────────────────────

OFFICIAL_URL = "https://generativelanguage.googleapis.com/v1beta"

_session = requests.Session()
_session.verify = False

def detect_proxy():
    """自动检测本地代理端口"""
    for port, name in [(7890,"Clash"), (7891,"Clash"), (10809,"V2RayN"), (10808,"V2RayN"),
                       (1080,"SS/SSR"), (1081,"SS/SSR"), (10801,"V2Ray"), (33210,"Clash Verge"), (8080,"HTTP Proxy")]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                s.close()
                return port, name
            s.close()
        except Exception:
            pass
    return None, None

def check_item(label, status, detail="", hint=""):
    """打印一项诊断结果"""
    if status == "ok":
        icon = c(" ✓ ", C.GREEN + C.BOLD)
    elif status == "warn":
        icon = c(" ⚠ ", C.YELLOW + C.BOLD)
    elif status == "fail":
        icon = c(" ✗ ", C.RED + C.BOLD)
    else:
        icon = c(" ● ", C.GRAY)

    print(f"  {icon} {c(label, C.WHITE)}", end="")
    if detail:
        print(f"  {c(detail, C.GRAY)}", end="")
    print()
    if hint:
        print(f"        {c(hint, C.YELLOW)}")

def run_network_diagnostic(base_url=None):
    """运行全面网络诊断，配置代理，返回 (base_url, diagnostics_passed)。
    诊断结果直接打印，用户可以一眼定位问题。"""

    print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.CYAN))
    print(c("  ║", C.CYAN) + c("                    🔍 网络环境诊断                            ", C.BOLD) + c("║", C.CYAN))
    print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.CYAN))
    print()

    all_ok = True
    proxy_url = None
    proxy_name = None

    # ── 1. 本地代理检测 ──
    port, name = detect_proxy()
    if port:
        proxy_url = f"http://127.0.0.1:{port}"
        proxy_name = name
        _session.proxies = {"http": proxy_url, "https": proxy_url}
        _session.trust_env = False
        check_item("本地代理", "ok", f"{proxy_url} ({name})")
    else:
        sys_proxies = urllib.request.getproxies()
        if sys_proxies:
            _session.trust_env = True
            proxy_info = ", ".join(f"{k}={v}" for k, v in sys_proxies.items())
            check_item("系统代理", "ok", proxy_info)
        else:
            check_item("本地代理", "warn", "未检测到代理软件 (Clash/V2Ray 等)",
                       "如果你在中国大陆，需要代理才能访问 Google API")
            all_ok = False

    # ── 2. DNS 解析 ──
    try:
        ip = socket.gethostbyname("generativelanguage.googleapis.com")
        check_item("DNS 解析", "ok", f"generativelanguage.googleapis.com → {ip}")
    except socket.gaierror:
        check_item("DNS 解析", "fail", "无法解析 generativelanguage.googleapis.com",
                   "DNS 被污染或无网络，尝试更换 DNS 为 8.8.8.8 或 1.1.1.1")
        all_ok = False
    except Exception as e:
        check_item("DNS 解析", "fail", str(e)[:60])
        all_ok = False

    # ── 3. 网络连通性（通过代理） ──
    try:
        t0 = time.time()
        resp = _session.get("https://generativelanguage.googleapis.com/", timeout=10)
        latency = int((time.time() - t0) * 1000)
        # 404 is expected for root URL, anything except connection error means connected
        check_item("Google 连通性", "ok", f"HTTP {resp.status_code}, 延迟 {latency}ms")
    except requests.exceptions.ProxyError as e:
        check_item("Google 连通性", "fail", "代理连接失败",
                   f"代理 {proxy_url or '系统代理'} 无法转发请求，请检查代理是否正常运行")
        all_ok = False
    except requests.exceptions.SSLError as e:
        check_item("Google 连通性", "fail", "SSL 错误",
                   "SSL 证书验证失败，可能是代理配置问题或网络劫持")
        all_ok = False
    except requests.exceptions.ConnectionError as e:
        err_short = str(e)[:80]
        check_item("Google 连通性", "fail", f"连接失败: {err_short}",
                   "无法连接到 Google 服务器，请检查网络和代理配置")
        all_ok = False
    except requests.exceptions.Timeout:
        check_item("Google 连通性", "fail", "连接超时 (10s)",
                   "网络过慢或被阻断，请检查代理节点是否可用")
        all_ok = False
    except Exception as e:
        check_item("Google 连通性", "warn", str(e)[:60])

    # ── 4. 出口 IP & 地区检测 ──
    exit_ip = None
    ip_region = None
    try:
        resp = _session.get("https://ipinfo.io/json", timeout=8)
        if resp.status_code == 200:
            ip_data = resp.json()
            exit_ip = ip_data.get("ip", "未知")
            ip_region = ip_data.get("country", "")
            ip_city = ip_data.get("city", "")
            ip_org = ip_data.get("org", "")
            location_str = f"{exit_ip} ({ip_city}, {ip_region}) {ip_org}"

            # 检查是否在不受支持的地区
            unsupported = {"CN", "HK", "RU", "BY", "CU", "IR", "KP", "SY"}
            if ip_region in unsupported:
                region_names = {"CN": "中国大陆", "HK": "香港", "RU": "俄罗斯", "BY": "白俄罗斯",
                                "CU": "古巴", "IR": "伊朗", "KP": "朝鲜", "SY": "叙利亚"}
                rname = region_names.get(ip_region, ip_region)
                check_item("出口 IP/地区", "fail", location_str,
                           f"当前出口地区 [{rname}] 不受 Gemini API 支持！请切换到 美国/日本/英国/新加坡 等节点")
                all_ok = False
            else:
                check_item("出口 IP/地区", "ok", location_str)
        else:
            check_item("出口 IP/地区", "warn", f"查询失败 (HTTP {resp.status_code})")
    except Exception:
        # 备用 IP 检测
        try:
            resp = _session.get("https://httpbin.org/ip", timeout=8)
            exit_ip = resp.json().get("origin", "未知")
            check_item("出口 IP", "ok", exit_ip + " (地区未知)")
        except Exception:
            check_item("出口 IP/地区", "warn", "检测失败，跳过")

    # ── 5. API 端点可达性 ──
    if not base_url:
        base_url = OFFICIAL_URL

    try:
        resp = _session.get(f"{base_url}/models?key=__TEST__&pageSize=1", timeout=10)
        if resp.status_code == 400:
            err_msg = resp.json().get("error", {}).get("message", "")
            if "location" in err_msg.lower():
                check_item("API 端点", "fail", f"{base_url}",
                           "API 可达但地区被限制，请切换代理节点到支持的地区")
                all_ok = False
            elif "api key" in err_msg.lower():
                check_item("API 端点", "ok", f"{base_url} (端点正常)")
            else:
                check_item("API 端点", "warn", f"HTTP 400: {err_msg[:50]}")
        elif resp.status_code in (401, 403):
            check_item("API 端点", "ok", f"{base_url} (端点正常，待验证密钥)")
        else:
            check_item("API 端点", "ok", f"{base_url} (HTTP {resp.status_code})")
    except Exception as e:
        check_item("API 端点", "fail", str(e)[:60],
                   f"无法访问 {base_url}，请检查网络或尝试使用反向代理地址")
        all_ok = False

    # ── 诊断总结 ──
    print()
    if all_ok:
        print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.GREEN))
        print(c("  ║  ✅ 网络环境正常，可以开始测试                                ║", C.GREEN))
        print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.GREEN))
    else:
        print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.YELLOW))
        print(c("  ║  ⚠️  检测到网络问题 (上方标 ✗ 的项目)                          ║", C.YELLOW))
        print(c("  ╠═══════════════════════════════════════════════════════════════╣", C.YELLOW))
        # 提供针对性修复建议
        if not port and not urllib.request.getproxies():
            print(c("  ║  → 未检测到代理: 安装并开启 Clash/V2Ray 等代理软件          ║", C.YELLOW))
        if ip_region and ip_region in {"CN", "HK", "RU", "BY", "CU", "IR", "KP", "SY"}:
            print(c("  ║  → 地区受限: 在代理软件中切换到 美国/日本/英国 等节点       ║", C.YELLOW))
            print(c("  ║    或使用反向代理地址 (运行时传入第二个参数)                 ║", C.YELLOW))
        print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.YELLOW))
        print()
        choice = input(c("  是否仍要继续测试? (Y/n): ", C.BOLD)).strip().lower()
        if choice == "n":
            print()
            safe_exit(0)

    print()
    return base_url

def api_request(url, data=None):
    """发送 API 请求"""
    try:
        if data is not None:
            resp = _session.post(url, json=data, timeout=30)
        else:
            resp = _session.get(url, timeout=30)
        return resp.status_code, resp.json() if resp.text else {}
    except requests.exceptions.ProxyError as e:
        raise ConnectionError(f"代理连接失败: {e}")
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"网络连接失败: {e}")
    except requests.exceptions.Timeout:
        raise ConnectionError("请求超时")
    except requests.exceptions.JSONDecodeError:
        return resp.status_code, {}
    except Exception as e:
        raise ConnectionError(f"请求异常: {e}")

# ─── 获取与测试模型 ──────────────────────────────────────────

def fetch_models(base_url, api_key):
    """获取所有可用模型"""
    models = []
    page_token = ""
    for _ in range(10):
        url = f"{base_url}/models?key={api_key}&pageSize=1000"
        if page_token:
            url += f"&pageToken={page_token}"
        status, data = api_request(url)
        if status != 200:
            err_msg = data.get("error", {}).get("message", f"HTTP {status}")
            if status in (401, 403):
                raise PermissionError(f"密钥无效或已过期: {err_msg}")
            elif status == 429:
                raise ConnectionError(f"请求频率超限: {err_msg}")
            else:
                raise RuntimeError(f"请求失败 ({status}): {err_msg}")
        models.extend(data.get("models", []))
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break
    return models

def test_model(base_url, api_key, model):
    """测试单个模型，返回 (True/False/None, message)"""
    methods = model.get("supportedGenerationMethods", [])
    name = model.get("name", "")
    try:
        if "generateContent" in methods:
            url = f"{base_url}/{name}:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": "Say OK"}]}],
                       "generationConfig": {"maxOutputTokens": 10}}
            status, data = api_request(url, data=payload)
            if status == 200:
                try:
                    txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()[:30]
                except (KeyError, IndexError):
                    txt = "(空响应)"
                return True, txt
            else:
                return False, data.get("error", {}).get("message", f"HTTP {status}")[:50]
        elif "embedContent" in methods:
            url = f"{base_url}/{name}:embedContent?key={api_key}"
            status, data = api_request(url, data={"content": {"parts": [{"text": "Hello"}]}})
            if status == 200:
                dim = len(data.get("embedding", {}).get("values", []))
                return True, f"维度 {dim}"
            else:
                return False, data.get("error", {}).get("message", f"HTTP {status}")[:50]
        elif "embedText" in methods:
            url = f"{base_url}/{name}:embedText?key={api_key}"
            status, data = api_request(url, data={"text": "Hello"})
            if status == 200:
                dim = len(data.get("embedding", {}).get("value", []))
                return True, f"维度 {dim}"
            else:
                return False, data.get("error", {}).get("message", f"HTTP {status}")[:50]
        else:
            return None, "无可测试接口"
    except Exception as e:
        return False, str(e)[:50]

# ─── 已知模型参数 & 错误翻译 ─────────────────────────────────

# 当 API 不返回 token 限额时，从此表中补全
KNOWN_MODEL_SPECS = {
    # DeepSeek
    "deepseek-chat":         {"input": 65_536,   "output": 8_192},
    "deepseek-reasoner":     {"input": 65_536,   "output": 8_192},
    "deepseek-coder":        {"input": 65_536,   "output": 8_192},
    "deepseek-v3":           {"input": 65_536,   "output": 8_192},
    "deepseek-r1":           {"input": 65_536,   "output": 8_192},
    # OpenAI
    "gpt-4o":                {"input": 128_000,  "output": 16_384},
    "gpt-4o-mini":           {"input": 128_000,  "output": 16_384},
    "gpt-4-turbo":           {"input": 128_000,  "output": 4_096},
    "gpt-4":                 {"input": 8_192,    "output": 8_192},
    "gpt-3.5-turbo":         {"input": 16_385,   "output": 4_096},
    "o1":                    {"input": 200_000,  "output": 100_000},
    "o1-mini":               {"input": 128_000,  "output": 65_536},
    "o1-preview":            {"input": 128_000,  "output": 32_768},
    "o3-mini":               {"input": 200_000,  "output": 100_000},
    # Qwen (通义千问)
    "qwen-turbo":            {"input": 131_072,  "output": 8_192},
    "qwen-plus":             {"input": 131_072,  "output": 8_192},
    "qwen-max":              {"input": 32_768,   "output": 8_192},
    "qwen-long":             {"input": 1_000_000,"output": 8_192},
    "qwen2.5-72b-instruct":  {"input": 131_072,  "output": 8_192},
    "qwen2.5-32b-instruct":  {"input": 131_072,  "output": 8_192},
    "qwen2.5-14b-instruct":  {"input": 131_072,  "output": 8_192},
    "qwen2.5-7b-instruct":   {"input": 131_072,  "output": 8_192},
    # Moonshot (Kimi)
    "moonshot-v1-8k":        {"input": 8_192,    "output": 4_096},
    "moonshot-v1-32k":       {"input": 32_768,   "output": 16_384},
    "moonshot-v1-128k":      {"input": 131_072,  "output": 65_536},
    # GLM (智谱)
    "glm-4":                 {"input": 128_000,  "output": 4_096},
    "glm-4-flash":           {"input": 128_000,  "output": 4_096},
    "glm-4-plus":            {"input": 128_000,  "output": 4_096},
    "glm-4-long":            {"input": 1_000_000,"output": 4_096},
    # Yi (零一万物)
    "yi-large":              {"input": 32_768,   "output": 4_096},
    "yi-medium":             {"input": 16_384,   "output": 4_096},
    "yi-spark":              {"input": 16_384,   "output": 4_096},
    # Claude (via OpenAI 兼容转发)
    "claude-3-opus":         {"input": 200_000,  "output": 4_096},
    "claude-3-sonnet":       {"input": 200_000,  "output": 4_096},
    "claude-3-haiku":        {"input": 200_000,  "output": 4_096},
    "claude-3.5-sonnet":     {"input": 200_000,  "output": 8_192},
    # Llama
    "meta-llama/Meta-Llama-3.1-405B-Instruct": {"input": 131_072, "output": 4_096},
    "meta-llama/Meta-Llama-3.1-70B-Instruct":  {"input": 131_072, "output": 4_096},
    "meta-llama/Meta-Llama-3.1-8B-Instruct":   {"input": 131_072, "output": 4_096},
    # Mistral
    "mistral-large-latest":  {"input": 128_000,  "output": 4_096},
    "mistral-small-latest":  {"input": 128_000,  "output": 4_096},
    # 腾讯云混元
    "hunyuan-pro":           {"input": 32_000,   "output": 4_096},
    "hunyuan-standard":      {"input": 32_000,   "output": 4_096},
    "hunyuan-lite":          {"input": 32_000,   "output": 4_096},
    "hunyuan-turbo":         {"input": 32_000,   "output": 4_096},
    "hunyuan-large":         {"input": 32_000,   "output": 4_096},
    "hunyuan-code":          {"input": 32_000,   "output": 4_096},
    "hunyuan-role":          {"input": 32_000,   "output": 4_096},
    "hunyuan-functioncall":  {"input": 32_000,   "output": 4_096},
    "hunyuan-vision":        {"input": 32_000,   "output": 4_096},
    # 讯飞星火
    "generalv3.5":           {"input": 128_000,  "output": 4_096},
    "generalv3":             {"input": 8_192,    "output": 4_096},
    "4.0Ultra":              {"input": 128_000,  "output": 8_192},
}


def fill_model_specs(model):
    """用已知参数补全 API 未返回的 token 限额"""
    model_id = model.get("_model_id") or model.get("name", "").replace("models/", "")
    if model.get("inputTokenLimit") and model.get("outputTokenLimit"):
        return  # 已有，无需补全

    # 精确匹配
    specs = KNOWN_MODEL_SPECS.get(model_id)
    if not specs:
        # 前缀模糊匹配 (如 deepseek-chat-v2 匹配 deepseek-chat)
        mid = model_id.lower()
        for key, val in KNOWN_MODEL_SPECS.items():
            if mid.startswith(key.lower()) or key.lower().startswith(mid):
                specs = val
                break
    if specs:
        if not model.get("inputTokenLimit"):
            model["inputTokenLimit"] = specs["input"]
        if not model.get("outputTokenLimit"):
            model["outputTokenLimit"] = specs["output"]


# OpenAI 兼容 API 常见错误码 → 中文提示
ERROR_TRANSLATIONS = {
    # HTTP 状态码级别
    400: "请求参数错误",
    401: "密钥无效或已过期",
    402: "账户余额不足，请充值",
    403: "没有权限访问此模型",
    404: "模型不存在或已下线",
    408: "请求超时",
    413: "请求内容过长 (超出 Token 上限)",
    422: "请求格式错误 (不可处理)",
    429: "请求太频繁，已触发速率限制",
    500: "服务商内部错误",
    502: "服务商网关错误",
    503: "服务暂时不可用 (可能在维护中)",
    504: "服务商网关超时",
    529: "服务过载，请稍后重试",
}

# 关键词 → 中文翻译 (匹配英文错误信息)
ERROR_KEYWORD_MAP = [
    ("insufficient balance",    "账户余额不足，请前往平台充值"),
    ("insufficient_balance",    "账户余额不足，请前往平台充值"),
    ("insufficient quota",      "配额不足，请前往平台充值或升级套餐"),
    ("quota exceeded",          "配额已耗尽"),
    ("rate limit",              "请求频率超限，请降低调用频率"),
    ("rate_limit_exceeded",     "请求频率超限，请降低调用频率"),
    ("invalid api key",         "密钥无效，请检查是否正确复制"),
    ("invalid_api_key",         "密钥无效，请检查是否正确复制"),
    ("invalid api-key",         "密钥无效，请检查是否正确复制"),
    ("authentication",          "认证失败，密钥无效或已过期"),
    ("unauthorized",            "未授权，密钥无效或已过期"),
    ("permission denied",       "没有权限，可能未开通此模型"),
    ("model not found",         "模型不存在或未开通"),
    ("model_not_found",         "模型不存在或未开通"),
    ("not found",               "资源不存在"),
    ("content filter",          "内容被安全过滤器拦截"),
    ("content_filter",          "内容被安全过滤器拦截"),
    ("context length exceeded",  "输入内容超出上下文长度限制"),
    ("context_length_exceeded",  "输入内容超出上下文长度限制"),
    ("server error",            "服务商内部错误"),
    ("internal error",          "服务商内部错误"),
    ("overloaded",              "服务过载，请稍后重试"),
    ("timeout",                 "请求超时"),
    ("billing",                 "计费问题，请检查账户状态"),
    ("payment required",        "需要付费，请先充值"),
    ("account deactivated",     "账户已停用"),
    ("deactivated",             "账户已停用"),
    ("expired",                 "密钥已过期，请重新生成"),
]


def translate_error(status_code, error_msg):
    """将 API 错误信息翻译成中文，返回 (中文摘要, 原始信息)"""
    msg_lower = (error_msg or "").lower()

    # 1. 关键词匹配
    for keyword, translation in ERROR_KEYWORD_MAP:
        if keyword in msg_lower:
            return translation

    # 2. 状态码匹配
    if status_code in ERROR_TRANSLATIONS:
        return ERROR_TRANSLATIONS[status_code]

    # 3. 无法翻译，保留原文但加中文状态码提示
    status_hint = ERROR_TRANSLATIONS.get(status_code, f"HTTP {status_code}")
    if error_msg:
        return f"{status_hint}: {error_msg[:60]}"
    return status_hint


def query_openai_balance(base_url, api_key, provider_name):
    """尝试查询 OpenAI 兼容服务商的账户余额/使用量信息"""
    balance_info = {}

    # 不同服务商有不同的余额查询端点
    balance_endpoints = [
        # SiliconFlow
        {"path": "/user/info",       "type": "siliconflow"},
        # DeepSeek
        {"path": "/user/balance",    "type": "deepseek"},
        # 通用 OpenAI dashboard
        {"path": "/dashboard/billing/credit_grants", "type": "openai_credit"},
        {"path": "/dashboard/billing/usage",         "type": "openai_usage"},
    ]

    headers = {"Authorization": f"Bearer {api_key}"}

    for ep in balance_endpoints:
        # 构建 URL: 移除 /v1 后缀再拼接
        url_base = base_url.rstrip("/")
        if url_base.endswith("/v1"):
            url_base = url_base[:-3]
        elif url_base.endswith("/v4"):
            url_base = url_base[:-3]

        url = f"{url_base}{ep['path']}"
        try:
            resp = _session.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                ep_type = ep["type"]

                if ep_type == "siliconflow":
                    # SiliconFlow: {"data": {"balance": "1.23", ...}}
                    bal = data.get("data", {}).get("balance")
                    if bal is not None:
                        balance_info["balance"] = float(bal)
                        balance_info["currency"] = "CNY"
                        balance_info["source"] = "SiliconFlow"
                        break

                elif ep_type == "deepseek":
                    # DeepSeek: {"balance_infos": [{"currency":"CNY","total_balance":"5.00",...}]}
                    infos = data.get("balance_infos", [])
                    if not infos and data.get("is_available") is not None:
                        balance_info["available"] = data.get("is_available", False)
                        balance_info["source"] = "DeepSeek"
                        break
                    for bi in infos:
                        balance_info["balance"] = float(bi.get("total_balance", 0))
                        balance_info["currency"] = bi.get("currency", "CNY")
                        balance_info["source"] = "DeepSeek"
                        break
                    if balance_info:
                        break

                elif ep_type == "openai_credit":
                    total = data.get("total_granted", 0)
                    used = data.get("total_used", 0)
                    balance_info["balance"] = total - used
                    balance_info["total_granted"] = total
                    balance_info["total_used"] = used
                    balance_info["currency"] = "USD"
                    balance_info["source"] = "OpenAI"
                    break

        except Exception:
            continue

    return balance_info


def print_account_diagnosis(provider, api_key, base_url, balance_info, models, test_results):
    """打印账户诊断信息，包括余额、密钥状态、常见问题提示"""
    print()
    divider("═")
    print(c(f"  💳 账户状态诊断 ({provider['icon']} {provider['name']})", C.BOLD))
    divider("═")
    print()

    # 余额信息
    if balance_info:
        bal = balance_info.get("balance")
        currency = balance_info.get("currency", "")
        currency_symbol = {"CNY": "¥", "USD": "$", "EUR": "€"}.get(currency, currency + " ")

        if bal is not None:
            if bal <= 0:
                check_item("账户余额", "fail", f"{currency_symbol}{bal:.2f}",
                           "余额为零！请前往平台充值后再测试")
            elif bal < 1:
                check_item("账户余额", "warn", f"{currency_symbol}{bal:.2f}",
                           "余额较低，建议及时充值")
            else:
                check_item("账户余额", "ok", f"{currency_symbol}{bal:.2f}")
        elif balance_info.get("available") is not None:
            if balance_info["available"]:
                check_item("账户状态", "ok", "可用")
            else:
                check_item("账户状态", "fail", "不可用", "请检查账户余额或状态")
    else:
        check_item("账户余额", "info", "无法查询 (该平台可能不支持余额查询接口)")

    # 模型测试统计
    if test_results:
        ok_count = sum(1 for s, _ in test_results.values() if s is True)
        fail_count = sum(1 for s, _ in test_results.values() if s is False)
        total = ok_count + fail_count

        if total > 0:
            if ok_count == 0:
                check_item("模型可用性", "fail", f"0/{total} 可用",
                           "所有模型均不可用，通常是余额不足或密钥权限问题")
            elif fail_count > ok_count:
                check_item("模型可用性", "warn", f"{ok_count}/{total} 可用",
                           "较多模型不可用，可能是套餐限制或模型未开通")
            else:
                check_item("模型可用性", "ok", f"{ok_count}/{total} 可用")

        # 分析常见错误原因
        error_reasons = {}
        for name, (ok, msg) in test_results.items():
            if ok is False and msg:
                reason = translate_error(0, msg)
                error_reasons.setdefault(reason, []).append(name)

        if error_reasons:
            print()
            print(c("  📋 错误原因分析:", C.BOLD))
            for reason, model_names in sorted(error_reasons.items(),
                                               key=lambda x: -len(x[1])):
                count = len(model_names)
                examples = ", ".join(n.replace("models/", "") for n in model_names[:3])
                if count > 3:
                    examples += f" 等 {count} 个模型"
                print(f"     {c('•', C.YELLOW)} {c(reason, C.WHITE)} → {c(examples, C.GRAY)}")

    print()


# ─── OpenAI 兼容 API ──────────────────────────────────────────

def openai_api_request(url, api_key, data=None):
    """发送 OpenAI 兼容格式的 API 请求"""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        if data is not None:
            headers["Content-Type"] = "application/json"
            resp = _session.post(url, json=data, headers=headers, timeout=30)
        else:
            resp = _session.get(url, headers=headers, timeout=30)
        return resp.status_code, resp.json() if resp.text else {}, resp.headers
    except requests.exceptions.ProxyError as e:
        raise ConnectionError(f"代理连接失败: {e}")
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"网络连接失败: {e}")
    except requests.exceptions.Timeout:
        raise ConnectionError("请求超时")
    except requests.exceptions.JSONDecodeError:
        return resp.status_code, {}, resp.headers
    except Exception as e:
        raise ConnectionError(f"请求异常: {e}")


def guess_openai_methods(model_id):
    """根据模型 ID 推断支持的接口类型"""
    mid = model_id.lower()
    if any(x in mid for x in ["embed", "bge-", "e5-", "gte-"]):
        return ["embedContent"]
    if any(x in mid for x in ["tts", "whisper", "audio", "speech"]):
        return []
    if any(x in mid for x in ["dall-e", "stable-diffusion", "flux", "imagen", "cogview"]):
        return ["predict"]
    if any(x in mid for x in ["rerank", "reranker"]):
        return []
    return ["generateContent"]


def openai_fetch_models(base_url, api_key, provider_name):
    """从 OpenAI 兼容 API 获取所有模型并规格化为统一格式"""
    status, data, _ = openai_api_request(f"{base_url}/models", api_key)
    if status != 200:
        err_msg = data.get("error", {}).get("message", f"HTTP {status}")
        if status in (401, 403):
            raise PermissionError(f"密钥无效或已过期: {err_msg}")
        elif status == 429:
            raise ConnectionError(f"请求频率超限: {err_msg}")
        else:
            raise RuntimeError(f"请求失败 ({status}): {err_msg}")

    raw_models = data.get("data", [])
    if not raw_models and data.get("models"):
        raw_models = data["models"]
    if not raw_models:
        return []

    models = []
    for m in raw_models:
        model_id = m.get("id", "")
        methods = guess_openai_methods(model_id)
        input_limit = (m.get("context_length") or m.get("max_context_length")
                       or m.get("context_window") or m.get("max_input_tokens"))
        output_limit = (m.get("max_output_tokens") or m.get("max_completion_tokens")
                        or m.get("max_tokens"))
        model = {
            "name": f"models/{model_id}",
            "displayName": model_id,
            "description": m.get("description") or f"Provider: {provider_name}",
            "supportedGenerationMethods": methods,
            "inputTokenLimit": input_limit,
            "outputTokenLimit": output_limit,
            "_provider_format": FORMAT_OPENAI,
            "_model_id": model_id,
            "_owned_by": m.get("owned_by", ""),
        }
        fill_model_specs(model)  # 补全 API 未返回的 token 限额
        models.append(model)
    return models


def openai_test_model(base_url, api_key, model):
    """测试 OpenAI 兼容 API 的单个模型，返回中文错误提示"""
    model_id = model.get("_model_id") or model.get("name", "").replace("models/", "")
    methods = model.get("supportedGenerationMethods", [])
    try:
        if "generateContent" in methods:
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 10,
            }
            status, data, _ = openai_api_request(
                f"{base_url}/chat/completions", api_key, data=payload)
            if status == 200:
                txt = (data.get("choices", [{}])[0]
                       .get("message", {}).get("content", "").strip()[:30])
                return True, txt or "(空响应)"
            else:
                err = data.get("error", {})
                raw_msg = err.get("message", "") if isinstance(err, dict) else str(err)
                cn_msg = translate_error(status, raw_msg)
                return False, cn_msg[:60]
        elif "embedContent" in methods:
            payload = {"model": model_id, "input": "Hello"}
            status, data, _ = openai_api_request(
                f"{base_url}/embeddings", api_key, data=payload)
            if status == 200:
                emb = data.get("data", [{}])
                dim = len(emb[0].get("embedding", [])) if emb else 0
                return True, f"维度 {dim}"
            else:
                err = data.get("error", {})
                raw_msg = err.get("message", "") if isinstance(err, dict) else str(err)
                cn_msg = translate_error(status, raw_msg)
                return False, cn_msg[:60]
        else:
            return None, "无可测试接口"
    except ConnectionError as e:
        return False, str(e)[:50]
    except Exception as e:
        return False, f"未知错误: {str(e)[:40]}"


# ─── 模型分类与分组 ──────────────────────────────────────────

def classify_model(model):
    """将模型分到一个系列中（同时支持 Gemini 和 OpenAI 格式）"""
    if model.get("_provider_format") == FORMAT_OPENAI:
        return classify_openai_model(model)
    # ── Gemini 分类 ──
    name = model.get("name", "").lower()
    if "gemini-3" in name:
        return "Gemini 3"
    if "gemini-2.5-pro" in name:
        return "Gemini 2.5 Pro"
    if "gemini-2.5-flash-lite" in name:
        return "Gemini 2.5 Flash-Lite"
    if "gemini-2.5-flash" in name:
        return "Gemini 2.5 Flash"
    if "gemini-2.0-flash-lite" in name:
        return "Gemini 2.0 Flash-Lite"
    if "gemini-2.0-flash" in name:
        return "Gemini 2.0 Flash"
    if "gemini-exp" in name or "gemini-flash" in name or "gemini-pro" in name:
        return "Gemini (其他)"
    if "gemma" in name:
        return "Gemma 开源模型"
    if "embedding" in name or "embed" in name:
        return "嵌入模型"
    if "imagen" in name:
        return "Imagen 图像生成"
    if "veo" in name:
        return "Veo 视频生成"
    if "deep-research" in name:
        return "Deep Research"
    if "robotics" in name:
        return "Gemini Robotics"
    return "其他"


def classify_openai_model(model):
    """将 OpenAI 兼容格式模型分到一个系列中"""
    mid = (model.get("_model_id") or model.get("name", "").replace("models/", "")).lower()
    # DeepSeek
    if "deepseek" in mid:
        if "coder" in mid:    return "DeepSeek Coder"
        if "reasoner" in mid or "-r1" in mid: return "DeepSeek Reasoner"
        return "DeepSeek"
    # Qwen
    if "qwen" in mid:
        if "vl" in mid:       return "Qwen 视觉"
        if "coder" in mid:    return "Qwen Coder"
        return "Qwen"
    # GPT
    if mid.startswith("gpt-") or mid.startswith("chatgpt"):
        if "4o" in mid:       return "GPT-4o"
        if "4" in mid:        return "GPT-4"
        if "3.5" in mid:      return "GPT-3.5"
        return "GPT"
    if mid.startswith(("o1", "o3", "o4")):
        return "OpenAI o-系列"
    # Claude
    if "claude" in mid:
        return "Claude"
    # Llama
    if "llama" in mid or "meta-llama" in mid:
        return "Llama"
    # Mistral
    if "mistral" in mid or "mixtral" in mid:
        return "Mistral"
    # GLM
    if "glm" in mid or "chatglm" in mid:
        return "GLM"
    # Moonshot
    if "moonshot" in mid or "kimi" in mid:
        return "Moonshot"
    # Hunyuan (腾讯)
    if "hunyuan" in mid:
        return "混元"
    # Spark (讯飞)
    if "spark" in mid or "generalv" in mid or "4.0ultra" in mid:
        return "星火"
    # Yi
    if mid.startswith("yi-"):
        return "Yi"
    # Gemini / Gemma via proxy
    if "gemini" in mid:
        return "Gemini"
    if "gemma" in mid:
        return "Gemma"
    # Embedding
    if any(x in mid for x in ["embed", "bge-", "e5-", "gte-"]):
        return "嵌入模型"
    # Image
    if any(x in mid for x in ["dall-e", "flux", "stable-diffusion", "sdxl", "cogview"]):
        return "图像生成"
    # Audio
    if any(x in mid for x in ["tts", "whisper", "speech"]):
        return "语音"
    # Rerank
    if "rerank" in mid:
        return "重排序"
    return "其他"


SERIES_ORDER = [
    "Gemini 3", "Gemini 2.5 Pro", "Gemini 2.5 Flash", "Gemini 2.5 Flash-Lite",
    "Gemini 2.0 Flash", "Gemini 2.0 Flash-Lite", "Gemini (其他)",
    "Gemma 开源模型", "嵌入模型", "Imagen 图像生成", "Veo 视频生成",
    "Deep Research", "Gemini Robotics", "其他"
]

SERIES_ICONS = {
    # Gemini
    "Gemini 3": "🚀", "Gemini 2.5 Pro": "💎", "Gemini 2.5 Flash": "⚡",
    "Gemini 2.5 Flash-Lite": "💡", "Gemini 2.0 Flash": "⚡", "Gemini 2.0 Flash-Lite": "💡",
    "Gemini (其他)": "🔮", "Gemma 开源模型": "🔓", "Imagen 图像生成": "🎨",
    "Veo 视频生成": "🎬", "Deep Research": "🔬", "Gemini Robotics": "🤖",
    # OpenAI-compatible
    "DeepSeek": "🔹", "DeepSeek Coder": "💻", "DeepSeek Reasoner": "🧠",
    "Qwen": "☁️", "Qwen 视觉": "👁️", "Qwen Coder": "💻",
    "GPT-4": "💎", "GPT-4o": "⚡", "GPT-3.5": "💡", "GPT": "🟢", "OpenAI o-系列": "🧠",
    "Claude": "🟤",
    "Llama": "🦙", "Mistral": "Ⓜ️", "GLM": "🟣", "Moonshot": "🌙",
    "Yi": "🌐", "混元": "🐧", "星火": "✨", "Gemini": "🔵", "Gemma": "🔓",
    "嵌入模型": "📐", "图像生成": "🎨", "语音": "🔊", "重排序": "🔀", "其他": "📦",
}

# ─── 配额限额分析 ─────────────────────────────────────────────

# Google Gemini API 免费层 (Free Tier) 参考限额
# 数据来源: https://ai.google.dev/pricing (2025)
# 付费层 (Pay-as-you-go) 限额通常高数百倍，且无每日请求限制
# RPM = 每分钟请求数, TPM = 每分钟 Token 数, RPD = 每日请求数
KNOWN_FREE_LIMITS = {
    "models/gemini-2.5-pro":               {"rpm": 5,   "tpm": 250_000,   "rpd": 25},
    "models/gemini-2.5-flash":             {"rpm": 10,  "tpm": 250_000,   "rpd": 500},
    "models/gemini-2.5-flash-lite":        {"rpm": 30,  "tpm": 1_000_000, "rpd": 3_000},
    "models/gemini-2.5-flash-preview-09-2025":       {"rpm": 10,  "tpm": 250_000,   "rpd": 500},
    "models/gemini-2.5-flash-lite-preview-09-2025":  {"rpm": 30,  "tpm": 1_000_000, "rpd": 3_000},
    "models/gemini-2.5-flash-image":       {"rpm": 10,  "tpm": 250_000,   "rpd": 500},
    "models/gemini-2.0-flash":             {"rpm": 15,  "tpm": 1_000_000, "rpd": 1_500},
    "models/gemini-2.0-flash-001":         {"rpm": 15,  "tpm": 1_000_000, "rpd": 1_500},
    "models/gemini-2.0-flash-exp-image-generation": {"rpm": 10, "tpm": 1_000_000, "rpd": 1_500},
    "models/gemini-2.0-flash-lite":        {"rpm": 30,  "tpm": 1_000_000, "rpd": 3_000},
    "models/gemini-2.0-flash-lite-001":    {"rpm": 30,  "tpm": 1_000_000, "rpd": 3_000},
    "models/gemini-exp-1206":              {"rpm": 10,  "tpm": 1_000_000, "rpd": 50},
    "models/gemini-3-pro-preview":         {"rpm": 5,   "tpm": 250_000,   "rpd": 25},
    "models/gemini-3-flash-preview":       {"rpm": 10,  "tpm": 250_000,   "rpd": 500},
    "models/gemini-3-pro-image-preview":   {"rpm": 5,   "tpm": 250_000,   "rpd": 25},
    "models/nano-banana-pro-preview":      {"rpm": 5,   "tpm": 250_000,   "rpd": 25},
    "models/gemini-flash-latest":          {"rpm": 10,  "tpm": 250_000,   "rpd": 500},
    "models/gemini-flash-lite-latest":     {"rpm": 30,  "tpm": 1_000_000, "rpd": 3_000},
    "models/gemini-pro-latest":            {"rpm": 5,   "tpm": 250_000,   "rpd": 25},
    "models/gemma-3-1b-it":               {"rpm": 30,  "tpm": 1_000_000, "rpd": 14_400},
    "models/gemma-3-4b-it":               {"rpm": 30,  "tpm": 1_000_000, "rpd": 14_400},
    "models/gemma-3-12b-it":              {"rpm": 30,  "tpm": 1_000_000, "rpd": 14_400},
    "models/gemma-3-27b-it":              {"rpm": 30,  "tpm": 1_000_000, "rpd": 14_400},
    "models/gemma-3n-e4b-it":             {"rpm": 30,  "tpm": 1_000_000, "rpd": 14_400},
    "models/gemma-3n-e2b-it":             {"rpm": 30,  "tpm": 1_000_000, "rpd": 14_400},
    "models/gemini-robotics-er-1.5-preview": {"rpm": 5, "tpm": 250_000, "rpd": 25},
}

def parse_rate_limit_headers(headers):
    """从 HTTP 响应头中解析速率限制信息"""
    info = {}
    h = {k.lower(): v for k, v in headers.items()}

    header_map = [
        ("x-ratelimit-limit-requests", "rpm"),
        ("x-ratelimit-remaining-requests", "rpm_remaining"),
        ("x-ratelimit-limit-tokens", "tpm"),
        ("x-ratelimit-remaining-tokens", "tpm_remaining"),
        ("x-ratelimit-limit-requests-per-day", "rpd"),
        ("x-ratelimit-remaining-requests-per-day", "rpd_remaining"),
        ("x-ratelimit-limit", "limit"),
        ("x-ratelimit-remaining", "remaining"),
        ("retry-after", "retry_after"),
    ]
    for key_pattern, field in header_map:
        if key_pattern in h:
            try:
                info[field] = int(h[key_pattern])
            except (ValueError, TypeError):
                info[field] = h[key_pattern]

    # 收集所有限额相关的原始头
    info["_raw"] = {k: v for k, v in headers.items()
                    if any(x in k.lower() for x in ["ratelimit", "rate-limit", "quota", "retry"])}
    return info


def fetch_all_quotas(base_url, api_key, models, test_results, api_format=FORMAT_GEMINI):
    """获取所有可用文本生成模型的配额信息
    对每个可用模型发送一次轻量请求以捕获响应头中的速率限制信息，
    无法获取时回退至已知的免费层参考值。"""

    # 只分析可用的文本生成模型
    gen_models = [m for m in models
                  if test_results.get(m["name"], (None,))[0] is True
                  and "generateContent" in m.get("supportedGenerationMethods", [])]

    if not gen_models:
        return {}

    print()
    print(c("  ⏳ 正在检测各模型配额限制...", C.CYAN))
    print()

    quota_data = {}

    for i, model in enumerate(gen_models, 1):
        name = model["name"]
        display = model.get("displayName", name.replace("models/", ""))
        progress_bar(i, len(gen_models), label=display)

        entry = {
            "displayName": display,
            "name": name,
            "inputTokenLimit": model.get("inputTokenLimit"),
            "outputTokenLimit": model.get("outputTokenLimit"),
            "rpm": None,
            "tpm": None,
            "rpd": None,
            "source": "未知",
            "headers_raw": {},
        }

        # 第 1 步: 发送轻量请求，捕获响应头
        try:
            if api_format == FORMAT_GEMINI:
                url = f"{base_url}/{name}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": "Hi"}]}],
                           "generationConfig": {"maxOutputTokens": 1}}
                resp = _session.post(url, json=payload, timeout=30)
            else:
                model_id = model.get("_model_id") or name.replace("models/", "")
                payload = {"model": model_id,
                           "messages": [{"role": "user", "content": "Hi"}],
                           "max_tokens": 1}
                resp = _session.post(f"{base_url}/chat/completions", json=payload,
                                     headers={"Authorization": f"Bearer {api_key}",
                                              "Content-Type": "application/json"},
                                     timeout=30)
            header_info = parse_rate_limit_headers(dict(resp.headers))
            entry["headers_raw"] = header_info.get("_raw", {})

            if "rpm" in header_info and isinstance(header_info["rpm"], int):
                entry["rpm"] = header_info["rpm"]
                entry["source"] = "API 响应头"
            if "tpm" in header_info and isinstance(header_info["tpm"], int):
                entry["tpm"] = header_info["tpm"]
            if "rpd" in header_info and isinstance(header_info["rpd"], int):
                entry["rpd"] = header_info["rpd"]
        except Exception:
            pass

        # 第 2 步: 回退至已知参考限额
        if entry["rpm"] is None:
            if name in KNOWN_FREE_LIMITS:
                known = KNOWN_FREE_LIMITS[name]
                entry["rpm"] = known.get("rpm")
                entry["tpm"] = known.get("tpm")
                entry["rpd"] = known.get("rpd")
                entry["source"] = "参考值 (Google 官方)"
            else:
                # 尝试前缀匹配
                for known_name, known_limits in KNOWN_FREE_LIMITS.items():
                    if name.startswith(known_name) or known_name.startswith(name):
                        entry["rpm"] = known_limits.get("rpm")
                        entry["tpm"] = known_limits.get("tpm")
                        entry["rpd"] = known_limits.get("rpd")
                        entry["source"] = "参考值 (近似匹配)"
                        break

        # 第 3 步: 计算每日最大输出吞吐量
        output_limit = entry.get("outputTokenLimit") or 0
        rpd = entry.get("rpd") or 0
        tpm = entry.get("tpm") or 0

        daily_by_rpd = rpd * output_limit if rpd else None
        daily_by_tpm = tpm * 1440 if tpm else None  # 1440 分钟/天

        if daily_by_rpd and daily_by_tpm:
            entry["daily_max_output"] = min(daily_by_rpd, daily_by_tpm)
        elif daily_by_rpd:
            entry["daily_max_output"] = daily_by_rpd
        elif daily_by_tpm:
            entry["daily_max_output"] = daily_by_tpm
        else:
            entry["daily_max_output"] = None

        quota_data[name] = entry

        if i % 3 == 0:
            time.sleep(0.2)

    clear_line()
    print(c(f"  ✅ 已检测 {len(quota_data)} 个可用模型的配额", C.GREEN + C.BOLD))
    return quota_data


def print_quota_report(quota_data):
    """打印配额对比报告表格，按每日最大吞吐量降序排列"""
    if not quota_data:
        return

    sorted_models = sorted(quota_data.values(),
                           key=lambda x: x.get("daily_max_output") or 0,
                           reverse=True)

    print()
    print(c("  ╔═══════════════════════════════════════════════════════════════════════════╗", C.MAGENTA))
    print(c("  ║", C.MAGENTA) + c("                      📊 模型配额与吞吐量分析                            ", C.BOLD) + c("║", C.MAGENTA))
    print(c("  ║", C.MAGENTA) + c("                    排名按每日最大输出吞吐量排序                          ", C.GRAY) + c("║", C.MAGENTA))
    print(c("  ╚═══════════════════════════════════════════════════════════════════════════╝", C.MAGENTA))
    print()

    # 表头
    hdr = f"  {'排名':>4s}  {'模型名称':<26s}  {'RPM':>5s}  {'TPM':>8s}  {'RPD':>6s}  {'输出/请求':>8s}  {'每日最大吞吐':>12s}"
    print(c(hdr, C.BOLD))
    divider("─", 82)

    medals = ["🥇", "🥈", "🥉"]

    for idx, entry in enumerate(sorted_models):
        rank = idx + 1
        medal = medals[idx] if idx < 3 else "  "

        display = entry["displayName"]
        if len(display) > 24:
            display = display[:22] + ".."
        rpm_s = str(entry.get("rpm")) if entry.get("rpm") is not None else "?"
        tpm_s = fmt_tokens(entry.get("tpm")) if entry.get("tpm") else "?"
        rpd_s = str(entry.get("rpd")) if entry.get("rpd") is not None else "?"
        out_s = fmt_tokens(entry.get("outputTokenLimit"))
        daily_s = fmt_tokens(entry.get("daily_max_output")) if entry.get("daily_max_output") else "?"

        if rank <= 3:
            nc, dc = C.GREEN + C.BOLD, C.GREEN + C.BOLD
        elif rank <= 6:
            nc, dc = C.WHITE, C.WHITE
        else:
            nc, dc = C.GRAY, C.GRAY

        src_mark = c(" ⚡", C.CYAN) if "API" in entry.get("source", "") else ""

        print(f"  {medal}{rank:>2d}  {c(f'{display:<26s}', nc)}  "
              f"{c(f'{rpm_s:>5s}', C.WHITE)}  {c(f'{tpm_s:>8s}', C.WHITE)}  "
              f"{c(f'{rpd_s:>6s}', C.WHITE)}  {c(f'{out_s:>8s}', C.WHITE)}  "
              f"{c(f'{daily_s:>12s}', dc)}{src_mark}")

    print()
    divider("─", 82)

    # 数据来源说明
    sources = set(e.get("source", "") for e in quota_data.values())
    print(f"  {c('📌 数据来源:', C.DIM)} ", end="")
    if "API 响应头" in sources:
        print(c("⚡ = API 实时响应头", C.CYAN), end="  ")
    if any("参考" in s for s in sources):
        print(c("其余 = Google 官方文档参考值 (免费层)", C.GRAY), end="")
    print()
    print(f"  {c('💡 每日最大吞吐 = min(RPD × 单次最大输出, TPM × 1440 分钟)', C.DIM)}")
    print(f"  {c('   付费账户 (Pay-as-you-go) 限额通常高数百倍, 且无每日请求限制', C.DIM)}")
    print()

    # 前三推荐
    if sorted_models:
        print(f"  {c('🏆 大量 Token 处理推荐:', C.BOLD + C.GREEN)}")
        for i, m in enumerate(sorted_models[:3]):
            d = m.get("daily_max_output")
            if d:
                prefix = ["🥇", "🥈", "🥉"][i]
                print(f"     {prefix} {c(m['displayName'], C.GREEN + C.BOLD)} — "
                      f"每日最多 ~{c(fmt_tokens(d), C.GREEN + C.BOLD)} tokens 输出")
        print()


def prompt_token_calculator(quota_data):
    """交互式 Token 需求计算器：用户输入需处理的 Token 总量，
    自动估算各模型所需时间并排名。"""
    if not quota_data:
        return

    try:
        raw = input(c("  📝 输入你需要的总 Token 数 (例: 10000000 或 10M，直接回车跳过): ",
                      C.BOLD + C.WHITE)).strip()
    except (EOFError, KeyboardInterrupt):
        return

    if not raw:
        return

    # 解析输入
    raw = raw.upper().replace(",", "").replace(" ", "").replace("_", "")
    try:
        if raw.endswith("B"):
            total_tokens = int(float(raw[:-1]) * 1_000_000_000)
        elif raw.endswith("M"):
            total_tokens = int(float(raw[:-1]) * 1_000_000)
        elif raw.endswith("K"):
            total_tokens = int(float(raw[:-1]) * 1_000)
        else:
            total_tokens = int(float(raw))
    except ValueError:
        print(c("  ⚠️  无法解析输入，跳过计算。", C.YELLOW))
        return

    if total_tokens <= 0:
        return

    sorted_models = sorted(quota_data.values(),
                           key=lambda x: x.get("daily_max_output") or 0,
                           reverse=True)

    print()
    print(c(f"  ╔═══════════════════════════════════════════════════════════════════════════╗", C.CYAN))
    print(c(f"  ║", C.CYAN) + c(f"          🧮 Token 需求预估: 共需 {fmt_tokens(total_tokens)} tokens", C.BOLD)
          + " " * max(0, 32 - len(fmt_tokens(total_tokens))) + c("║", C.CYAN))
    print(c(f"  ╚═══════════════════════════════════════════════════════════════════════════╝", C.CYAN))
    print()

    hdr = f"  {'模型名称':<28s}  {'每日吞吐':>10s}  {'预计耗时':>16s}  {'所需请求数':>10s}"
    print(c(hdr, C.BOLD))
    divider("─", 72)

    for entry in sorted_models:
        daily = entry.get("daily_max_output")
        if not daily or daily == 0:
            continue

        display = entry["displayName"]
        if len(display) > 26:
            display = display[:24] + ".."

        days = total_tokens / daily
        output_per_req = entry.get("outputTokenLimit") or 1
        num_requests = (total_tokens + output_per_req - 1) // output_per_req

        # 格式化时间
        if days < 1:
            hours = days * 24
            if hours < 1:
                minutes = hours * 60
                time_str = f"~{minutes:.0f} 分钟"
            else:
                time_str = f"~{hours:.1f} 小时"
        elif days < 7:
            time_str = f"~{days:.1f} 天"
        else:
            time_str = f"~{days:.0f} 天 ({days / 7:.1f} 周)"

        # 颜色
        if days < 1:
            tc = C.GREEN + C.BOLD
        elif days < 3:
            tc = C.WHITE
        elif days < 7:
            tc = C.YELLOW
        else:
            tc = C.RED

        print(f"  {c(f'{display:<28s}', C.WHITE)}  {c(fmt_tokens(daily) + '/天', C.GRAY):>16s}"
              f"  {c(f'{time_str:>16s}', tc)}  {c(f'{num_requests:>10,d}', C.GRAY)}")

    print()

# ─── 可视化输出 ───────────────────────────────────────────────

def print_model_row(model, test_result=None, idx=0):
    """打印一行模型信息"""
    display = model.get("displayName", "")
    model_id = model.get("name", "").replace("models/", "")
    methods = model.get("supportedGenerationMethods", [])
    inp = fmt_tokens(model.get("inputTokenLimit"))
    out = fmt_tokens(model.get("outputTokenLimit"))

    # 可用性标记
    if test_result is not None:
        ok, msg = test_result
        if ok is True:
            status = c(" ✓ ", C.GREEN + C.BOLD)
        elif ok is False:
            status = c(" ✗ ", C.RED + C.BOLD)
        else:
            status = c(" - ", C.GRAY)
    else:
        status = c("   ", C.GRAY)

    # 能力标签（简短）
    caps = []
    if "generateContent" in methods:
        caps.append(c("生成", C.GREEN))
    if "embedContent" in methods or "embedText" in methods:
        caps.append(c("嵌入", C.YELLOW))
    if "bidiGenerateContent" in methods:
        caps.append(c("实时", C.MAGENTA))
    if "predict" in methods or "predictLongRunning" in methods:
        caps.append(c("预测", C.CYAN))
    caps_str = c("|", C.GRAY).join(caps) if caps else c("--", C.GRAY)

    # 主行
    idx_str = c(f"{idx:>2}", C.GRAY)
    name_str = c(display if display else model_id, C.WHITE + C.BOLD)
    id_str = c(model_id, C.GRAY)

    print(f"  {status} {idx_str}  {name_str}")
    print(f"         {id_str}")
    print(f"         {caps_str}   {c('输入', C.DIM)} {c(inp, C.WHITE)}  {c('输出', C.DIM)} {c(out, C.WHITE)}", end="")

    # 测试详情
    if test_result is not None:
        ok, msg = test_result
        if ok is True:
            print(f"  {c(msg, C.GREEN)}", end="")
        elif ok is False:
            print(f"  {c(msg[:45], C.RED)}", end="")
    print()
    print()

def print_summary(models, test_results):
    """打印美观的统计摘要"""
    total = len(models)
    tested = {k: v for k, v in test_results.items()}
    ok_count = sum(1 for s, _ in tested.values() if s is True)
    fail_count = sum(1 for s, _ in tested.values() if s is False)
    skip_count = sum(1 for s, _ in tested.values() if s is None)

    gen_count = sum(1 for m in models if "generateContent" in m.get("supportedGenerationMethods", []))
    emb_count = sum(1 for m in models if "embedContent" in m.get("supportedGenerationMethods", [])
                    or "embedText" in m.get("supportedGenerationMethods", []))
    img_count = sum(1 for m in models if "predict" in m.get("supportedGenerationMethods", [])
                    or "predictLongRunning" in m.get("supportedGenerationMethods", []))

    print()
    print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.BLUE))
    print(c("  ║", C.BLUE) + c("                       📊 测试结果摘要                       ", C.BOLD) + c("║", C.BLUE))
    print(c("  ╠═══════════════════════════════════════════════════════════════╣", C.BLUE))

    # 可用性统计 - 可视化条
    bar_width = 40
    ok_w = int(bar_width * ok_count / total) if total else 0
    fail_w = int(bar_width * fail_count / total) if total else 0
    skip_w = bar_width - ok_w - fail_w

    bar = c("█" * ok_w, C.GREEN) + c("█" * fail_w, C.RED) + c("█" * skip_w, C.GRAY)
    print(c("  ║", C.BLUE) + f"  {bar}               " + c("║", C.BLUE))
    print(c("  ║", C.BLUE) + f"  {c('■', C.GREEN)} 可用 {c(str(ok_count), C.GREEN + C.BOLD):>12s}   {c('■', C.RED)} 不可用 {c(str(fail_count), C.RED + C.BOLD):>10s}   {c('■', C.GRAY)} 跳过 {c(str(skip_count), C.GRAY):>8s}     " + c("║", C.BLUE))
    print(c("  ╠═══════════════════════════════════════════════════════════════╣", C.BLUE))

    # 模型类型统计
    print(c("  ║", C.BLUE) + f"  {c('模型总数', C.DIM)}         {c(str(total), C.WHITE + C.BOLD):>10s}                                " + c("║", C.BLUE))
    print(c("  ║", C.BLUE) + f"  {c('文本生成模型', C.GREEN)}     {c(str(gen_count), C.GREEN + C.BOLD):>10s}                                " + c("║", C.BLUE))
    print(c("  ║", C.BLUE) + f"  {c('嵌入模型', C.YELLOW)}         {c(str(emb_count), C.YELLOW + C.BOLD):>10s}                                " + c("║", C.BLUE))
    print(c("  ║", C.BLUE) + f"  {c('图像/视频模型', C.CYAN)}   {c(str(img_count), C.CYAN + C.BOLD):>12s}                                " + c("║", C.BLUE))

    print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.BLUE))
    print()

def export_json(api_key, base_url, models, test_results, quota_data=None):
    """导出结果到 JSON (包含配额分析)"""
    export_data = {
        "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "***",
        "base_url": base_url,
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_models": len(models),
        "available": sum(1 for s, _ in test_results.values() if s is True),
        "unavailable": sum(1 for s, _ in test_results.values() if s is False),
        "models": []
    }
    for model in models:
        info = {
            "name": model.get("name"),
            "displayName": model.get("displayName"),
            "description": model.get("description"),
            "supportedMethods": model.get("supportedGenerationMethods", []),
            "inputTokenLimit": model.get("inputTokenLimit"),
            "outputTokenLimit": model.get("outputTokenLimit"),
        }
        if model.get("name") in test_results:
            s, msg = test_results[model["name"]]
            info["testResult"] = {"available": s, "message": msg}
        # 附加配额信息
        if quota_data and model.get("name") in quota_data:
            q = quota_data[model["name"]]
            info["quota"] = {
                "rpm": q.get("rpm"),
                "tpm": q.get("tpm"),
                "rpd": q.get("rpd"),
                "dailyMaxOutput": q.get("daily_max_output"),
                "source": q.get("source"),
            }
        export_data["models"].append(info)

    # 配额排行摘要
    if quota_data:
        ranked = sorted(quota_data.values(),
                        key=lambda x: x.get("daily_max_output") or 0,
                        reverse=True)
        export_data["quotaRanking"] = [
            {
                "rank": i + 1,
                "name": e["name"],
                "displayName": e["displayName"],
                "rpm": e.get("rpm"),
                "tpm": e.get("tpm"),
                "rpd": e.get("rpd"),
                "outputTokenLimit": e.get("outputTokenLimit"),
                "dailyMaxOutput": e.get("daily_max_output"),
                "source": e.get("source"),
            }
            for i, e in enumerate(ranked)
        ]

    filename = f"api_test_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    return filename

# ─── Web 代理服务器 ──────────────────────────────────────────

def start_web_server(port=8765):
    """启动本地 Web 代理服务器，为 HTML 版提供 CORS 代理功能。
    浏览器页面通过 /api/proxy?url=<目标URL> 发起请求，
    服务器转发至实际 API 并返回结果，绕过浏览器 CORS 限制。"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs, unquote
    import webbrowser
    import threading

    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "index.html")

    if not os.path.exists(html_path):
        print(c("  ❌ 未找到 index.html，请确认与 gemini_test.py 在同一目录", C.RED))
        safe_exit(1)

    # 创建独立的 requests 会话（自动继承系统代理）
    web_session = requests.Session()
    web_session.verify = False

    class ProxyHandler(BaseHTTPRequestHandler):

        def do_OPTIONS(self):
            """处理 CORS 预检请求"""
            self.send_response(200)
            self._cors_headers()
            self.end_headers()

        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self._serve_html()
            elif self.path.startswith("/api/proxy"):
                self._handle_proxy("GET")
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path.startswith("/api/proxy"):
                self._handle_proxy("POST")
            else:
                self.send_error(404)

        def _cors_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Expose-Headers", "*")

        def _serve_html(self):
            try:
                with open(html_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, str(e))

        def _handle_proxy(self, method):
            """代理转发请求到目标 API"""
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            target_url = params.get("url", [None])[0]

            if not target_url:
                self.send_response(400)
                self._cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"error": {"message": "缺少 url 参数"}}).encode())
                return

            target_url = unquote(target_url)

            # 读取请求体
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            # 转发请求头（过滤浏览器专用头）
            skip_headers = {
                "host", "connection", "accept-encoding", "origin",
                "referer", "sec-fetch-mode", "sec-fetch-site",
                "sec-fetch-dest", "sec-ch-ua", "sec-ch-ua-mobile",
                "sec-ch-ua-platform",
            }
            forward_headers = {}
            for key in self.headers:
                if key.lower() not in skip_headers:
                    forward_headers[key] = self.headers[key]

            # 转发请求
            try:
                if method == "POST":
                    resp = web_session.post(
                        target_url, headers=forward_headers,
                        data=body, timeout=30)
                else:
                    resp = web_session.get(
                        target_url, headers=forward_headers, timeout=30)

                # 返回响应
                self.send_response(resp.status_code)
                self._cors_headers()

                # 转发响应头（保留 rate-limit 等关键头）
                skip_resp = {"content-encoding", "transfer-encoding",
                             "connection", "content-length"}
                for key, value in resp.headers.items():
                    if key.lower() not in skip_resp:
                        self.send_header(key, value)

                resp_body = resp.content
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)

            except requests.exceptions.ProxyError as e:
                self._send_proxy_error(f"代理连接失败: {e}")
            except requests.exceptions.ConnectionError as e:
                self._send_proxy_error(f"无法连接目标服务器: {e}")
            except requests.exceptions.Timeout:
                self._send_proxy_error("请求超时 (30s)")
            except Exception as e:
                self._send_proxy_error(f"代理请求异常: {e}")

        def _send_proxy_error(self, msg):
            self.send_response(502)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            err_body = json.dumps(
                {"error": {"message": msg}}).encode("utf-8")
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)

        def log_message(self, format, *args):
            """简化日志输出"""
            method = args[0] if args else ""
            if "/api/proxy" in str(method):
                # 只在代理请求时输出简短日志
                status = args[-1] if len(args) > 1 else ""
                sys.stdout.write(f"\r  📡 {method} → {status}    \n")
                sys.stdout.flush()

    # 尝试启动服务器
    for p in (port, port + 1, port + 2):
        try:
            server = HTTPServer(("127.0.0.1", p), ProxyHandler)
            port = p
            break
        except OSError:
            continue
    else:
        print(c(f"  ❌ 端口 {port}-{port+2} 均被占用，无法启动服务", C.RED))
        safe_exit(1)

    url = f"http://localhost:{port}"
    print()
    print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.GREEN))
    print(c("  ║", C.GREEN) + c("            🌐 Web 代理服务已启动!                              ", C.BOLD) + c("║", C.GREEN))
    print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.GREEN))
    print()
    print(c(f"  🔗 访问地址: {url}", C.CYAN + C.BOLD))
    print(c(f"  📡 代理模式: 所有 API 请求将通过本地服务器中转，绕过 CORS 限制", C.GRAY))
    print(c(f"  🛑 按 Ctrl+C 停止服务", C.GRAY))
    print()
    divider()

    # 自动打开浏览器
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(c("\n\n  ⚠️  Web 服务已停止。", C.YELLOW))
        server.server_close()
        safe_exit(0)


# ─── 主流程 ──────────────────────────────────────────────────

def main():
    # 检查 --web 启动模式
    if "--web" in sys.argv:
        print_header()
        start_web_server()
        return

    print_header()

    # ① 获取 API 密钥
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        print(c(f"  🔑 API 密钥: {api_key[:8]}...{api_key[-4:]}", C.WHITE))
    else:
        api_key = input(c("  🔑 请输入 API 密钥: ", C.BOLD + C.WHITE)).strip()

    if not api_key:
        print(c("\n  ❌ 未输入密钥，退出。\n", C.RED))
        safe_exit(1)

    custom_url = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else None

    # ② 提前配置代理（探测服务商时需要）
    proxy_port, proxy_name = detect_proxy()
    if proxy_port:
        px = f"http://127.0.0.1:{proxy_port}"
        _session.proxies = {"http": px, "https": px}
        _session.trust_env = False
    else:
        sys_proxies = urllib.request.getproxies()
        if sys_proxies:
            _session.trust_env = True

    # ③ 自动识别 API 服务商
    provider = auto_detect_provider(api_key, custom_url)
    api_format = provider["format"]
    base_url = provider["base_url"]

    # ④ 网络诊断
    if api_format == FORMAT_GEMINI:
        base_url = run_network_diagnostic(base_url)
    else:
        run_openai_diagnostic(provider, proxy_port, proxy_name)

    # ⑤ 获取模型列表
    print(c("  ⏳ 正在获取模型列表...", C.CYAN))

    try:
        t0 = time.time()
        if api_format == FORMAT_GEMINI:
            models = fetch_models(base_url, api_key)
        else:
            models = openai_fetch_models(base_url, api_key, provider["name"])
        t_fetch = time.time() - t0
    except PermissionError as e:
        print(c(f"\n  ❌ {e}", C.RED))
        print(c("     请确认密钥是否正确", C.YELLOW))
        safe_exit(1)
    except ConnectionError as e:
        print(c(f"\n  ❌ {e}", C.RED))
        print(c("     网络连接出现问题，请参考上方诊断结果排查", C.YELLOW))
        safe_exit(1)
    except Exception as e:
        print(c(f"\n  ❌ {e}", C.RED))
        safe_exit(1)

    if not models:
        print(c("  ⚠️  密钥有效，但未找到任何可用模型。", C.YELLOW))
        safe_exit(0)

    print(c(f"  ✅ 发现 {len(models)} 个模型 ({t_fetch:.1f}s)", C.GREEN + C.BOLD))

    # ⑥ 逐一测试模型可用性（带进度条）
    print()
    print(c("  ⏳ 正在逐一测试模型可用性...", C.CYAN))
    print()

    test_results = {}
    t0 = time.time()
    for i, model in enumerate(models, 1):
        model_name = model.get("name", "")
        display = model.get("displayName", model_name.replace("models/", ""))
        progress_bar(i, len(models), label=display)
        if api_format == FORMAT_GEMINI:
            result = test_model(base_url, api_key, model)
        else:
            result = openai_test_model(base_url, api_key, model)
        test_results[model_name] = result
        if i % 5 == 0:
            time.sleep(0.2)
    clear_line()
    t_test = time.time() - t0
    print(c(f"  ✅ 全部测试完成 ({t_test:.1f}s)", C.GREEN + C.BOLD))

    # ⑦ 按系列分组展示
    print()
    divider("═")
    print(c(f"  📋 模型详细列表 ({provider['icon']} {provider['name']})", C.BOLD))
    divider("═")

    # 分组
    groups = {}
    for model in models:
        series = classify_model(model)
        groups.setdefault(series, []).append(model)

    # 确定系列顺序
    if api_format == FORMAT_GEMINI:
        ordered_series = [s for s in SERIES_ORDER if s in groups]
        for s in groups:
            if s not in ordered_series:
                ordered_series.append(s)
    else:
        ordered_series = sorted(groups.keys(),
                                key=lambda s: (-len(groups[s]), s))

    idx = 0
    for series in ordered_series:
        group = groups[series]
        icon = SERIES_ICONS.get(series, "📦")

        ok_in_group = sum(1 for m in group
                         if test_results.get(m["name"], (None,))[0] is True)
        total_in_group = len(group)

        print()
        print(f"  {icon} {c(series, C.BOLD + C.WHITE)} {c(f'({ok_in_group}/{total_in_group} 可用)', C.GRAY)}")
        divider("─", 50)
        print()

        for model in group:
            idx += 1
            result = test_results.get(model.get("name"))
            print_model_row(model, result, idx)

    # ⑧ 统计摘要
    print_summary(models, test_results)

    # ⑨ 账户状态诊断 (OpenAI 兼容服务商)
    balance_info = {}
    if api_format == FORMAT_OPENAI:
        print(c("  ⏳ 正在查询账户余额...", C.CYAN))
        balance_info = query_openai_balance(base_url, api_key, provider["name"])
        print_account_diagnosis(provider, api_key, base_url, balance_info,
                                models, test_results)

    # ⑩ 配额限额分析
    quota_data = fetch_all_quotas(base_url, api_key, models, test_results, api_format)
    if quota_data:
        print_quota_report(quota_data)
        prompt_token_calculator(quota_data)

    # ⑪ 自动导出
    filename = export_json(api_key, base_url, models, test_results, quota_data)
    print(c(f"  💾 测试结果已自动导出到: {filename}", C.GREEN))
    print()

    # ⑫ 完成
    print(c("  ✅ 全部测试流程完成！", C.GREEN + C.BOLD))
    safe_exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\n\n  ⚠️  用户中断操作。", C.YELLOW))
        safe_exit(0)
    except SystemExit:
        raise  # 允许 safe_exit() 正常退出
    except Exception as e:
        print(c(f"\n  ❌ 程序发生意外错误: {e}", C.RED))
        import traceback
        traceback.print_exc()
        safe_exit(1)
