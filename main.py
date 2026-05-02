"""
主程序入口文件

这个文件是项目的入口点。
目前的实现比较简单，你可以在这里添加自定义的爬虫逻辑。

【学习建议】
你可以尝试：
1. 修改爬取的参数（如是否获取图片）
2. 添加命令行参数支持
3. 实现定时爬取
4. 添加数据分析和可视化功能
"""


def main():
    """
    主函数
    
    【知识点：函数定义】
    def 关键字用于定义函数
    函数名后的括号内是参数列表（这个函数没有参数）
    """
    print("Hello from modle-top!")
    
    # TODO: 在这里调用 crawler.py 中的爬虫
    # from crawler import ModelRankCrawler
    # crawler = ModelRankCrawler()
    # models = crawler.crawl()


# 【知识点：模块入口检测】
# if __name__ == "__main__": 是 Python 程序的标准入口写法
# 只有当这个文件被直接运行时，才会执行 main()
# 如果这个文件被 import 导入，则不会执行
if __name__ == "__main__":
    main()


# ============================================================================
# 练习建议
# ============================================================================

"""
【练习 1：运行爬虫】
修改这个文件，导入并运行 crawler.py 中的爬虫：
    
    from crawler import ModelRankCrawler
    
    crawler = ModelRankCrawler()
    try:
        models = crawler.crawl(fetch_images=False)
        crawler.save_to_json(models, "output/models.json")
    finally:
        crawler.close()

【练习 2：添加命令行参数】
使用 argparse 模块添加命令行参数支持：

    import argparse
    
    parser = argparse.ArgumentParser(description='爬取模型排行榜')
    parser.add_argument('--images', action='store_true', help='是否获取图片')
    parser.add_argument('--output', default='output/models.json', help='输出文件路径')
    args = parser.parse_args()

【练习 3：数据分析】
读取爬取的 JSON 文件，进行数据分析：

    - 统计各国家的模型数量
    - 找出评分最高的开源模型
    - 分析价格分布
    - 生成可视化图表（使用 matplotlib）
"""
