import json
import copy
import re
from bs4 import BeautifulSoup
from models.author import AuthorDetails
from models.book import BookDetails
from core.config import BASE_URL

class BookParser:
    @staticmethod
    def parse_author_details(html: str, url: str) -> AuthorDetails:
        soup = BeautifulSoup(html, 'lxml')
        h1 = soup.css.select_one('h1')
        title = h1.get_text(strip=True) if h1 else ""
        
        name = title
        if name.startswith("تحميل كتب "):
            name = name[len("تحميل كتب "):]
        if name.lower().endswith(" pdf"):
            name = name[:-4]
            
        description = ""
        media_body = soup.find('div', class_='media-body')
        if media_body:
            p_desc = media_body.find('p', class_='m-b-5 f-s-18')
            if p_desc:
                p_copy = copy.copy(p_desc)
                for a in p_copy.find_all('a', class_='morelink'):
                    a.decompose()
                description = p_copy.get_text(" ", strip=True)
            else:
                for p in media_body.find_all('p'):
                    txt = p.get_text(strip=True)
                    if txt:
                        description = txt
                        break

        avg_rate = ""
        rate = ""
        if media_body:
            div_stats = media_body.find('div')
            if div_stats:
                spans = [s for s in div_stats.find_all('span', recursive=False) if s.get('title')]
                if len(spans) >= 1: avg_rate = spans[0].get('title')
                if len(spans) >= 2: rate = spans[1].get('title')

        image_url = ""
        media_left = soup.find('div', class_='media-left')
        if media_left:
            img = media_left.find('img')
            if img:
                image_url = img.get('src', '')
                if image_url and image_url.startswith('/'):
                    image_url = BASE_URL + image_url

        return AuthorDetails(
            name=name, url=url, title=title, image=image_url,
            description=description, avg_rate=avg_rate, rate=rate
        )

    @staticmethod
    def parse_book_details(html: str, url: str) -> BookDetails:
        soup = BeautifulSoup(html, 'lxml')
        
        title_el = soup.select_one('h1.kufi-b') or soup.select_one('h1')
        title = title_el.text.strip() if title_el else ''

        rating_el = soup.select_one('.book_rating span')
        ratings = rating_el.text.strip() if rating_el else ''
        if ratings:
            rating_match = re.search(r'[\d,]+', ratings)
            if rating_match:
                ratings = rating_match.group(0)

        qr_el = soup.select_one('img[alt*="Qr Code"]') or soup.select_one('img[src*="qrcode"]')
        qr_code = qr_el['src'] if qr_el and qr_el.has_attr('src') else ''

        target_labels = {
            'المؤلف': 'author', 'مؤلف': 'author_fallback', 'قسم': 'category', 'اللغة': 'language',
            'الصفحات': 'pages', 'حجم الملف': 'file_size', 'حجم الملفات': 'file_size', 
            'نوع الملف': 'file_type', 'نوع الملفات': 'file_type',
            'تاريخ الإنشاء': 'creation_date'
        }
        
        tables = soup.find_all('table')
        search_area = soup
        if tables:
            for t in tables:
                if 'اللغة' in t.text or 'الصفحات' in t.text or 'حجم الملف' in t.text or 'حجم الملفات' in t.text or 'نوع الملف' in t.text or 'نوع الملفات' in t.text:
                    search_area = t
                    break

        extracted_details = {}
        for label_ar, key_en in target_labels.items():
            element = search_area.find(string=lambda text: text and text.strip() == label_ar)
            value = ""
            if element:
                tr = element.find_parent('tr')
                if tr:
                    tds = tr.find_all(['td', 'th'])
                    if len(tds) >= 2:
                        value = tds[-1].get_text(separator=" ", strip=True)
                else:
                    parent = element.parent
                    if parent:
                        parent_div = parent.find_parent('div')
                        full_text = parent_div.get_text(separator=" ", strip=True) if parent_div else parent.get_text(separator=" ", strip=True)
                        if label_ar in full_text:
                            value = full_text.split(label_ar)[-1].strip()
                            value = value.lstrip(':').strip()

            if key_en not in extracted_details or not extracted_details[key_en]:
                extracted_details[key_en] = value.replace('[تعديل]', '').strip()
                
        # Resolve author vs author_fallback
        author_val = extracted_details.get('author', '')
        if not author_val:
            author_val = extracted_details.get('author_fallback', '')
        extracted_details['author'] = author_val
        if 'author_fallback' in extracted_details:
            del extracted_details['author_fallback']

        # Description
        description = ''
        desc_el = soup.select_one('#book_description')
        if desc_el:
            description = desc_el.get_text(separator=' ', strip=True)
        else:
            user_desc_el = soup.select_one('body > div.the_main > div.container > div > div.row.wrapper > div.col-md-9.content > div > div:nth-child(9) > p')
            if user_desc_el:
                description = user_desc_el.get_text(separator=' ', strip=True)
            else:
                for p in soup.select('div.col-md-9.content > div > div > p'):
                    text = p.get_text(separator=' ', strip=True)
                    if len(text) > 50 and "الكتب الإلكترونية هي مكملة" not in text:
                        description = text
                        break

        cover_el = soup.select_one('img.media-object')
        cover_image = cover_el['src'] if cover_el and cover_el.has_attr('src') else ''

        other_tags = []
        tags_elements = soup.select('.tag_box a.tag_btn')
        for tag in tags_elements:
            tag_text = tag.get_text(strip=True)
            if tag_text:
                other_tags.append(tag_text)
        other_tags_str = json.dumps(other_tags, ensure_ascii=False) if other_tags else ''

        # Extract only the numbers from the file size (e.g. from "3.76 ميجا بايت" to "3.76")
        if 'file_size' in extracted_details and extracted_details['file_size']:
            size_match = re.search(r'[\d\.]+', extracted_details['file_size'])
            if size_match:
                extracted_details['file_size'] = size_match.group(0)

        return BookDetails(
            url=url, title=title, ratings=ratings, qr_code=qr_code,
            cover_image=cover_image, description=description, other_tags=other_tags_str,
            **extracted_details
        )
