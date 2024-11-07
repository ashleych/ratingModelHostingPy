import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

@pytest.fixture()
def chrome_browser():
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--start-maximized')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    
    yield driver
    driver.quit()

class TestCustomerList:
    BASE_URL = "http://localhost:8000"  # Adjust based on your application URL
    
    def test_customer_list_page_loads(self, chrome_browser):
        """Test that the customer list page loads successfully"""
        # Navigate to the customers page
        chrome_browser.get(f"{self.BASE_URL}/customers")
        
        # Verify the page title is present
        title = chrome_browser.find_element(By.TAG_NAME, "h1")
        assert title.text == "Customers"
        
        # Verify the table headers
        headers = chrome_browser.find_elements(By.TAG_NAME, "th")
        expected_headers = ["CIF Number", "Name", "Actions"]
        actual_headers = [header.text for header in headers]
        assert actual_headers == expected_headers

    def test_customer_table_structure(self, chrome_browser):
        """Test that the customer table has the correct structure"""
        chrome_browser.get(f"{self.BASE_URL}/customers")
        
        # Verify table exists
        table = chrome_browser.find_element(By.TAG_NAME, "table")
        assert table.get_attribute("class") == "min-w-max w-full table-auto"
        
        # Verify table has tbody
        tbody = table.find_element(By.TAG_NAME, "tbody")
        assert tbody.get_attribute("class") == "text-gray-600 dark:text-gray-200 text-sm font-light"

    def test_customer_row_elements(self, chrome_browser):
        """Test that each customer row has the required elements"""
        chrome_browser.get(f"{self.BASE_URL}/customers")
        
        # Get all customer rows
        rows = chrome_browser.find_elements(By.CSS_SELECTOR, "tbody tr")
        
        for row in rows:
            # Verify CIF number cell
            cif_cell = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)")
            assert cif_cell.find_element(By.CLASS_NAME, "font-medium").is_displayed()
            
            # Verify customer name link
            name_cell = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
            name_link = name_cell.find_element(By.TAG_NAME, "a")
            assert "hx-get" in name_link.get_attribute("outerHTML")
            assert "hx-target" in name_link.get_attribute("outerHTML")
            
            # Verify action buttons
            actions_cell = row.find_element(By.CSS_SELECTOR, "td:nth-child(3)")
            view_button = actions_cell.find_element(By.CSS_SELECTOR, "a:nth-child(1)")
            edit_button = actions_cell.find_element(By.CSS_SELECTOR, "a:nth-child(2)")
            assert "hx-get" in view_button.get_attribute("outerHTML")
            assert "hx-get" in edit_button.get_attribute("outerHTML")

    def test_htmx_navigation(self, chrome_browser):
        """Test HTMX navigation when clicking on customer name"""
        chrome_browser.get(f"{self.BASE_URL}/customers")
        
        # Find first customer link
        customer_link = chrome_browser.find_element(By.CSS_SELECTOR, "td:nth-child(2) a")
        customer_name = customer_link.text
        
        # Click the link
        customer_link.click()
        
        # Wait for HTMX request to complete
        WebDriverWait(chrome_browser, 10).until(
            EC.presence_of_element_located((By.ID, "main-content"))
        )
        
        # Verify URL changed
        assert "/customers" in chrome_browser.current_url
        
        # Optional: Verify loading indicator appears and disappears
        try:
            loading = WebDriverWait(chrome_browser, 2).until(
                EC.presence_of_element_located((By.CLASS_NAME, "loading-indicator"))
            )
            WebDriverWait(chrome_browser, 5).until(
                EC.invisibility_of_element(loading)
            )
        except:
            pytest.fail("Loading indicator not found or did not disappear")

    def test_dark_mode_classes(self, chrome_browser):
        """Test that dark mode classes are present"""
        chrome_browser.get(f"{self.BASE_URL}/customers")
        
        # Check table header dark mode classes
        header = chrome_browser.find_element(By.TAG_NAME, "thead")
        assert "dark:bg-gray-700" in header.find_element(By.TAG_NAME, "tr").get_attribute("class")
        
        # Check table body dark mode classes
        rows = chrome_browser.find_elements(By.CSS_SELECTOR, "tbody tr")
        for row in rows:
            assert "dark:border-gray-700" in row.get_attribute("class")
            assert "dark:hover:bg-gray-600" in row.get_attribute("class")

if __name__ == "__main__":
    pytest.main(["-v"])
