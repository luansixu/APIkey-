"""
Gemini API 密钥测试工具 v2.0
直接在终端运行: py gemini_test.py [API_KEY]
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

def print_header():
    print()
    print(c("  ╔═══════════════════════════════════════════════════════════════╗", C.BLUE))
    print(c("  ║", C.BLUE) + c("         Gemini API 密钥测试工具  ", C.BOLD) + c("v2.0", C.CYAN) + c("                     ", C.BOLD) + c("║", C.BLUE))
    print(c("  ║", C.BLUE) + c("         一键测试密钥 · 列出模型 · 验证可用性                ", C.GRAY) + c("║", C.BLUE))
    print(c("  ╚═══════════════════════════════════════════════════════════════╝", C.BLUE))
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
            sys.exit(0)

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

# ─── 模型分类与分组 ──────────────────────────────────────────

def classify_model(model):
    """将模型分到一个系列中"""
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

SERIES_ORDER = [
    "Gemini 3", "Gemini 2.5 Pro", "Gemini 2.5 Flash", "Gemini 2.5 Flash-Lite",
    "Gemini 2.0 Flash", "Gemini 2.0 Flash-Lite", "Gemini (其他)",
    "Gemma 开源模型", "嵌入模型", "Imagen 图像生成", "Veo 视频生成",
    "Deep Research", "Gemini Robotics", "其他"
]

SERIES_ICONS = {
    "Gemini 3": "🚀", "Gemini 2.5 Pro": "💎", "Gemini 2.5 Flash": "⚡",
    "Gemini 2.5 Flash-Lite": "💡", "Gemini 2.0 Flash": "⚡", "Gemini 2.0 Flash-Lite": "💡",
    "Gemini (其他)": "🔮", "Gemma 开源模型": "🔓", "嵌入模型": "📐",
    "Imagen 图像生成": "🎨", "Veo 视频生成": "🎬", "Deep Research": "🔬",
    "Gemini Robotics": "🤖", "其他": "📦"
}

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

def export_json(api_key, base_url, models, test_results):
    """导出结果到 JSON"""
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
        export_data["models"].append(info)

    filename = f"gemini_test_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    return filename

# ─── 主流程 ──────────────────────────────────────────────────

def main():
    print_header()

    # ① 获取 API 密钥（唯一必须交互的步骤）
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        print(c(f"  🔑 API 密钥: {api_key[:8]}...{api_key[-4:]}", C.WHITE))
    else:
        api_key = input(c("  🔑 请输入 API 密钥: ", C.BOLD + C.WHITE)).strip()

    if not api_key:
        print(c("\n  ❌ 未输入密钥，退出。\n", C.RED))
        sys.exit(1)

    # ② 全自动网络诊断（检测代理、连通性、出口 IP、地区）
    base_url = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else None
    base_url = run_network_diagnostic(base_url)

    # ③ 获取模型列表
    print(c("  ⏳ 正在获取模型列表...", C.CYAN))

    try:
        t0 = time.time()
        models = fetch_models(base_url, api_key)
        t_fetch = time.time() - t0
    except PermissionError as e:
        print(c(f"\n  ❌ {e}", C.RED))
        print(c("     请确认密钥是否正确，是否已在 Google AI Studio 中启用", C.YELLOW))
        sys.exit(1)
    except ConnectionError as e:
        print(c(f"\n  ❌ {e}", C.RED))
        print(c("     网络连接出现问题，请参考上方诊断结果排查", C.YELLOW))
        sys.exit(1)
    except Exception as e:
        err_str = str(e)
        if "location is not supported" in err_str.lower():
            print(c(f"\n  ❌ 地区限制: {e}", C.RED))
            print(c("     诊断未能提前拦截此问题，请切换代理节点到美国/日本/英国后重试", C.YELLOW))
        elif "quota" in err_str.lower():
            print(c(f"\n  ❌ 配额耗尽: {e}", C.RED))
            print(c("     此密钥的免费配额已用完，请更换密钥或等待配额重置", C.YELLOW))
        else:
            print(c(f"\n  ❌ {e}", C.RED))
        sys.exit(1)

    if not models:
        print(c("  ⚠️  密钥有效，但未找到任何可用模型。", C.YELLOW))
        sys.exit(0)

    print(c(f"  ✅ 发现 {len(models)} 个模型 ({t_fetch:.1f}s)", C.GREEN + C.BOLD))

    # ④ 逐一测试模型可用性（带进度条）
    print()
    print(c("  ⏳ 正在逐一测试模型可用性...", C.CYAN))
    print()

    test_results = {}
    t0 = time.time()
    for i, model in enumerate(models, 1):
        model_name = model.get("name", "")
        display = model.get("displayName", model_name.replace("models/", ""))
        progress_bar(i, len(models), label=display)
        result = test_model(base_url, api_key, model)
        test_results[model_name] = result
        if i % 5 == 0:
            time.sleep(0.2)
    clear_line()
    t_test = time.time() - t0
    print(c(f"  ✅ 全部测试完成 ({t_test:.1f}s)", C.GREEN + C.BOLD))

    # ⑤ 按系列分组展示
    print()
    divider("═")
    print(c("  📋 模型详细列表", C.BOLD))
    divider("═")

    # 分组
    groups = {}
    for model in models:
        series = classify_model(model)
        groups.setdefault(series, []).append(model)

    idx = 0
    for series in SERIES_ORDER:
        if series not in groups:
            continue
        group = groups[series]
        icon = SERIES_ICONS.get(series, "📦")

        # 统计该系列可用数
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

    # ⑥ 统计摘要
    print_summary(models, test_results)

    # ⑦ 自动导出
    filename = export_json(api_key, base_url, models, test_results)
    print(c(f"  💾 测试结果已自动导出到: {filename}", C.GREEN))
    print()


if __name__ == "__main__":
    main()
