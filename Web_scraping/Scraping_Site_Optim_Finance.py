import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, urlparse
import csv
from typing import Dict, List, Any

class OptimFinanceScraper:
    def __init__(self, base_url: str = "https://www.optim-finance.com/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.scraped_data = {}
        
    def get_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a web page"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract text using CSS selector"""
        try:
            elements = soup.select(selector)
            if elements:
                return elements[0].get_text(strip=True)
            return ""
        except Exception as e:
            print(f"Error with selector '{selector}': {e}")
            return ""
    
    def extract_multiple_text(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """Extract multiple text elements using CSS selector"""
        try:
            elements = soup.select(selector)
            return [elem.get_text(strip=True) for elem in elements]
        except Exception as e:
            print(f"Error with selector '{selector}': {e}")
            return []
    
    def extract_links(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """Extract links using CSS selector"""
        try:
            elements = soup.select(selector)
            links = []
            for elem in elements:
                href = elem.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    links.append(full_url)
            return links
        except Exception as e:
            print(f"Error extracting links with selector '{selector}': {e}")
            return []
    
    def extract_images(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """Extract image URLs using CSS selector"""
        try:
            elements = soup.select(selector)
            images = []
            for elem in elements:
                src = elem.get('src') or elem.get('data-src')
                if src:
                    full_url = urljoin(self.base_url, src)
                    images.append(full_url)
            return images
        except Exception as e:
            print(f"Error extracting images with selector '{selector}': {e}")
            return []
    
    def scrape_homepage(self) -> Dict[str, Any]:
        """Scrape the homepage data"""
        print("Scraping homepage...")
        soup = self.get_page(self.base_url)
        if not soup:
            return {}
        
        data = {
            'a_propos_societe': self.extract_text(soup, 'div.ps-lg-0'),
            'description_1': self.extract_text(soup, 'div.process-section__card'),
            'description_2': self.extract_text(soup, 'div:nth-of-type(2) div.process-section__card'),
            'description_3': self.extract_text(soup, 'div:nth-of-type(3) div.process-section__card'),
            'description_4': self.extract_text(soup, 'p.px-10'),
            'valeurs_description': self.extract_multiple_text(soup, '.valeurs-section div.row'),
            'solutions_acceuil': self.extract_text(soup, 'div.col-lg-7'),
            'trusted_by': self.extract_text(soup, '.partenaires-section--logos div.owl-stage'),
            'contact_details': self.extract_text(soup, 'div.col-lg-6:nth-of-type(3)'),
        }
        
        # Extract navigation links
        nav_links = {
            'missions': self.extract_links(soup, 'li:nth-of-type(2) a.nav-link'),
            'solutions_fin': self.extract_links(soup, 'li:nth-of-type(3) a.nav-link'),
            'portage_salarial': self.extract_links(soup, 'li:nth-of-type(4) a.nav-link'),
            'auto_entreprise': self.extract_links(soup, 'li:nth-of-type(5) a.nav-link'),
            'gestion_societe': self.extract_links(soup, 'li:nth-of-type(6) a'),
            'simulations': self.extract_links(soup, 'li:nth-of-type(7) a'),
            'documentation': self.extract_links(soup, 'a.pe-3'),
            'conditions_utilisation': self.extract_links(soup, '.gap-4 li:nth-of-type(1) a'),
            'politique_confidentialite': self.extract_links(soup, '.gap-4 li:nth-of-type(2) a'),
        }
        
        data['navigation_links'] = nav_links
        return data
    
    def scrape_missions_page(self, url: str) -> Dict[str, Any]:
        """Scrape missions page"""
        print(f"Scraping missions page: {url}")
        soup = self.get_page(url)
        if not soup:
            return {}
        
        return {
            'mission_1': self.extract_text(soup, 'div.w-75'),
            'mission_2': self.extract_text(soup, '.mission-section div.row'),
        }
    
    def scrape_solutions_page(self, url: str) -> Dict[str, Any]:
        """Scrape solutions financières page"""
        print(f"Scraping solutions page: {url}")
        soup = self.get_page(url)
        if not soup:
            return {}
        
        return {
            'solutions_text': self.extract_text(soup, 'div.gap-3.d-flex'),
            'description': self.extract_text(soup, 'div.pb-5'),
            'solutions_text_1': self.extract_text(soup, '.solutions-financieres-section div.heading-style1'),
            'portage_salarial': self.extract_text(soup, 'div.col-lg-4:nth-of-type(1) div.solutions-financieres-section__card'),
            'auto_entreprise': self.extract_text(soup, 'div.bg-white.solutions-financieres-section__card'),
            'gestion_societe': self.extract_text(soup, 'div:nth-of-type(3) div.solutions-financieres-section__card'),
        }
    
    def scrape_portage_salarial_page(self, url: str) -> Dict[str, Any]:
        """Scrape portage salarial page"""
        print(f"Scraping portage salarial page: {url}")
        soup = self.get_page(url)
        if not soup:
            return {}
        
        return {
            'description': self.extract_text(soup, 'div.heading-style3'),
            'definition': self.extract_text(soup, '.step-1 div.col-lg-8'),
            'pour_vous': self.extract_text(soup, 'div.flex-row-reverse'),
            'offre': self.extract_text(soup, '.step-3 div.row'),
            'frais': self.extract_text(soup, '.step-4 div.row'),
            'simulation_cta': self.extract_text(soup, '.step-5 div.pt-5'),
        }
    
    def scrape_auto_entreprise_page(self, url: str) -> Dict[str, Any]:
        """Scrape auto-entreprise page"""
        print(f"Scraping auto-entreprise page: {url}")
        soup = self.get_page(url)
        if not soup:
            return {}
        
        return {
            'description': self.extract_text(soup, 'div.heading-style3'),
            'definition': self.extract_text(soup, '.step-1 div.col-lg-8'),
            'pour_vous': self.extract_text(soup, 'div.pe-lg-5'),
            'caracteristiques': self.extract_text(soup, '.step-4 div.row'),
            'simulation_cta': self.extract_text(soup, '.step-5 div.pt-5'),
        }
    
    def scrape_gestion_societe_page(self, url: str) -> Dict[str, Any]:
        """Scrape gestion société page"""
        print(f"Scraping gestion société page: {url}")
        soup = self.get_page(url)
        if not soup:
            return {}
        
        return {
            'description': self.extract_text(soup, 'div.heading-style3'),
            'presentation': self.extract_text(soup, '.flex-lg-row div.col-lg-6'),
            'expert': self.extract_text(soup, 'div.ps-lg-5'),
            'definition_1': self.extract_text(soup, 'div.mt-lg-0'),
            'services': self.extract_text(soup, 'section.services-section'),
            'simulation_cta': self.extract_text(soup, '.simuler-section div.row'),
        }
    
    def scrape_documentation_page(self, url: str) -> Dict[str, Any]:
        """Scrape documentation page"""
        print(f"Scraping documentation page: {url}")
        soup = self.get_page(url)
        if not soup:
            return {}
        
        data = {
            'search_section': self.extract_text(soup, 'div.w-75'),
            'description_totale': self.extract_text(soup, '.documentation-section div.row'),
        }
        
        # Extract FAQ link and content
        faq_links = self.extract_links(soup, 'a.text-danger.fs-24px')
        if faq_links:
            faq_soup = self.get_page(faq_links[0])
            if faq_soup:
                data['faq_content'] = self.extract_text(faq_soup, 'div.documentation-section--result')
        
        return data
    
    def scrape_legal_page(self, url: str, page_type: str) -> Dict[str, Any]:
        """Scrape legal pages (conditions d'utilisation, politique de confidentialité)"""
        print(f"Scraping {page_type} page: {url}")
        soup = self.get_page(url)
        if not soup:
            return {}
        
        return {
            'content': self.extract_text(soup, 'div.documentation-section--result'),
            'page_type': page_type,
            'url': url
        }
        """Scrape documentation page"""
        print(f"Scraping documentation page: {url}")
        soup = self.get_page(url)
        if not soup:
            return {}
        
        data = {
            'search_section': self.extract_text(soup, 'div.w-75'),
            'description_totale': self.extract_text(soup, '.documentation-section div.row'),
        }
        
        # Extract FAQ link and content
        faq_links = self.extract_links(soup, 'a.text-danger.fs-24px')
        if faq_links:
            faq_soup = self.get_page(faq_links[0])
            if faq_soup:
                data['faq_content'] = self.extract_text(faq_soup, 'div.documentation-section--result')
        
        return data
    
    def scrape_all(self) -> Dict[str, Any]:
        """Scrape all pages based on the sitemap configuration"""
        all_data = {}
        
        # Start with homepage
        homepage_data = self.scrape_homepage()
        all_data['homepage'] = homepage_data
        
        # Extract URLs from navigation
        nav_links = homepage_data.get('navigation_links', {})
        
        # Scrape each main section
        if nav_links.get('missions'):
            all_data['missions'] = self.scrape_missions_page(nav_links['missions'][0])
            time.sleep(1)  # Be respectful to the server
        
        if nav_links.get('solutions_fin'):
            all_data['solutions_financieres'] = self.scrape_solutions_page(nav_links['solutions_fin'][0])
            time.sleep(1)
        
        if nav_links.get('portage_salarial'):
            all_data['portage_salarial'] = self.scrape_portage_salarial_page(nav_links['portage_salarial'][0])
            time.sleep(1)
        
        if nav_links.get('auto_entreprise'):
            all_data['auto_entreprise'] = self.scrape_auto_entreprise_page(nav_links['auto_entreprise'][0])
            time.sleep(1)
        
        if nav_links.get('gestion_societe'):
            all_data['gestion_societe'] = self.scrape_gestion_societe_page(nav_links['gestion_societe'][0])
            time.sleep(1)
        
        if nav_links.get('documentation'):
            all_data['documentation'] = self.scrape_documentation_page(nav_links['documentation'][0])
            time.sleep(1)
        
        # Scrape legal pages
        if nav_links.get('conditions_utilisation'):
            all_data['conditions_utilisation'] = self.scrape_legal_page(
                nav_links['conditions_utilisation'][0], 'Conditions d\'utilisation'
            )
            time.sleep(1)
        
        if nav_links.get('politique_confidentialite'):
            all_data['politique_confidentialite'] = self.scrape_legal_page(
                nav_links['politique_confidentialite'][0], 'Politique de confidentialité'
            )
            time.sleep(1)
        
        return all_data
    
    def save_to_json(self, data: Dict[str, Any], filename: str = 'optim_finance_data.json'):
        """Save scraped data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
    
    def save_to_csv(self, data: Dict[str, Any], filename: str = 'optim_finance_data.csv'):
        """Save scraped data to CSV file (flattened)"""
        flattened_data = []
        
        def flatten_dict(d, parent_key='', sep='_'):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                        else:
                            items.append((f"{new_key}_{i}", item))
                else:
                    items.append((new_key, v))
            return dict(items)
        
        flat_data = flatten_dict(data)
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Key', 'Value'])
            for key, value in flat_data.items():
                writer.writerow([key, str(value)])
        
        print(f"Data saved to {filename}")

# Usage example
if __name__ == "__main__":
    scraper = OptimFinanceScraper()
    
    # Scrape all data
    print("Starting web scraping...")
    scraped_data = scraper.scrape_all()
    
    # Save results
    scraper.save_to_json(scraped_data)
    scraper.save_to_csv(scraped_data)
    
    # Print summary
    print(f"\nScraping completed!")
    print(f"Total sections scraped: {len(scraped_data)}")
    for section, content in scraped_data.items():
        if isinstance(content, dict):
            print(f"- {section}: {len(content)} items")
        else:
            print(f"- {section}: {type(content)}")