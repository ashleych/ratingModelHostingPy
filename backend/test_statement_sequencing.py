# import unittest
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from datetime import datetime
# import time
# import pytest  
# from selenium import webdriver  
# from selenium.webdriver.chrome.service import Service as ChromeService  
# from webdriver_manager.chrome import ChromeDriverManager  
  
  
# @pytest.fixture()  
# def chrome_browser():  
#     driver = webdriver.Chrome()  
  
#     # Use this line instead of the prev if you wish to download the ChromeDriver binary on the fly  
#     # driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))  
      
#     driver.implicitly_wait(10)  
#     # Yield the WebDriver instance  
#     yield driver  
#     # Close the WebDriver instance  
#     driver.quit()
# def test_title(chrome_browser):  
#     """  
#     Test the title of the Python.org website  
#     """  
#     chrome_browser.get("https://www.python.org")  
#     assert chrome_browser.title == "Welcome to Python.org"
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import time

@pytest.fixture()
def chrome_browser():
    # Set up Chrome options
    chrome_options = Options()
    
    # Remove or comment out headless mode to see the browser
    # chrome_options.add_argument('--headless')  # This makes the browser invisible
    
    # These are still good to keep for stability
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Optional: Add some window size settings
    chrome_options.add_argument('--start-maximized')  # Start with maximized window
    # Or set specific dimensions:
    # chrome_options.add_argument('--window-size=1920,1080')
    
    service = Service(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )
    
    driver.implicitly_wait(10)
    yield driver
    driver.quit()
# @pytest.fixture()
# def chrome_browser():
#     # Set up Chrome options
#     chrome_options = Options()
#     chrome_options.add_argument('--no-sandbox')
#     chrome_options.add_argument('--disable-dev-shm-usage')
#     # chrome_options.add_argument('--headless')  # Uncomment if you want headless mode
    
#     # Create service using ChromeDriverManager
#     service = Service(ChromeDriverManager().install())
    
#     # Initialize driver with service and options
#     driver = webdriver.Chrome(
#         service=service,
#         options=chrome_options
#     )
    
#     driver.implicitly_wait(10)
#     yield driver
#     driver.quit()

def test_title(chrome_browser):
    """
    Test the title of the Python.org website
    """
    chrome_browser.get("https://www.python.org")
    time.sleep(2)  # Add a 2-second delay to see what's happening

    assert chrome_browser.title == "Welcome to Python.org"
