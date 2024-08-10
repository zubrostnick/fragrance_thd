'''
Web-scraping code used to scrap initial dataset. Does not work anymore because of changed security constraints on a Fragrantica.com website
'''



from bs4 import BeautifulSoup
import requests
import os
import pickle
import time
import selenium  # programmatically control web browsers
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import Firefox
from splinter import Browser
import random
import scipy.interpolate as si # implementation of mouse move v3
import numpy as np
import pandas as pd
# from seleniumbase import Driver # it can sove captchas given the url (not in browser)
from selenium.webdriver.common.action_chains import ActionChains  # allow low-level interactions
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.by import By
# import re


file_path = 'scraped_data.csv'


def init_undetected_browser():
    """
    Creating Instance of splinter browser with undetected_chromedriver
    """
    options = uc.ChromeOptions()

    # Add any additional options here
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless")

    driver = uc.Chrome(
        options=options,
        service=Service(ChromeDriverManager().install())
    )

    browser = Browser(driver=driver)
    browser.driver.set_window_size(1200, 800)
    return browser

def init_browser():
    """
    Creating Instance of splinter browser with in-built firefox driver
    """
    # service = Service(ChromeDriverManager().install())
    # browser = Browser("chrome", headless=False, incognito=True) #service=service,
    browser = Browser('firefox', headless=False)  # incognito=True
    return browser


def random_pause(min_delay=1.5, max_delay=3.5):
    """
    Function that returns random value within input boundaries;
    default values:
    min_delay=1.5
    max_delay=3.5
    """
    time.sleep(random.uniform(min_delay, max_delay))


def simulate_mouse_movement_simple(driver):
    """Simulating random simple mouse movements"""
    action = ActionChains(driver)
    for _ in range(random.randint(5, 10)):
        x_offset = random.randint(-100, 100)
        y_offset = random.randint(-100, 100)
        action.move_by_offset(x_offset, y_offset).perform()
        random_pause(0.1, 0.5)  # Short random pause between movements


def simulate_human_mouse_movement(driver, start_element, end_element, steps=10):
    """Ця хуйня не працює"""
    action = ActionChains(driver)

    def clamp(value, min_value, max_value):
        return max(min(value, max_value), min_value)

    viewport_width = driver.execute_script("return window.innerWidth")
    viewport_height = driver.execute_script("return window.innerHeight")
    print(viewport_height, viewport_width)

    start_x = clamp(start_element.location['x'] + start_element.size['width'] / 2, 0, viewport_width)
    start_y = clamp(start_element.location['y'] + start_element.size['height'] / 2, 0, viewport_height)
    end_x = clamp(end_element.location['x'] + end_element.size['width'] / 2, 0, viewport_width)
    end_y = clamp(end_element.location['y'] + end_element.size['height'] / 2, 0, viewport_height)

    delta_x = (end_x - start_x) / steps
    delta_y = (end_y - start_y) / steps

    action.move_to_element_with_offset(start_element, start_x, start_y).perform()
    random_pause(0.2, 0.5)

    for i in range(steps):
        offset_x = clamp(delta_x * (i + 1) + random.uniform(-5, 5), 0, viewport_width)
        offset_y = clamp(delta_y * (i + 1) + random.uniform(-5, 5), 0, viewport_height)
        action.move_by_offset(offset_x - start_x, offset_y - start_y).perform()
        start_x, start_y = offset_x, offset_y
        random_pause(0.05, 0.2)

    action.move_to_element(end_element).perform()
    random_pause(0.2, 0.5)


def generate_smooth_path(browser, end_coordinates, viewport_width, viewport_height, num_points=30):
    """
    Create random intermediate control points within the window frame using B-spline interpolation
    returns a path in a form of mouse offset list
    """
    # Obtaining scroll information
    print("\nStart of generating smooth mouse path function")

    scroll_info = browser.driver.execute_script("""
                return {
                    scrollX: window.scrollX,
                    scrollY: window.scrollY,
                };
            """)

    print(f"Browser screen current parameters: {viewport_width}, {viewport_height}; scroll: {scroll_info['scrollX']}, {scroll_info['scrollY']}")
    print("end point (target):", [end_coordinates['x'], end_coordinates['y']])


    intermediate_points = np.random.rand(3, 2) * [viewport_width, viewport_height] # + np.array([scroll_info['scrollX'], scroll_info['scrollY']])

    # Combine start, intermediate, and end points
    points = np.vstack([intermediate_points, np.array([end_coordinates['x'] - scroll_info['scrollX'], end_coordinates['y'] - round(scroll_info['scrollY'])])])

    action = ActionChains(browser.driver)
    action.move_by_offset(points[0][0], points[0][1])
    action.perform()
    print("initial update cursor location: ", browser.driver.execute_script("return {x: window.mouseX, y: window.mouseY};"))


    x = points[:, 0]
    y = points[:, 1]

    t = range(len(points))
    ipl_t = np.linspace(0.0, len(points) - 1, num_points)

    x_tup = si.splrep(t, x, k=3)
    y_tup = si.splrep(t, y, k=3)

    x_list = list(x_tup)
    xl = x.tolist()
    x_list[1] = xl + [0.0, 0.0, 0.0, 0.0]

    y_list = list(y_tup)
    yl = y.tolist()
    y_list[1] = yl + [0.0, 0.0, 0.0, 0.0]

    coordinates = list(zip(si.splev(ipl_t, x_list), si.splev(ipl_t, y_list)))
    coordinates = [(round(x), round(y)) for x, y in coordinates]
    offsets = []
    for i in range(1, len(coordinates)):
        # Calculate the difference between the current and the previous coordinate
        offset_x = coordinates[i][0] - coordinates[i - 1][0]
        offset_y = coordinates[i][1] - coordinates[i - 1][1]

        # Append the offset to the list
        offsets.append((offset_x, offset_y))

    return offsets

def get_interpolated_coordinates():
    """Supplementary test function that returns B-spline interpolation values """
    # Curve base:
    points = [[0, 0], [0, 2], [2, 3], [4, 0], [6, 3], [8, 2], [8, 0]]
    points = np.array(points)

    x = points[:, 0]
    y = points[:, 1]

    t = range(len(points))
    ipl_t = np.linspace(0.0, len(points) - 1, 100)

    x_tup = si.splrep(t, x, k=3)
    y_tup = si.splrep(t, y, k=3)

    x_list = list(x_tup)
    xl = x.tolist()
    x_list[1] = xl + [0.0, 0.0, 0.0, 0.0]

    y_list = list(y_tup)
    yl = y.tolist()
    y_list[1] = yl + [0.0, 0.0, 0.0, 0.0]

    return si.splev(ipl_t, x_list), si.splev(ipl_t, y_list)  # x_i ,y_i interpolate values

def simulate_mouse_movement_v3(driver, start_element, x_i, y_i):
    """Test function for human-like mouse movements  """
    # Inject JavaScript to track the mouse position
    driver.execute_script("""
        window.mouseX = 0;
        window.mouseY = 0;

        document.addEventListener('mousemove', function(e) {
            window.mouseX = e.pageX;  
            window.mouseY = e.pageY;
        });
    """)

    # First, go to your start point or Element:
    # action.move_to_element(start_element)
    print("element location: ", start_element.location)
    print("cursor location: ", driver.execute_script("return {x: window.mouseX, y: window.mouseY};"))
    # action.perform()
    action = ActionChains(driver)
    action.move_by_offset(-5, -5)
    action.perform()
    # print("cursor location: ", driver.execute_script("return {x: window.mouseX, y: window.mouseY};"))
    for mouse_x, mouse_y in zip(x_i, y_i):
        # current_coordinates = browser.driver.execute_script("return {x: window.mouseX, y: window.mouseY};")
        # print("Offset:", mouse_x, mouse_y)
        # print("Starting Location 1: ", browser.driver.execute_script("return {x: window.mouseX, y: window.mouseY};") )
        # print("Projected Location 1: ", current_coordinates['x'] + mouse_x, current_coordinates['y'] + mouse_y)
        # print("Starting Location 2: ", final_x, final_y)
        # final_x += mouse_x
        # final_y += mouse_y
        # print("Projected Location 2: ", final_x, final_y)
        # Here you should reset the ActionChain and the 'jump' wont happen:
        print("Offset: ", mouse_x, mouse_y)
        current_coordinates = driver.execute_script("return {x: window.mouseX, y: window.mouseY};")
        print("Projected Location: ", current_coordinates['x'] + mouse_x, current_coordinates['y'] + mouse_y)
        action = ActionChains(driver)
        action.move_by_offset(mouse_x, mouse_y)
        action.perform()
        print("cursor location: ", driver.execute_script("return {x: window.mouseX, y: window.mouseY};"),
              end='\n\n')

    action.click().perform()


def perform_smooth_mouse_move_v4(browser, offsets):
    """Perform the mouse movement"""
    action = ActionChains(browser.driver)
    for mouse_x, mouse_y in offsets:
        action.move_by_offset(mouse_x, mouse_y)
        action.perform()
    action.click().perform()


def random_slow_scroll(browser):
    """ Function to simulate slow, random scrolling"""
    start_time = time.time()
    scroll_height = browser.execute_script("return document.body.scrollHeight")
    current_position = browser.execute_script("return window.pageYOffset")

    for i in range(random.randint(3,7)):
        scroll_step = random.randint(50, 200)  # Random step size
        current_position += scroll_step
        browser.execute_script(f"window.scrollTo(0, {current_position});")
        random_pause(0.05, 0.15)  # Random pause between steps

        # Check if the end of the page is reached
        if current_position >= scroll_height:
            break
    print("Scroll action took: ", time.time() - start_time)



def crawl_and_parse(year_from, year_to, url='https://www.fragrantica.com/search/'):
    # Search is performed using css selectors (find_by_css) or by Xpath (find_by_xpath)

    # browser = init_browser()
    browser = init_undetected_browser()
    browser.visit(url)
    time.sleep(2)  # to load the page properly

    ### Agree to the privacy notice ###
    try:
        browser.find_by_css('button.css-47sehv').click()
    except Exception as e:
        # if the button is not found (no need to consent) or in case of other unpredictable errors
        print(e, 'An error is in privacy notice consent block')
    time.sleep(2)

    ###  Filtering by release year (for the simplicity of data storing)  ###
    # value: min - 1920, max - 2024

    try:
        browser.find_by_css('input[type="number"]')[0].fill(year_from)
        browser.find_by_css('input[type="number"]')[1].fill(year_to)
    except Exception as e:
        print(e)
        return
    else:
        result1 = browser.find_by_css('input[type="number"]')[0].value
        result2 = browser.find_by_css('input[type="number"]')[0].value
        print(f"Operation successful, new values (first, second): {result1}, {result2} ")

    time.sleep(3)

    ####  CLICK "SHOW MORE RESULTS"  ####
    # (otherwise only 30 can be displayed)

    while True:  # while search is not fully expaneded:
        try:
            button = browser.find_by_xpath(
                '//button[@class="button"and contains(text(),"Show more results")]').first  # xpath expression to locate elements. - XML path query language
            if 'disabled' in button['outerHTML']:
                print('\"Show more results button\" is disabled')
                break

            print(browser.find_by_xpath('//button[@class="button" and contains(text(),"Show more results")]').first.text)
            button.click()
        except Exception as e:
            print(e)
            break
        else:
            print("\"Show more results button\" was pressed successfully")

    html_content = browser.html
    html_soup = BeautifulSoup(html_content, 'lxml')

    perfumes_number = len(html_soup.select('div.cell.card.fr-news-box a'))
    print("Perfumes Number:", perfumes_number)

    # Inject JavaScript to track the mouse position
    browser.driver.execute_script("""
             window.mouseX = 0;
             window.mouseY = 0;

             document.addEventListener('mousemove', function(e) {
                 window.mouseX = e.pageX;  
                 window.mouseY = e.pageY;
             });
         """)

    successful_extractions = 0
    iteration_min = 0
    iteration_max = 0
    parsing_time = 0
    viewport_width = browser.driver.execute_script('return window.innerWidth')
    viewport_height = browser.driver.execute_script('return window.innerHeight')
    page_width = browser.driver.execute_script('document.documentElement.scrollWidth')
    page_height = browser.driver.execute_script('document.documentElement.scrollHeight')

    result_df = pd.DataFrame()
    for perfume_iter in range(perfumes_number):
        start_time = time.time()
        try:
            # Trying to access perfume page:
            while True:
                try:
                    #browser.find_by_css('span[class="link-span"]')[perfume_iter].click()
                    element_to_click = browser.find_by_css('span[class="link-span"]')[perfume_iter]

                    # Scroll to the element
                    browser.execute_script("arguments[0].scrollIntoView(true);", element_to_click._element)
                    time.sleep(1)  # Wait for the scroll to complete

                    # Simulated mouse path
                    offsets = generate_smooth_path(browser, element_to_click._element.location, viewport_width, viewport_height)
                    perform_smooth_mouse_move_v4(browser, offsets)
                    element_to_click.click()
                    print("Moving to the perfume page")
                    break
                except Exception: #selenium.common.exceptions.ElementClickInterceptedException
                    print("Could not click on the element, use scroll")
                    element_to_click = browser.find_by_css('span[class="link-span"]')[perfume_iter]
                    try:
                        # Scrolling to the element
                        browser.execute_script("""
                                    #     arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest'});
                                    # """, element_to_click)
                        time.sleep(1)  # Wait for the scroll to complete

                    except Exception as e:
                        print('Error occurred while scrolling:', e)

            random_pause()  # waiting for the page to load completely

            ### I'm a human verification ###
            html_content = browser.html
            html_soup = BeautifulSoup(html_content, 'lxml')

            while html_soup.title.text == "Just a moment...":
                try:
                    browser.find_by_xpath('//iframe[contains(@src, "challenges.cloudflare.com")]').first.click()
                except Exception as e:
                    print(e, 'Could not complete the captcha ')

            # Additional measures to avoid getting blocked:
            # Random smooth scrolling
            random_slow_scroll(browser)

            # parsing the page
            parse_result = parse_perfume_page(browser.html)
            result_df = pd.concat([result_df, parse_result], ignore_index=True)

            random_pause()
            browser.back()
            random_pause()

        except Exception as e:
            print("Exception while extracting data occured:", e)
            print("Successful Extractions:", successful_extractions)
            print(f"Iteration times: Average - {parsing_time/successful_extractions if successful_extractions != 0 else 0}; Max - {iteration_max}; min - {iteration_min}")
            result_df.to_csv(file_path, index=False)
            return

        successful_extractions += 1
        iteration_elapsed_time = time.time() - start_time
        print(f"Iteration {perfume_iter + 1} took {iteration_elapsed_time}")
        parsing_time += iteration_elapsed_time
        iteration_max = max(iteration_max, iteration_elapsed_time)
        if perfume_iter == 0:
            iteration_min = iteration_max
        else:
            iteration_min = min(iteration_min, iteration_elapsed_time)

    print("Search: success!")
    print(f"Iteration times: Average - {parsing_time/successful_extractions if successful_extractions != 0 else 0}; Max - {iteration_max}; min - {iteration_min}")
    result_df.to_csv(file_path, index=False)

    # enable this code where you need to look into the html code manually
    # with open('crawl_test_page.html', 'w', encoding='utf-8') as file:
    #      file.write(html_soup.prettify())
    return


def fetch_and_parse(url='https://www.fragrantica.com/search/', n_displayed=100):
    """Fetching the webpage content"""

    if os.path.exists(file_path):
        # Load the data from the file
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
    else:
        # If the file doesn't exist, create an empty dictionary
        data = []

    # # When we use a session, it enables us to persist certain parameters such as cookies, headers, and other configuration across requests made using the same session
    # async_session = FuturesSession()
    # #request_session = requests.session()
    # headers_agent = {
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    # }
    # html_content = async_session.get(url, headers=headers_agent)
    # try:
    #     html_content.raise_for_status()  # Raises an HTTPError for bad requests (4xx or 5xx)
    #
    # html_soup = BeautifulSoup(html_content.text, 'lxml')
    #
    # data = []
    # perfume_urls = [url + a['href'] for a in html_soup.select('div.cell.card.fr-news-box a')[:n_displayed]]
    # futures = [async_session.get(perfume_url, headers=headers_agent) for perfume_url in perfume_urls]
    # for future in as_completed(futures):
    #     response = future.result()
    #     response.raise_for_status()  # Raises an HTTPError for bad requests (4xx or 5xx)
    #     data.append(parse_perfume_page(response.text))
    # Fetching the webpage content

    headers_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    # v1
    session = requests.session()  # When you use a session, it enables you to persist certain parameters such as cookies, headers, and other configuration across requests made using the same session

    html_content = session.get(url, headers=headers_agent, timeout=10).text
    # #v2 (VPN)
    # options = Options()
    # options.headless = True
    # driver = webdriver.Firefox(options=options)
    # driver.get(url)
    # html_content = driver.page_source
    # print(html_content)
    # driver.quit()

    html_soup = BeautifulSoup(html_content, 'lxml')
    perfume_urls = [url + a['href'] for a in html_soup.select('div.cell.card.fr-news-box a')[:n_displayed]]
    print(perfume_urls)
    print(html_soup.prettify())
    success_counter = 0
    retries = 0
    retry_delay = 30  # Initial retry delay in seconds
    interval = 6
    for perfume_url in perfume_urls:
        try:
            response = session.get(perfume_url, headers=headers_agent, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad requests (4xx or 5xx)
            data.append(parse_perfume_page(response.text))

        except Exception as e:  # session.exceptions.RequestException
            print(f"Error: {e} on iteration {success_counter}")
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)

            if response.status_code == 429:
                print(f"Received 429 Too Many Requests. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                retries += 1
                continue
        success_counter += 1
        time.sleep(interval)

    return data


def parse_perfume_page(html_content):
    """
    Args:
        html_content:

    Returns:
        dictionary, that contains the values for each of parameters:
        - 'tittle' - tittle of the parfume
        - 'rating' -  of the rating on a 5-point scale
        - 'votes' - total amount of votes': votes
        - 'accords': dictionary, that matches accord name with a percentage of dominance ??
        - 'seasons':  dictionary, that matches season name with a percentage of suitability for given season
        - 'day_night': dictionary, that matches daytime name with a percentage of suitability (day/night occasions)
    #     'notes': notes,
    #     'gender': gender,
    #     'price': price

    """
    soup = BeautifulSoup(html_content, 'lxml')
    # print(soup.prettify())

    # Extracting perfume title
    title = soup.title.text
    perfume_comp = soup.find_all("div", class_="cell small-12")[3].find_all("b")[1].get_text()
    for_gender = soup.find("small").get_text()

    # Extracting rating and votes
    rating_section = soup.find('div', itemprop='aggregateRating')
    rating = rating_section.find('span', itemprop='ratingValue').text if rating_section else None
    votes = rating_section.find('span', itemprop='ratingCount').text if rating_section else None
    num_reviews_element = soup.select_one('meta[itemprop="reviewCount"]')
    num_reviews = num_reviews_element['content'] if num_reviews_element else None
    # Extracting main accords
    accords = {}
    accord_list = soup.find_all('div', {'class': 'accord-bar'})
    for accord in accord_list:
        name = accord.text.strip()
        percentage = accord.get('style', '').split(':')[-1].strip('%;')
        accords[name] = float(percentage)
        # print(name, percentage)

    # Extracting season preferences
    seasons = extract_season(soup)

    # Day/Night preferences
    day_night = extract_day_night(soup)

    # Extracting Longevity, Sillage, Gender, Price to value ratio
    results_long_sill_gend_pv = extract_long_sill_gend_pv(soup)

    # Extracting notes
    top_notes, middle_notes, base_notes = parse_fragrance_notes(soup)

    data = {
        'name': title,
        'company': perfume_comp,
        'for_gender': for_gender,
        'rating': rating,
        'number_votes': votes,
        'main accords': accords,
        'top notes': top_notes,
        'middle notes': middle_notes,
        'base notes': base_notes,
        'seasons': seasons,
        'day_night': day_night,
        'longevity': results_long_sill_gend_pv['LONGEVITY'],
        'sillage': results_long_sill_gend_pv['SILLAGE'],
        'gender_vote': results_long_sill_gend_pv['GENDER'],
        'price value': results_long_sill_gend_pv['PRICE VALUE']
    }
    # Convert the data into a DataFrame
    df_mock = pd.DataFrame(data)

    return df_mock


def extract_season(soup):
    """
    Parse fragrance features - season usage suitability
    @param soup: soup object
    @return: dict which contain the percentage value of season suitability with keys 'winter', 'spring', 'summer', 'fall'
    """
    seasons = {}
    for i in range(4):
        try:
            season = soup.find('div', index=str(i))
            percentage = \
                season.find('div', class_='voting-small-chart-size').find_all('div')[1].get('style', '').split(';')[
                    -3].split(
                    ':')[-1].strip('%;')
            seasons[season.text.strip().lower()] = float(percentage)
        except Exception as e:     #
            print(f"Error extracting season {i}: {e}")
    return seasons


def extract_day_night(soup):
    """
    Parse fragrance features - night/day usage suitability
    @param soup: soup object
    @return: dict wich contain the percentage value of suitability with keys 'day', 'night'
    """
    day_night = {}
    for i in range(2):
        try:
            day_or_night = soup.find('div', index=str(4 + i))
            percentage = \
                day_or_night.find('div', class_='voting-small-chart-size').find_all('div')[1].get('style', '').split(
                    ';')[
                    -3].split(':')[-1].strip('%;')
            day_night[day_or_night.text.strip().lower()] = float(percentage)
        except Exception as e: # AttributeError, IndexError
            print(f"Error extracting day/night {i}: {e}")
    return day_night

def extract_long_sill_gend_pv(soup):
    """ Parse fragrance features like Longevity, Sillage, Gender, Price/Value from the BeautifulSoup object."""
    categories = ['LONGEVITY', 'SILLAGE', 'GENDER', 'PRICE VALUE']
    results = {category: None for category in categories}

    for category in categories:
        category_span = soup.find('span', text=category, attrs={'style': 'font-size: small;'})
        if category_span:
            first_div = category_span.find_parent('div')
            if first_div:
                third_div = first_div.find_next_sibling('div').find_next_sibling('div')
                if third_div:
                    for grid_row in third_div.find_all('div', class_='grid-x grid-margin-x'):
                        category_name_element = grid_row.find('span', class_='vote-button-name')
                        value_element = grid_row.find('span', class_='vote-button-legend')

                        if category_name_element and value_element:
                            try:
                                value = int(value_element.text)
                            except ValueError:  # error handling
                                continue
                            category_name = category_name_element.text

                            results[category][category_name] = value
    return results



def extract_notes(note_div):
    """Extract notes from a note div."""
    notes_list = []
    note_divs = note_div.find_all("div")
    for i in range(2, len(note_divs), 3):
        notes_list.append(note_divs[i].get_text())
    return notes_list


def parse_fragrance_notes(soup):
    """Parse fragrance notes from the BeautifulSoup object."""
    note_style = "display: flex; justify-content: center; text-align: center; flex-flow: wrap; align-items: flex-end; padding: 0.5rem;"
    notes = soup.find_all("div", attrs={"style": note_style})

    top_notes_list = []
    middle_notes_list = []
    base_notes_list = []

    if len(notes) == 3:
        top_notes_list = extract_notes(notes[0])
        middle_notes_list = extract_notes(notes[1])
        base_notes_list = extract_notes(notes[2])
    elif len(notes) == 2:
        top_notes_list = extract_notes(notes[0])
        middle_notes_list = extract_notes(notes[1])
    elif len(notes) == 1:
        middle_notes_list = extract_notes(notes[0])

    return top_notes_list, middle_notes_list, base_notes_list



if __name__ == '__main__':
    crawl_and_parse(1940, 1940)

    # test block:
    # with open('Leather Parfume.html', 'r', encoding="utf8") as html_file:
    #     content = html_file.read()
    #     output = parse_perfume_page(content)
    #     print(output)
    # https://www.fragrantica.com/perfume/Tom-Ford/Ombre-Leather-Parfum-68716.html
