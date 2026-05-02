# AI Model Rank Crawler

CocoLoop AI 模型排行榜爬虫，用于抓取 https://top.cocoloop.cn/ 的模型排行信息。

## 功能特性

- 爬取 AI 模型排行榜数据
- 支持获取模型图片（可选）
- 结构化 JSON 输出
- 包含完整的模型信息字段

## 环境要求

- Python >= 3.13
- uv 包管理器

## 安装

```powershell
# 克隆项目
git clone https://github.com/scikie/model-top.git
cd modle-top

# 安装依赖
uv sync
```

## 使用方法

### 基本用法

```powershell
uv run crawler.py
```

### 在代码中使用

```python
from crawler import ModelRankCrawler

crawler = ModelRankCrawler()

try:
    # 爬取数据（不获取图片）
    models = crawler.crawl(fetch_images=False)
    
    # 爬取数据（获取图片，较慢）
    # models = crawler.crawl(fetch_images=True)
    
    # 保存到 JSON
    crawler.save_to_json(models, "output/models.json")
finally:
    crawler.close()
```

## 数据结构

每个模型包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| rank | int | 排名 |
| name | str | 模型名称 |
| company | str | 开发公司/团队 |
| country | str | 国家/地区代码 |
| description | str | 模型描述 |
| score | int | 评分 |
| trend_direction | str | 趋势方向 (up/down) |
| trend_value | int | 排名变化值 |
| is_open_source | bool | 是否开源 |
| pricing | str | 定价信息 |
| pricing_unit | str | 定价单位 |
| detail_url | str | 详情页链接 |
| image_url | str | 模型图片链接 |

## 输出示例

```json
[
  {
    "rank": 1,
    "name": "HappyHorse 1.0",
    "company": "Alibaba",
    "country": "CN",
    "description": "ATH 郑波团队出品，视频 Arena 榜首",
    "score": 1512,
    "trend_direction": "up",
    "trend_value": 18,
    "is_open_source": true,
    "pricing": "API 公测中",
    "pricing_unit": "定价",
    "detail_url": "https://top.cocoloop.cn/models/happyhorse-1",
    "image_url": null
  }
]
```

## 项目结构

```
modle-top/
├── crawler.py        # 主爬虫脚本
├── output/
│   └── models.json   # 输出数据
├── download/         # 本地 HTML 参考
├── pyproject.toml    # 项目配置
└── README.md
```

## 注意事项

- 获取图片（`fetch_images=True`）会访问每个模型的详情页，耗时较长
- 请合理控制请求频率，避免对目标服务器造成压力
- 数据仅供参考，以官网为准

## License

MIT
