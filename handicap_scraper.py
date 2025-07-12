#!/usr/bin/env python3
import urllib.request
import urllib.parse
import html.parser
import html
import os
import re
from datetime import datetime
import locale
import xml.etree.ElementTree as ET

class HandicapArticleScraper:
    def __init__(self):
        self.articles = []
        # Try to set French locale for date formatting
        try:
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        except:
            # Fallback if French locale not available
            pass
    
    def fetch_rss(self, url):
        """Fetch RSS feed content"""
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
            })
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            print(f"Error fetching RSS feed: {e}")
            return None
    
    def extract_date_from_link(self, link):
        """Extract date from article link"""
        try:
            # Try to fetch the actual article page to get the real date
            req = urllib.request.Request(link, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                
                # Look for date patterns in the content
                # Pattern like "11 juillet 2025" in the article
                date_patterns = [
                    r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})',
                    r'(\d{1,2})/(\d{1,2})/(\d{4})',
                    r'(\d{4})-(\d{1,2})-(\d{1,2})'
                ]
                
                months = {
                    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
                    'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
                }
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        match = matches[0]
                        if len(match) == 3:
                            if match[1].lower() in months:  # French month name
                                day, month_name, year = match
                                month = months[match[1].lower()]
                                return datetime(int(year), month, int(day))
                            else:  # Numeric format
                                try:
                                    return datetime(int(match[2]), int(match[1]), int(match[0]))
                                except:
                                    continue
        except Exception as e:
            print(f"Could not extract date from {link}: {e}")
        
        # Fallback to current date
        return datetime.now()

    def parse_rss_articles(self, rss_content):
        """Parse articles from RSS feed"""
        parsed_articles = []
        
        try:
            # Parse XML
            root = ET.fromstring(rss_content)
            
            # Find all item elements
            items = root.findall('.//item')
            
            print(f"Found {len(items)} items in RSS feed")
            
            for item in items:
                try:
                    # Extract title
                    title_elem = item.find('title')
                    title = title_elem.text.strip() if title_elem is not None else "No title"
                    
                    # Extract link
                    link_elem = item.find('link')
                    link = link_elem.text.strip() if link_elem is not None else ""
                    
                    # Extract description/content
                    description_elem = item.find('description')
                    content = ""
                    if description_elem is not None:
                        content_raw = description_elem.text or ""
                        # Remove HTML tags
                        content = re.sub(r'<[^>]+>', '', content_raw)
                        content = html.unescape(content).strip()
                        # Remove excessive whitespace
                        content = re.sub(r'\s+', ' ', content)
                    
                    # Extract publication date
                    pubdate_elem = item.find('pubDate')
                    article_date = datetime.now()  # Default fallback
                    
                    if pubdate_elem is not None:
                        try:
                            # Parse RSS date format (RFC 2822)
                            # Example: "Mon, 10 Jul 2025 14:30:00 GMT" or "Mon, 10 Jul 2025 14:30:00 +0000"
                            date_str = pubdate_elem.text.strip()
                            # Remove timezone info (GMT, UTC, +0000, etc.)
                            date_str = re.sub(r'\s*(GMT|UTC|[+-]\d{4})$', '', date_str)
                            article_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S")
                        except Exception as e:
                            print(f"Could not parse date '{pubdate_elem.text}': {e}")
                            # Try to extract date from link as fallback
                            article_date = self.extract_date_from_link(link)
                    
                    # Extract source from URL
                    source = self.extract_source_from_url(link)
                    
                    # Clean title and content from invisible characters
                    clean_title = html.unescape(title).replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
                    clean_content = content.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
                    
                    # Create article object
                    article = {
                        'title': clean_title,
                        'link': link,
                        'content': clean_content,
                        'date': article_date,
                        'date_text': self.format_french_date(article_date),
                        'source': source
                    }
                    
                    parsed_articles.append(article)
                    print(f"Parsed: {title} - {article['date_text']}")
                    
                except Exception as e:
                    print(f"Error parsing RSS item: {e}")
                    continue
            
        except ET.ParseError as e:
            print(f"Error parsing RSS XML: {e}")
        except Exception as e:
            print(f"Error processing RSS feed: {e}")
        
        # Sort articles by date (newest first)
        parsed_articles.sort(key=lambda x: x['date'], reverse=True)
        
        return parsed_articles
    
    def extract_source_from_url(self, url):
        """Extract source name from URL"""
        try:
            # Parse the URL to get the domain
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Map common domains to readable source names
            source_mapping = {
                'handicap.fr': 'handicap.fr',
                'informations.handicap.fr': 'handicap.fr',
                'faire-face.fr': 'faire-face.fr',
                'handinova.fr': 'handinova.fr',
                'handicap.live': 'handicap.live',
                'yanous.com': 'yanous.com'
            }
            
            # Return mapped source or domain as fallback
            return source_mapping.get(domain, domain)
            
        except Exception as e:
            return "source inconnue"
    
    def format_french_date(self, dt):
        """Format date in French format"""
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                  'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
        
        day_name = days[dt.weekday()]
        month_name = months[dt.month - 1]
        
        return f"{day_name} {dt.day} {month_name} {dt.year}"
    
    
    def save_summary_only(self, articles):
        """Create only the summary HTML file"""
        # Create directory (for GitHub Pages, we'll put files at root)
        os.makedirs('archives', exist_ok=True)
        
        # Create summary HTML file
        self.create_summary_html(articles)
        
        # Create summary text file
        self.create_summary_text(articles)
        
        return articles
    
    def create_summary_html(self, articles):
        """Create a summary HTML file with all articles"""
        # Get today's date in French format for the title
        today = datetime.now()
        today_french = self.format_french_date(today)
        
        summary_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Revue de presse] {today_french}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 20px auto;
            padding: 15px;
            line-height: 1.4;
            color: #333;
            background-color: #f8f9fa;
        }}
        h1 {{
            color: #3498db;
            text-align: center;
            padding-bottom: 8px;
            cursor: pointer;
            margin-bottom: 15px;
        }}
        h1:hover {{
            color: #2980b9;
        }}
        .article-item {{
            background: white;
            padding: 12px;
            margin: 8px 0;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .article-title {{
            color: #3498db;
            font-size: 1.1em;
            font-weight: bold;
            margin-bottom: 5px;
            cursor: pointer;
        }}
        .article-title:hover {{
            color: #2980b9;
        }}
        .article-date {{
            color: #7f8c8d;
            font-style: italic;
            font-size: 0.85em;
            display: inline;
            margin-left: 5px;
        }}
        .article-link {{
            color: #3498db;
            text-decoration: none;
        }}
        .article-link:hover {{
            text-decoration: underline;
        }}
        .continue-link {{
            color: #3498db;
            text-decoration: none;
        }}
        .continue-link:hover {{
            text-decoration: underline;
        }}
        p {{
            margin: 0;
            color: #333;
        }}
    </style>
</head>
<body>
    <h1 onclick="window.location.reload()">[Revue de presse] {today_french}</h1>
"""
        
        for article in articles:
            french_date = self.format_french_date(article['date']).lower()
            content_preview = html.escape(article['content'][:200])
            source = article.get('source', 'source inconnue')
            
            summary_content += f"""
    <div class="article-item">
        <div class="article-title" onclick="window.open('{html.escape(article['link'])}', '_blank')">{html.escape(article['title'])}</div>
        <p>{content_preview}{'<a href="' + html.escape(article['link']) + '" class="continue-link" target="_blank">...</a>' if len(article['content']) > 200 else ''}<span class="article-date">({source} / {french_date})</span></p>
    </div>
"""
        
        summary_content += """
</body>
</html>"""
        
        # Create filename with format yyyy-mm-dd (fichier du jour écrasé)
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}.html"
        filepath = os.path.join('archives', filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            print(f"Summary file created: archives/{filename}")

            # Écrase aussi index.html à la racine
            with open('index.html', 'w', encoding='utf-8') as f_index:
                f_index.write(summary_content)
            print("index.html écrasé avec le résumé du jour")
        except Exception as e:
            print(f"Error creating summary file: {e}")
    
    def create_summary_text(self, articles):
        """Create a summary text file with all articles"""
        # Get today's date in French format for the title
        today = datetime.now()
        today_french = self.format_french_date(today)
        
        summary_content = f"Revue de presse / {today_french}\n\n"
        
        for article in articles:
            french_date = self.format_french_date(article['date']).lower()
            source = article.get('source', 'source inconnue')
            content_preview = article['content'][:200]
            
            # Add article title with #
            summary_content += f"# {article['title']}\n"
            
            # Add article content preview (same as HTML)
            summary_content += f"{content_preview}"
            if len(article['content']) > 200:
                summary_content += "..."
            summary_content += "\n"
            
            # Add source link on new line
            summary_content += f"{article['link']}\n"
            
            # Add date only without parentheses
            summary_content += f"{french_date}\n\n"
        
        # Create filename with format yyyy-mm-dd (fichier du jour écrasé)
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}.txt"
        filepath = os.path.join('archives', filename)
        
        try:
            # Créer le fichier txt dans archives
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            print(f"Text summary file created: archives/{filename}")

            # Créer le fichier txt.html à la racine
            html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Revue de presse] {today_french}</title>
    <style>
        body {{
            font-family: monospace;
            white-space: pre-wrap;
            max-width: 1000px;
            margin: 20px auto;
            padding: 15px;
            line-height: 1.4;
        }}
    </style>
</head>
<body>
{summary_content}
</body>
</html>"""

        with open('txt.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("txt.html écrasé avec le résumé du jour au format texte")
        except Exception as e:
            print(f"Error creating text summary files: {e}")
    
    def create_index_page(self):
        """Create an index page listing all available press reviews"""
        import glob
        
        # Get all HTML files in the directory
        html_files = glob.glob('archives/*.html')
        html_files = [f for f in html_files if not f.endswith('index.html')]
        html_files.sort(reverse=True)  # Most recent first
        
        # Get all TXT files
        txt_files = glob.glob('archives/*.txt')
        txt_files.sort(reverse=True)
        
        index_content = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archives - Revue de presse Handicap</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }
        h1 {
            color: #3498db;
            text-align: center;
            margin-bottom: 30px;
        }
        .file-list {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .file-item:last-child {
            border-bottom: none;
        }
        .file-date {
            font-weight: bold;
            color: #2c3e50;
        }
        .file-links {
            display: flex;
            gap: 10px;
        }
        .file-link {
            color: #3498db;
            text-decoration: none;
            padding: 5px 10px;
            border: 1px solid #3498db;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .file-link:hover {
            background-color: #3498db;
            color: white;
        }
        .last-update {
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>📰 Archives - Revue de presse Handicap</h1>
    
    <div class="file-list">
        <h2>Revues de presse disponibles</h2>
"""
        
        # Group files by date
        dates = set()
        for html_file in html_files:
            filename = os.path.basename(html_file)
            if filename.count('-') >= 2:  # Format: YYYY-MM-DD.html
                date_part = filename.replace('.html', '')
                dates.add(date_part)
        
        for txt_file in txt_files:
            filename = os.path.basename(txt_file)
            if filename.count('-') >= 2:  # Format: YYYY-MM-DD.txt
                date_part = filename.replace('.txt', '')
                dates.add(date_part)
        
        dates = sorted(dates, reverse=True)
        
        for date_str in dates:
            try:
                # Parse date for display
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                display_date = self.format_french_date(date_obj)
                
                html_file = f"{date_str}.html"
                txt_file = f"{date_str}.txt"
                
                html_exists = os.path.exists(f"archives/{html_file}")
                txt_exists = os.path.exists(f"archives/{txt_file}")
                
                if html_exists or txt_exists:
                    index_content += f"""
        <div class="file-item">
            <div class="file-date">{display_date}</div>
            <div class="file-links">
"""
                    if html_exists:
                        index_content += f'                <a href="archives/{html_file}" class="file-link">📄 HTML</a>\n'
                    if txt_exists:
                        index_content += f'                <a href="archives/{txt_file}" class="file-link">📝 Texte</a>\n'
                    
                    index_content += """            </div>
        </div>"""
            except ValueError:
                continue
        
        # Add last update time
        now = datetime.now()
        last_update = self.format_french_date(now)
        
        index_content += f"""
    </div>
    
    <div class="last-update">
        Dernière mise à jour: {last_update} à {now.strftime('%H:%M')}
    </div>
</body>
</html>"""
        
        # Write index file at root for GitHub Pages
        try:
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(index_content)
        except Exception as e:
            print(f"Error creating index page: {e}")
    
    def create_redirect_pages(self):
        """Create redirect pages to latest files"""
        import glob
        
        # Get the most recent HTML and TXT files
        html_files = glob.glob('archives/*.html')
        html_files.sort(reverse=True)  # Most recent first
        
        txt_files = glob.glob('archives/*.txt')
        txt_files.sort(reverse=True)  # Most recent first
        
        if html_files:
            latest_html = os.path.basename(html_files[0])
            
            # Create root index.html that redirects to latest HTML
            redirect_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=archives/{latest_html}">
    <title>Redirection vers la revue de presse</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            background-color: #f8f9fa;
        }}
        .loading {{
            color: #3498db;
            font-size: 1.2em;
        }}
        .manual-link {{
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="loading">
        📰 Redirection vers la revue de presse du jour...
    </div>
    <p>
        Si la redirection ne fonctionne pas, 
        <a href="archives/{latest_html}" class="manual-link">cliquez ici</a>
    </p>
</body>
</html>"""
            
            try:
                with open('index.html', 'w', encoding='utf-8') as f:
                    f.write(redirect_html)
                print(f"Redirect page created: index.html → archives/{latest_html}")
            except Exception as e:
                print(f"Error creating redirect page: {e}")
        
        if txt_files:
            latest_txt = os.path.basename(txt_files[0])
            
            # Create txt.html that redirects to latest TXT
            redirect_txt = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=archives/{latest_txt}">
    <title>Redirection vers le fichier texte</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            background-color: #f8f9fa;
        }}
        .loading {{
            color: #3498db;
            font-size: 1.2em;
        }}
        .manual-link {{
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="loading">
        📝 Redirection vers le fichier texte du jour...
    </div>
    <p>
        Si la redirection ne fonctionne pas, 
        <a href="archives/{latest_txt}" class="manual-link">cliquez ici</a>
    </p>
</body>
</html>"""
            
            try:
                with open('txt.html', 'w', encoding='utf-8') as f:
                    f.write(redirect_txt)
                print(f"Redirect page created: txt.html → archives/{latest_txt}")
            except Exception as e:
                print(f"Error creating txt redirect page: {e}")
    
    def run(self):
        """Main execution method"""
        rss_url = "https://www.inoreader.com/stream/user/1006129458/tag/Handicap__Revue_de_presse"
        
        print("Fetching RSS feed from:", rss_url)
        rss_content = self.fetch_rss(rss_url)
        
        if not rss_content:
            print("Failed to fetch RSS feed")
            return
        
        print("Parsing RSS articles...")
        articles = self.parse_rss_articles(rss_content)
        
        if not articles:
            print("No articles found in RSS feed!")
            return
        
        print(f"Found {len(articles)} articles")
        
        print("Creating summary...")
        self.save_summary_only(articles)
        
        print("Creating index page...")
        self.create_index_page()
        
        print("Creating redirect pages...")
        self.create_redirect_pages()
        
        # Get today's filename for the message
        today = datetime.now()
        html_filename = f"{today.strftime('%Y-%m-%d')}.html"
        txt_filename = f"{today.strftime('%Y-%m-%d')}.txt"
        
        print(f"Successfully processed {len(articles)} articles")
        print(f"HTML summary available at: archives/{html_filename}")
        print(f"Text summary available at: archives/{txt_filename}")
        print(f"Index page updated: index.html")

def main():
    scraper = HandicapArticleScraper()
    scraper.run()

if __name__ == "__main__":
    main()