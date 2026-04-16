import requests
import re
from bs4 import BeautifulSoup
from .base_fetcher import BaseFetcher

class SDFetcher(BaseFetcher):
    def fetch(self):
        # 1? ??: ?? ?? ???
        url = 'https://finance.naver.com/sise/sise_index.naver?code=KOSPI'
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(url, headers=headers)
            res.encoding = 'euc-kr'
            if res.status_code == 200:
                # ???? ??? ???? ?? ??????? ?? ?? ??
                text = res.text
                # '?? -123?' ??? ?? ?????
                indiv = re.findall(r'??.*?([+-]?[0-9,]+)?', text)
                foreign = re.findall(r'???.*?([+-]?[0-9,]+)?', text)
                if indiv and foreign:
                    return {
                        'individual': int(indiv[0].replace(',', '')),
                        'foreign': int(foreign[0].replace(',', ''))
                    }
        except:
            pass
        return {}
