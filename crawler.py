import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

import httpx
from bs4 import BeautifulSoup


@dataclass
class ModelInfo:
    rank: int
    name: str
    company: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    score: Optional[int] = None
    trend_direction: Optional[str] = None
    trend_value: Optional[int] = None
    is_open_source: bool = False
    pricing: Optional[str] = None
    pricing_unit: Optional[str] = None
    detail_url: Optional[str] = None
    image_url: Optional[str] = None


class ModelRankCrawler:
    BASE_URL = "https://top.cocoloop.cn/"
    
    def __init__(self):
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=30.0,
            follow_redirects=True,
        )
    
    def fetch_page(self, url: Optional[str] = None) -> str:
        url = url or self.BASE_URL
        response = self.client.get(url)
        response.raise_for_status()
        return response.text
    
    def parse_rank(self, text: str) -> Optional[int]:
        match = re.search(r'\d+', text)
        return int(match.group()) if match else None
    
    def parse_trend(self, element) -> tuple[Optional[str], Optional[int]]:
        trend_elem = element.select_one('span[class*="text-signal-"]')
        if not trend_elem:
            return None, None
        
        direction = "up" if "text-signal-up" in trend_elem.get("class", []) else "down"
        value_text = trend_elem.get_text(strip=True)
        value = self.parse_rank(value_text)
        
        return direction, value
    
    def parse_pricing(self, element) -> tuple[Optional[str], Optional[str]]:
        pricing_container = element.select_one('div.hidden.md\\:block.min-w-0')
        if not pricing_container:
            return None, None
        
        texts = [t.get_text(strip=True) for t in pricing_container.find_all('div')]
        if len(texts) >= 1:
            pricing_value = texts[0] if texts[0] != '—' else None
            pricing_unit = texts[1] if len(texts) > 1 else None
            return pricing_value, pricing_unit
        
        return None, None
    
    def parse_models(self, html: str) -> list[ModelInfo]:
        soup = BeautifulSoup(html, 'lxml')
        models = []
        
        model_links = soup.select('a[href^="/models/"]')
        
        for link in model_links:
            try:
                model = self._parse_model_item(link)
                if model:
                    models.append(model)
            except Exception as e:
                print(f"Error parsing model: {e}")
                continue
        
        return models
    
    def _parse_model_item(self, element) -> Optional[ModelInfo]:
        rank_elem = (
            element.select_one('span.tabular-nums.text-gold-dark') or
            element.select_one('span.tabular-nums.text-silver') or
            element.select_one('span.tabular-nums.text-bronze') or
            element.select_one('span.tabular-nums.text-gray-400')
        )
        if not rank_elem:
            return None
        
        rank = self.parse_rank(rank_elem.get_text(strip=True))
        if rank is None:
            return None
        
        name_elem = element.select_one('span.truncate')
        name = name_elem.get_text(strip=True) if name_elem else None
        
        is_open_source = element.select_one('span.text-gold-dark') is not None
        
        info_divs = element.select('div.hidden.md\\:block')
        company = None
        country = None
        description = None
        
        if len(info_divs) >= 1:
            company = info_divs[0].get_text(strip=True)
        if len(info_divs) >= 2:
            country = info_divs[1].get_text(strip=True)
        if len(info_divs) >= 3:
            description = info_divs[2].get_text(strip=True)
        
        score_elem = element.select_one('div.text-right div.text-\\[18px\\]')
        score = self.parse_rank(score_elem.get_text(strip=True)) if score_elem else None
        
        trend_direction, trend_value = self.parse_trend(element)
        
        pricing, pricing_unit = self.parse_pricing(element)
        
        href = element.get('href', '')
        detail_url = f"https://top.cocoloop.cn{href}" if href else None
        
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
        try:
            html = self.fetch_page(detail_url)
            soup = BeautifulSoup(html, 'lxml')
            
            og_image = soup.select_one('meta[property="og:image"]')
            if og_image:
                return og_image.get('content')
            
            img = soup.select_one('img[class*="model"]') or soup.select_one('main img')
            if img and img.get('src'):
                src = img.get('src')
                if src.startswith('/'):
                    return f"https://top.cocoloop.cn{src}"
                return src
        except Exception as e:
            print(f"Error fetching detail page: {e}")
        
        return None
    
    def crawl(self, fetch_images: bool = False) -> list[ModelInfo]:
        print(f"Fetching {self.BASE_URL}...")
        html = self.fetch_page()
        
        print("Parsing models...")
        models = self.parse_models(html)
        print(f"Found {len(models)} models")
        
        if fetch_images:
            print("Fetching model images (this may take a while)...")
            for i, model in enumerate(models, 1):
                if model.detail_url:
                    print(f"  [{i}/{len(models)}] {model.name}")
                    model.image_url = self.fetch_detail_image(model.detail_url)
        
        return models
    
    def save_to_json(self, models: list[ModelInfo], output_path: str):
        data = [asdict(m) for m in models]
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(models)} models to {output_path}")
    
    def close(self):
        self.client.close()


def main():
    crawler = ModelRankCrawler()
    
    try:
        models = crawler.crawl(fetch_images=False)
        
        crawler.save_to_json(models, "output/models.json")
        
        print("\nTop 10 Models:")
        for m in models[:10]:
            badge = " [开源]" if m.is_open_source else ""
            trend = f" ({'↑' if m.trend_direction == 'up' else '↓'}{m.trend_value})" if m.trend_value else ""
            print(f"  {m.rank}. {m.name}{badge} - Score: {m.score}{trend}")
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
