"""
This script retrieves information about perfumes from the Fragrantica website. It uses Selenium to handle the dynamic 
content of the website and BeautifulSoup to parse the HTML. The script is designed to run in a headless browser for 
efficiency. The information retrieved includes the title, rating, number of votes and reviews, accords, seasonality, 
day/night preference, longevity, sillage, gender, and price value of each perfume. The results are saved in a CSV file.
"""
import time

import pandas as pd
from selenium import webdriver  # selenium is used, since the page is loaded dynamically
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.chrome.options import Options
from requests import Session
from bs4 import BeautifulSoup

# constants
WAIT_TIME_SELENIUM = 2  # feel free to test and adjust this value


def scrape_perfume(perfume_url):
    """
    Scrapes perfume data from a given URL.

    Parameters:
        perfume_url (str): The URL of the perfume page to scrape.

    Returns:
        dict: A dictionary containing the scraped perfume data, including title, rating, number of votes,
              number of reviews, accords, seasonal ratings (winter, spring, summer, fall), day/night ratings,
              longevity, sillage, gender, and price value.
    """
    options = Options()
    options.headless = True

    with webdriver.Chrome(options=options) as driver:
        driver.get(perfume_url)
        time.sleep(WAIT_TIME_SELENIUM)

        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'lxml')

        title = soup.title.text

        rating_element = soup.select_one('span[itemprop="ratingValue"]')

        rating = rating_element.text if rating_element is not None else 'No rating'

        num_votes_element = soup.select_one('span[itemprop="ratingCount"]')
        num_votes = num_votes_element.text if num_votes_element is not None else 'No votes'

        num_reviews_element = soup.select_one('meta[itemprop="reviewCount"]')
        num_reviews = num_reviews_element['content'] if num_reviews_element is not None else 'No reviews'

        accords = [div.text for div in soup.select('div.accord-bar')]
        
        # get the page source after content has loaded (that's the whole point of using Selenium!)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'lxml')

        winter, spring, summer, fall = None, None, None, None
        day, night = None, None

        # extract the seasons
        for i in range(4):
            try:
                season = soup.find('div', index=str(i))
                percentage_div = season.find('div', class_='voting-small-chart-size').find_all('div')[1]
                percentage_style = percentage_div.get('style', '')
                percentage = percentage_style.split(';')[-3].split(':')[-1].strip('%;')
                season_name = season.text.strip()
                if season_name.lower() == 'winter':
                    winter = float(percentage)
                elif season_name.lower() == 'spring':
                    spring = float(percentage)
                elif season_name.lower() == 'summer':
                    summer = float(percentage)
                elif season_name.lower() == 'fall':
                    fall = float(percentage)
            except (AttributeError, IndexError) as e:
                print(f"Error extracting season {i}: {e}")

        # extract day/night
        for i in range(2):
            try:
                day_or_night = soup.find('div', index=str(4 + i))
                percentage_div = day_or_night.find('div', class_='voting-small-chart-size').find_all('div')[1]
                percentage_style = percentage_div.get('style', '')
                percentage = percentage_style.split(';')[-3].split(':')[-1].strip('%;')
                if day_or_night.text.strip().lower() == 'day':
                    day = float(percentage)
                elif day_or_night.text.strip().lower() == 'night':
                    night = float(percentage)
            except (AttributeError, IndexError) as e:
                print(f"Error extracting day/night {i}: {e}")

        # longevity, sillage, gender, price value
        # N.B. These features have similar structure, that's why the for-loop was used
        # TODO: what if the values of several categories are the same?
        categories = ['LONGEVITY', 'SILLAGE', 'GENDER', 'PRICE VALUE']
        results = {category: None for category in categories}

        for category in categories:
            category_span = soup.find('span', text=category, attrs={'style': 'font-size: small;'})
            if category_span:
                first_div = category_span.find_parent('div')
                if first_div:
                    third_div = first_div.find_next_sibling('div').find_next_sibling('div')
                    if third_div:
                        largest_value = 0
                        largest_category = None
                        for grid_row in third_div.find_all('div', class_='grid-x grid-margin-x'):
                            category_name_element = grid_row.find('span', class_='vote-button-name')
                            value_element = grid_row.find('span', class_='vote-button-legend')

                            if category_name_element and value_element:
                                try:
                                    value = int(value_element.text)
                                except ValueError:  # error handling
                                    continue
                                category_name = category_name_element.text

                                if value > largest_value:
                                    largest_category = category_name
                                    largest_value = value
                        results[category] = largest_category
        
        perfume_data = {
            'Title': title,
            'Rating': rating,
            'Number of votes': num_votes,
            'Number of reviews': num_reviews,
            'Accords': ", ".join(accords),
            'Winter': winter,
            'Spring': spring,
            'Summer': summer,
            'Fall': fall,
            'Day': day,
            'Night': night,
            'Longevity': results['LONGEVITY'],
            'Sillage': results['SILLAGE'],
            'Gender': results['GENDER'],
            'Price value': results['PRICE VALUE']
        }
        
        return perfume_data


def scrape_fragrantica(main_url='https://www.fragrantica.com/search/', headers={'User-Agent': 'Mozilla/5.0'}, max_workers=5, n_displayed=3):
    """
    Scrapes Fragrantica website to retrieve information about perfumes.

    Parameters:
        main_url (str, optional): The main URL of the Fragrantica website. Defaults to 'https://www.fragrantica.com/search/'.
        headers (dict, optional): The headers to be used in the HTTP request. Defaults to {'User-Agent': 'Mozilla/5.0'}.
        max_workers (int, optional): The maximum number of worker threads to use for concurrent execution. Defaults to 5.
        n_displayed (int, optional): The number of perfume URLs to be displayed. Defaults to 3.

    Returns:
        list: A list of dictionaries containing information about the scraped perfumes.
    """
    with Session() as session:
        session.headers.update(headers)
        response = session.get(main_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        perfume_urls = [main_url + a['href'] for a in soup.select('div.cell.card.fr-news-box a')[:n_displayed]]
    
    with ThreadPoolExecutor(max_workers) as executor:
        perfumes_list = list(executor.map(scrape_perfume, perfume_urls))
    
    return perfumes_list


if __name__ == '__main__':
    start_time = time.time()
    res = scrape_fragrantica(n_displayed=10)
    end_time = time.time()
    print(f"Execution time of the function is: {end_time - start_time} seconds")

    df = pd.DataFrame(res)
    df.to_csv('data/perfumes.csv', index=False)