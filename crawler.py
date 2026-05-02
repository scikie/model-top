"""
 ============================================================================
 模型排行榜爬虫 - 学习版
 ============================================================================
 
 这是一个用于爬取 https://top.cocoloop.cn/ 网站模型排行榜数据的爬虫程序。
 
 【学习目标】
 1. 理解 HTTP 请求的基本概念（GET请求、请求头、超时设置等）
 2. 学习 HTML 解析技术（使用 BeautifulSoup 库）
 3. 掌握 Python 数据类（dataclass）的使用
 4. 了解爬虫的道德规范和最佳实践
 5. 学习数据持久化（保存为 JSON 文件）
 
 【前置知识】
 - Python 基础语法（变量、函数、类、列表推导式等）
 - 了解 HTTP 协议的基本概念
 - 知道什么是 HTML 和 CSS 选择器
 
 【依赖库】
 - httpx: 现代 HTTP 客户端库（比 requests 更现代化，支持 HTTP/2）
 - beautifulsoup4: HTML/XML 解析库
 - lxml: 高性能的 HTML 解析器（BeautifulSoup 的后端）
"""


# ============================================================================
# 导入区域
# ============================================================================

# 【Python 标准库】
import json  # JSON 数据处理，用于保存和读取 JSON 格式数据
import re  # 正则表达式模块，用于文本模式匹配和提取

# 【数据类相关】
# dataclass: Python 3.7+ 引入的装饰器，用于快速创建数据类
# field: 用于自定义字段的默认值和其他属性
# asdict: 将 dataclass 实例转换为字典
from dataclasses import dataclass, field, asdict

# 【类型提示】
# Optional: 表示一个值可以是指定类型或 None（Python 3.10+ 可以用 X | None 替代）
from typing import Optional

# 【路径处理】
# Path: 面向对象的文件系统路径处理，比字符串路径更安全更强大
from pathlib import Path

# 【第三方库】
import httpx  # HTTP 客户端库，支持同步和异步请求
from bs4 import BeautifulSoup  # HTML 解析库，用于从网页中提取数据


# ============================================================================
# 数据模型定义
# ============================================================================

@dataclass
class ModelInfo:
    """
    【知识点：@dataclass 装饰器】
    
    dataclass 是 Python 3.7 引入的特性，它可以：
    1. 自动生成 __init__、__repr__、__eq__ 等魔法方法
    2. 减少样板代码，让类定义更简洁
    3. 提供类型提示支持
    
    等价的传统写法：
    class ModelInfo:
        def __init__(self, rank, name, company=None, ...):
            self.rank = rank
            self.name = name
            ...
    
    【参数说明】
    rank: 排名（必须提供）
    name: 模型名称（必须提供）
    company: 公司名称（可选，默认 None）
    country: 国家（可选）
    description: 描述信息（可选）
    score: 分数（可选）
    trend_direction: 趋势方向，'up' 或 'down'（可选）
    trend_value: 趋势变化的数值（可选）
    is_open_source: 是否开源，默认为 False
    pricing: 价格（可选）
    pricing_unit: 价格单位，如 '/百万token'（可选）
    detail_url: 详情页链接（可选）
    image_url: 图片链接（可选）
    """
    rank: int  # 排名，整数类型，没有默认值，创建对象时必须提供
    name: str  # 模型名称，字符串类型，必须提供
    
    # 【知识点：Optional 类型提示】
    # Optional[str] 等价于 str | None（Python 3.10+）
    # 表示这个参数可以是字符串，也可以是 None
    company: Optional[str] = None  # 公司名，默认为 None
    country: Optional[str] = None  # 国家，默认为 None
    description: Optional[str] = None  # 描述，默认为 None
    score: Optional[int] = None  # 分数，默认为 None
    trend_direction: Optional[str] = None  # 趋势方向
    trend_value: Optional[int] = None  # 趋势数值
    is_open_source: bool = False  # 是否开源，默认 False
    pricing: Optional[str] = None  # 价格
    pricing_unit: Optional[str] = None  # 价格单位
    detail_url: Optional[str] = None  # 详情页链接
    image_url: Optional[str] = None  # 图片链接


# ============================================================================
# 爬虫主类
# ============================================================================

class ModelRankCrawler:
    """
    模型排行榜爬虫类
    
    【知识点：类的组织结构】
    一个良好的爬虫类通常包含以下组件：
    
    1. 配置常量（如 BASE_URL）
    2. 初始化方法（__init__）
    3. HTTP 请求方法（获取网页内容）
    4. 解析方法（从 HTML 中提取数据）
    5. 业务逻辑方法（整合请求和解析）
    6. 数据保存方法
    7. 资源清理方法（close）
    
    【设计原则】
    - 单一职责：每个方法只做一件事
    - 可配置性：通过参数控制行为（如 fetch_images）
    - 错误处理：合理捕获和处理异常
    - 资源管理：正确关闭网络连接等资源
    """
    
    # 【知识点：类变量 vs 实例变量】
    # 类变量：所有实例共享的变量，定义在类体中、方法外
    # 实例变量：每个实例独有的变量，定义在 __init__ 方法中
    # BASE_URL 是类变量，所有爬虫实例共享这个地址
    BASE_URL = "https://top.cocoloop.cn/"
    
    def __init__(self):
        """
        初始化爬虫
        
        【知识点：__init__ 方法】
        __init__ 是 Python 的构造方法（初始化方法）
        在创建对象时自动调用，用于初始化对象的状态
        
        使用方式：
        crawler = ModelRankCrawler()  # 自动调用 __init__
        
        【知识点：httpx.Client】
        httpx 是一个现代化的 HTTP 客户端库，类似于 requests 但功能更强：
        - 支持同步和异步两种模式
        - 支持 HTTP/2
        - 更好的超时和重定向处理
        - 连接池管理（提高性能）
        
        使用 Client（客户端）而不是每次都创建新连接的好处：
        1. 连接复用：保持 TCP 连接，减少握手开销
        2. 连接池：自动管理多个连接
        3. 配置集中：所有请求共享相同的配置（headers、timeout 等）
        """
        self.client = httpx.Client(
            # 【知识点：HTTP Headers（请求头）】
            # HTTP 请求头用于告诉服务器关于客户端的信息
            # 这是爬虫最重要的配置之一
            
            headers={
                # 【User-Agent：浏览器身份标识】
                # 告诉服务器你是谁（什么浏览器、什么操作系统）
                # 很多网站会检查 User-Agent 来识别爬虫
                # 使用真实浏览器的 User-Agent 可以让爬虫看起来像正常用户
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                
                # 【Accept：告诉服务器你想要什么类型的内容】
                # text/html: HTML 文档
                # application/xhtml+xml: XHTML 文档
                # application/xml: XML 文档
                # image/webp: WebP 图片格式
                # */*: 任何类型
                # q=0.9 等是优先级权重，1.0 最高
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                
                # 【Accept-Language：告诉服务器你偏好的语言】
                # zh-CN: 中文（中国）
                # zh: 中文
                # en: 英文
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            
            # 【知识点：超时设置】
            # timeout: 请求超时时间，防止程序因网络问题而永久等待
            # 30.0 秒是合理的选择（网站响应时间 + 网络延迟）
            # 超时会抛出 httpx.TimeoutException 异常
            timeout=30.0,
            
            # 【知识点：重定向（Redirect）】
            # follow_redirects=True: 自动跟随重定向（如 301、302 响应）
            # 例如：访问 http://example.com 自动跳转到 https://example.com
            follow_redirects=True,
        )
    
    def fetch_page(self, url: Optional[str] = None) -> str:
        """
        获取网页内容
        
        【参数】
        url: 要获取的网址，如果为 None 则使用 BASE_URL
        
        【返回值】
        网页的 HTML 内容（字符串形式）
        
        【知识点：HTTP GET 请求】
        GET 请求是最常见的 HTTP 请求方法：
        - 用于获取（读取）数据
        - 参数通常放在 URL 中（查询字符串）
        - 不应该有副作用（不会修改服务器数据）
        
        其他常见的 HTTP 方法：
        - POST: 提交数据（如表单提交）
        - PUT: 更新数据
        - DELETE: 删除数据
        """
        # 【知识点：默认参数值的惯用写法】
        # url = url or self.BASE_URL
        # 如果 url 是 None 或空字符串，使用 self.BASE_URL
        # 这比三元运算符更 Pythonic
        url = url or self.BASE_URL
        
        # 【知识点：发送 GET 请求】
        # client.get(url) 返回一个 Response 对象，包含：
        # - response.text: 响应内容（字符串）
        # - response.content: 响应内容（字节）
        # - response.status_code: HTTP 状态码
        # - response.headers: 响应头
        response = self.client.get(url)
        
        # 【知识点：HTTP 状态码】
        # 2xx: 成功（200 OK, 201 Created, 204 No Content）
        # 3xx: 重定向（301 永久移动, 302 临时移动）
        # 4xx: 客户端错误（404 Not Found, 403 Forbidden）
        # 5xx: 服务器错误（500 Internal Server Error）
        
        # 【知识点：raise_for_status()】
        # 检查响应状态码，如果是 4xx 或 5xx，抛出异常
        # 这是一种"快速失败"的错误处理策略
        # 例如：404 会抛出 httpx.NotFoundError
        response.raise_for_status()
        
        # 返回网页的 HTML 内容
        return response.text
    
    def parse_rank(self, text: str) -> Optional[int]:
        """
        从文本中解析排名数字
        
        【参数】
        text: 包含数字的文本，如 "第1名" 或 "#123"
        
        【返回值】
        解析出的整数，如果没有找到则返回 None
        
        【知识点：正则表达式（Regular Expression）】
        正则表达式是文本匹配的强大工具：
        - r'\\d+' 是一个正则表达式
        - \\d: 匹配一个数字（等价于 [0-9]）
        - +: 匹配前面的字符一次或多次
        - r'...' : 原始字符串，不转义反斜杠
        
        常用正则表达式：
        - r'\\d+': 匹配整数
        - r'\\d+\\.\\d+': 匹配小数
        - r'[a-zA-Z]+': 匹配字母
        - r'\\w+': 匹配单词字符（字母、数字、下划线）
        - r'\\s+': 匹配空白字符
        """
        # 【知识点：re.search()】
        # 在字符串中搜索第一个匹配项
        # 返回一个 Match 对象，如果没有匹配则返回 None
        match = re.search(r'\d+', text)
        
        # 【知识点：三元条件表达式】
        # value_if_true if condition else value_if_false
        # match.group() 返回匹配的字符串
        # int() 将字符串转换为整数
        return int(match.group()) if match else None
    
    def parse_trend(self, element) -> tuple[Optional[str], Optional[int]]:
        """
        解析趋势信息（上升或下降）
        
        【参数】
        element: BeautifulSoup 元素对象
        
        【返回值】
        元组 (direction, value)
        - direction: "up" 或 "down"，表示上升或下降
        - value: 变化的数值
        
        【知识点：CSS 选择器】
        CSS 选择器用于定位 HTML 元素：
        - 'span': 选择所有 <span> 标签
        - '.class': 选择 class="class" 的元素
        - '#id': 选择 id="id" 的元素
        - 'span[class*="text-signal-"]': 选择 span 标签，且 class 包含 "text-signal-"
        - [attr*="value"]: 属性选择器，匹配属性包含某值
        
        select_one(): 返回第一个匹配的元素
        select(): 返回所有匹配的元素列表
        """
        # 【知识点：CSS 属性选择器】
        # span[class*="text-signal-"] 选择 class 属性包含 "text-signal-" 的 span 元素
        # * 表示"包含"（还有 ^= 开头，$= 结尾）
        trend_elem = element.select_one('span[class*="text-signal-"]')
        
        if not trend_elem:
            return None, None
        
        # 【知识点：get() 方法获取属性】
        # trend_elem.get("class", []) 获取 class 属性
        # 第二个参数是默认值（当属性不存在时返回）
        # class 属性返回一个列表，如 ['text-signal-up', 'text-lg']
        # 如果 class 属性存在但为空字符串，返回 ['']
        direction = "up" if "text-signal-up" in trend_elem.get("class", []) else "down"
        
        # 【知识点：get_text() 提取文本】
        # get_text() 获取元素内的所有文本（包括子元素的文本）
        # strip=True: 去除首尾空白字符
        value_text = trend_elem.get_text(strip=True)
        value = self.parse_rank(value_text)
        
        # 【知识点：返回多个值（元组解包）】
        # Python 函数可以返回多个值，实际返回的是一个元组
        # 调用方可以这样接收：direction, value = self.parse_trend(element)
        return direction, value
    
    def parse_pricing(self, element) -> tuple[Optional[str], Optional[str]]:
        """
        解析价格信息
        
        【参数】
        element: BeautifulSoup 元素对象
        
        【返回值】
        元组 (pricing, pricing_unit)
        - pricing: 价格值，如 "0.0012"
        - pricing_unit: 价格单位，如 "/百万token"
        
        【知识点：转义 CSS 选择器】
        CSS 中的特殊字符需要转义：
        - '.': 类选择器
        - '#': ID 选择器
        - ':': 伪类
        - '\\\\': 转义符
        
        在 BeautifulSoup 中，类名中的 '.' 和 ':' 需要转义：
        - 'div.hidden.md\\\\:block' 匹配 <div class="hidden md:block">
        - 注意 Python 字符串中 '\\\\:' 实际是 '\\:'
        """
        # 【知识点：复杂的 CSS 选择器】
        # 这个选择器包含多个部分：
        # - div: 选择 div 标签
        # - .hidden: 类名包含 "hidden"
        # - md\\:block: 类名包含 "md:block"（响应式设计中的 Tailwind CSS）
        # - .min-w-0: 类名包含 "min-w-0"
        # 多个类名连写表示 AND 关系（同时包含所有类）
        pricing_container = element.select_one('div.hidden.md\\:block.min-w-0')
        
        if not pricing_container:
            return None, None
        
        # 【知识点：列表推导式（List Comprehension）】
        # [expression for item in iterable]
        # 这是 Python 最强大的特性之一，用于快速创建列表
        
        # 等价的传统写法：
        # texts = []
        # for t in pricing_container.find_all('div'):
        #     texts.append(t.get_text(strip=True))
        
        # 列表推导式更简洁高效
        texts = [t.get_text(strip=True) for t in pricing_container.find_all('div')]
        
        # 【知识点：列表索引和边界检查】
        # 访问列表前要检查索引是否越界
        # len(texts) >= 1 确保 texts[0] 不会报错
        if len(texts) >= 1:
            # 【知识点：三元表达式】
            # texts[0] if texts[0] != '—' else None
            # 如果 texts[0] 是 '—'（占位符），则返回 None
            pricing_value = texts[0] if texts[0] != '—' else None
            pricing_unit = texts[1] if len(texts) > 1 else None
            return pricing_value, pricing_unit
        
        return None, None
    
    def parse_models(self, html: str) -> list[ModelInfo]:
        """
        解析整个页面，提取所有模型信息
        
        【参数】
        html: 网页的 HTML 内容
        
        【返回值】
        模型信息列表
        
        【知识点：BeautifulSoup 解析器】
        BeautifulSoup 支持多种解析器：
        - 'html.parser': Python 内置解析器，速度适中，容错性好
        - 'lxml': 第三方解析器，速度最快，需要安装
        - 'lxml-xml': XML 解析器
        - 'html5lib': 最容错，但速度最慢
        
        推荐使用 'lxml'（需要 pip install lxml）
        """
        # 【知识点：创建 BeautifulSoup 对象】
        # BeautifulSoup(html, 'lxml') 将 HTML 字符串解析为可查询的对象树
        soup = BeautifulSoup(html, 'lxml')
        models = []
        
        # 【知识点：CSS 属性选择器 - 开头匹配】
        # a[href^="/models/"] 选择 href 属性以 "/models/" 开头的 <a> 标签
        # ^= 表示"以...开头"
        # $= 表示"以...结尾"
        # *= 表示"包含"
        model_links = soup.select('a[href^="/models/"]')
        
        # 【知识点：异常处理 - 继续执行】
        # 在循环中，即使某个元素解析失败，也要继续处理其他元素
        # 这比整个程序崩溃要好
        for link in model_links:
            try:
                model = self._parse_model_item(link)
                if model:
                    models.append(model)
            except Exception as e:
                # 【知识点：错误日志】
                # 打印错误信息，但不中断程序
                # 实际项目中应该使用 logging 模块
                print(f"Error parsing model: {e}")
                continue
        
        return models
    
    def _parse_model_item(self, element) -> Optional[ModelInfo]:
        """
        解析单个模型条目
        
        【知识点：私有方法命名约定】
        以单下划线开头的方法表示"内部使用"（protected）
        以双下划线开头的方法表示"私有"（private，会有名称改编）
        
        这只是约定，Python 没有真正的私有方法
        但 IDE 和 linter 会给出警告
        
        【参数】
        element: BeautifulSoup 元素对象（一个 <a> 标签）
        
        【返回值】
        ModelInfo 对象，如果解析失败返回 None
        """
        # 【知识点：CSS 选择器链式调用】
        # 使用 or 连接多个选择器，按优先级依次尝试
        # 先尝试 'span.tabular-nums.text-gold-dark'（金色，通常表示前几名）
        # 如果没有，再尝试银色、铜色、灰色
        rank_elem = (
            element.select_one('span.tabular-nums.text-gold-dark') or
            element.select_one('span.tabular-nums.text-silver') or
            element.select_one('span.tabular-nums.text-bronze') or
            element.select_one('span.tabular-nums.text-gray-400')
        )
        
        if not rank_elem:
            return None
        
        # 解析排名
        rank = self.parse_rank(rank_elem.get_text(strip=True))
        if rank is None:
            return None
        
        # 【知识点：CSS 类选择器】
        # 'span.truncate' 选择 class 包含 "truncate" 的 span 元素
        # truncate 是 Tailwind CSS 的类，用于文本截断
        name_elem = element.select_one('span.truncate')
        name = name_elem.get_text(strip=True) if name_elem else None
        
        # 【知识点：元素存在性检查】
        # 很多时候只需要检查元素是否存在（不需要其内容）
        # element.select_one(...) is not None 检查元素是否存在
        is_open_source = element.select_one('span.text-gold-dark') is not None
        
        # 【知识点：批量选择和索引访问】
        # select() 返回列表，可以通过索引访问
        # 注意检查列表长度，避免 IndexError
        info_divs = element.select('div.hidden.md\\:block')
        company = None
        country = None
        description = None
        
        # 按索引依次获取信息
        if len(info_divs) >= 1:
            company = info_divs[0].get_text(strip=True)
        if len(info_divs) >= 2:
            country = info_divs[1].get_text(strip=True)
        if len(info_divs) >= 3:
            description = info_divs[2].get_text(strip=True)
        
        # 【知识点：CSS 类名中的特殊字符】
        # 'div.text-right div.text-\\[18px\\]'
        # [] 在 CSS 选择器中有特殊含义，需要转义
        # \\[ 和 \\] 在 Python 字符串中表示 \[ 和 \]
        score_elem = element.select_one('div.text-right div.text-\\[18px\\]')
        score = self.parse_rank(score_elem.get_text(strip=True)) if score_elem else None
        
        # 解析趋势和价格
        trend_direction, trend_value = self.parse_trend(element)
        pricing, pricing_unit = self.parse_pricing(element)
        
        # 【知识点：获取元素属性】
        # element.get('href', '') 获取 href 属性，默认为空字符串
        href = element.get('href', '')
        detail_url = f"https://top.cocoloop.cn{href}" if href else None
        
        # 【知识点：创建 dataclass 实例】
        # dataclass 自动生成的 __init__ 方法
        # 可以使用位置参数或关键字参数
        return ModelInfo(
            rank=rank,
            name=name,
            company=company,
            country=country,
            description=description,
            score=score,
            trend_direction=trend_direction,
            trend_value=trend_value,
            is_open_source=is_open_source,
            pricing=pricing,
            pricing_unit=pricing_unit,
            detail_url=detail_url,
            image_url=None,
        )
    
    def fetch_detail_image(self, detail_url: str) -> Optional[str]:
        """
        从详情页获取模型图片
        
        【参数】
        detail_url: 详情页链接
        
        【返回值】
        图片 URL，如果找不到则返回 None
        
        【知识点：爬虫的深度】
        - 一级页面：首页、列表页
        - 二级页面：详情页（从一级页面的链接进入）
        - 三级页面：更深层的页面
        
        这个方法实现了二级页面爬取
        """
        try:
            # 访问详情页
            html = self.fetch_page(detail_url)
            soup = BeautifulSoup(html, 'lxml')
            
            # 【知识点：Open Graph 协议】
            # og:image 是 Open Graph 协议的元标签
            # 用于社交媒体分享时显示的图片
            # 很多网站都会设置这个标签
            og_image = soup.select_one('meta[property="og:image"]')
            if og_image:
                # 【知识点：获取自闭合标签的属性】
                # meta 标签是自闭合标签，没有文本内容
                # 使用 get() 获取属性值
                return og_image.get('content')
            
            # 备用方案：查找页面中的图片
            img = soup.select_one('img[class*="model"]') or soup.select_one('main img')
            if img and img.get('src'):
                src = img.get('src')
                # 【知识点：相对 URL 转 绝对 URL】
                # 如果 src 以 '/' 开头，是相对路径，需要拼接域名
                if src.startswith('/'):
                    return f"https://top.cocoloop.cn{src}"
                return src
        except Exception as e:
            print(f"Error fetching detail page: {e}")
        
        return None
    
    def crawl(self, fetch_images: bool = False) -> list[ModelInfo]:
        """
        执行爬虫主流程
        
        【参数】
        fetch_images: 是否获取详情页图片（会增加请求次数）
        
        【返回值】
        模型信息列表
        
        【知识点：爬虫工作流程】
        1. 发送 HTTP 请求获取网页内容
        2. 解析 HTML 提取数据
        3. （可选）跟进链接获取更多数据
        4. 保存数据
        
        这是爬虫的核心方法，协调其他方法完成整个流程
        """
        print(f"Fetching {self.BASE_URL}...")
        html = self.fetch_page()
        
        print("Parsing models...")
        models = self.parse_models(html)
        print(f"Found {len(models)} models")
        
        # 【知识点：条件执行】
        # 获取详情页图片是可选的，因为会显著增加请求次数
        # 可能被网站的反爬机制检测到
        if fetch_images:
            print("Fetching model images (this may take a while)...")
            # 【知识点：enumerate() 函数】
            # enumerate(iterable, start) 返回 (index, item) 的迭代器
            # 用于需要索引的循环
            for i, model in enumerate(models, 1):
                if model.detail_url:
                    # 显示进度
                    print(f"  [{i}/{len(models)}] {model.name}")
                    model.image_url = self.fetch_detail_image(model.detail_url)
        
        return models
    
    def save_to_json(self, models: list[ModelInfo], output_path: str):
        """
        保存数据到 JSON 文件
        
        【参数】
        models: 模型信息列表
        output_path: 输出文件路径
        
        【知识点：数据持久化】
        常见的数据存储格式：
        - JSON: 轻量级，人类可读，适合半结构化数据
        - CSV: 表格格式，适合 Excel 处理
        - SQLite: 轻量级数据库，适合结构化数据
        - Pickle: Python 专用，不适合长期存储
        """
        # 【知识点：dataclass 转字典】
        # asdict(model) 将 dataclass 实例转换为字典
        # 列表推导式将所有模型转换为字典
        data = [asdict(m) for m in models]
        
        # 【知识点：Path 对象】
        # Path(output_path) 创建路径对象
        # 比字符串路径更安全、更强大
        output_file = Path(output_path)
        
        # 【知识点：创建目录】
        # parent.mkdir(parents=True, exist_ok=True)
        # - parents=True: 递归创建所有父目录
        # - exist_ok=True: 目录已存在时不报错
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 【知识点：上下文管理器（with 语句）】
        # with 语句自动管理资源（如文件）
        # 离开 with 块时，文件会自动关闭
        # 即使发生异常，也能正确关闭资源
        
        # 【知识点：文件编码】
        # encoding='utf-8': 确保中文等非 ASCII 字符正确保存
        # 中文 Windows 默认编码可能是 GBK，显式指定 UTF-8 更安全
        
        # 【知识点：JSON 中文处理】
        # ensure_ascii=False: 允许在 JSON 中直接保存 Unicode 字符
        # 如果为 True（默认），中文会被转义为 \uXXXX
        # indent=2: 美化输出，缩进 2 个空格
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(models)} models to {output_path}")
    
    def close(self):
        """
        关闭爬虫，释放资源
        
        【知识点：资源清理】
        网络连接、文件句柄等资源需要手动关闭
        否则会造成资源泄漏
        
        使用方式：
        crawler = ModelRankCrawler()
        try:
            # 使用 crawler
            ...
        finally:
            crawler.close()  # 确保资源被释放
        
        或者使用上下文管理器（需要实现 __enter__ 和 __exit__）
        """
        self.client.close()


# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """
    主函数：程序入口
    
    【知识点：程序结构】
    一个良好的 Python 程序结构：
    1. 导入区域（标准库 → 第三方库 → 本地模块）
    2. 常量定义
    3. 类和函数定义
    4. 主程序入口
    
    【知识点：main 函数的作用】
    - 集中管理程序流程
    - 方便测试和导入
    - 避免全局代码执行
    """
    # 【知识点：创建对象】
    # crawler = ModelRankCrawler() 调用 __init__ 初始化对象
    crawler = ModelRankCrawler()
    
    try:
        # 【知识点：try-finally 语句】
        # finally 块无论是否发生异常都会执行
        # 用于确保资源清理（如关闭网络连接）
        
        # 执行爬虫，不获取详情页图片
        models = crawler.crawl(fetch_images=False)
        
        # 保存到 JSON 文件
        crawler.save_to_json(models, "output/models.json")
        
        # 【知识点：数据展示】
        # 打印前 10 个模型的信息
        print("\nTop 10 Models:")
        for m in models[:10]:
            # 【知识点：三元表达式】
            # 为开源模型添加标记
            badge = " [开源]" if m.is_open_source else ""
            
            # 【知识点：f-string 格式化】
            # Python 3.6+ 的字符串格式化方式
            # f"..." 中的 {expression} 会被替换为表达式的值
            trend = f" ({'↑' if m.trend_direction == 'up' else '↓'}{m.trend_value})" if m.trend_value else ""
            print(f"  {m.rank}. {m.name}{badge} - Score: {m.score}{trend}")
    
    finally:
        # 【知识点：资源清理】
        # 确保网络连接被关闭
        crawler.close()


# ============================================================================
# 程序入口点
# ============================================================================

# 【知识点：__name__ 变量】
# Python 为每个模块设置 __name__ 变量：
# - 如果模块被直接运行（python crawler.py），__name__ == "__main__"
# - 如果模块被导入（import crawler），__name__ == "crawler"（模块名）
#
# 这样可以防止在导入模块时执行不需要的代码
# 是 Python 程序的标准入口写法
if __name__ == "__main__":
    main()


# ============================================================================
# 拓展知识
# ============================================================================

"""
【1. 爬虫的道德和法律问题】

✓ 应该做的：
- 遵守 robots.txt（网站的爬虫协议）
- 设置合理的请求间隔（不要对服务器造成压力）
- 使用真实的 User-Agent（但不要冒充）
- 尊重网站的服务条款
- 不要爬取个人信息和敏感数据

✗ 不应该做的：
- 暴力破解验证码
- 使用爬虫进行 DDoS 攻击
- 爬取受版权保护的内容用于商业用途
- 不遵守 robots.txt

【2. 常见的反爬机制】

- User-Agent 检测：检查是否是真实浏览器
- IP 限制：同一 IP 请求次数过多会被封禁
- 验证码：人机验证
- 动态加载：JavaScript 渲染的内容（需要 Selenium/Playwright）
- Cookie/Session：需要登录才能访问

【3. 进阶技术】

- 异步爬虫（asyncio + httpx 异步模式）
- 分布式爬虫（Scrapy 框架）
- 动态页面爬取（Selenium/Playwright）
- 代理池（避免 IP 被封）
- 数据存储（数据库、消息队列）

【4. 学习资源】

- 官方文档：
  • httpx: https://www.python-httpx.org/
  • BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
  
- 进阶框架：
  • Scrapy: https://scrapy.org/（功能强大的爬虫框架）
  • Playwright: https://playwright.dev/python/（浏览器自动化）
  
- 教程：
  • Python 官方教程：https://docs.python.org/zh-cn/3/tutorial/
  • 正则表达式教程：https://regexone.com/
"""
