import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class AppNavigator:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--start-maximized')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        self.base_url = "http://localhost:8000"  # Change this to your app's base URL
        
    def wait_for_element(self, by, value, timeout=10):
        """Helper method to wait for an element to be visible"""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.visibility_of_element_located((by, value)))
    
    def navigate_to_customers(self):
        """Navigate to customers page"""
        self.driver.get(f"{self.base_url}/customers")
        
    def navigate_to_customer_detail(self, index=0):
        """Click on a customer name to view details"""
        customer_links = self.driver.find_elements(By.CSS_SELECTOR, "td:nth-child(2) a")
        if customer_links:
            customer_links[index].click()
    
    def navigate_to_edit_customer(self, index=0):
        """Click edit button for a customer"""
        self.driver.get(f"{self.base_url}/customers")
        edit_buttons = self.driver.find_elements(By.CSS_SELECTOR, "td:nth-child(3) a:nth-child(2)")
        if edit_buttons:
            edit_buttons[index].click()


    def navigate_to_customer_statement(self, index=0, target_date="2023-12-31"):
        """Navigate to a specific customer statement by date"""
        # First navigate to customer detail page
        self.driver.get(f"{self.base_url}/customers")
        
        # Wait for and click customer link
        customer_links = self.driver.find_elements(By.CSS_SELECTOR, "td:nth-child(2) a")
        if customer_links:
            customer_links[index].click()
            
        # Wait for statements to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".divide-y.divide-gray-200"))
        )
        
        # Find the statement with matching date
        statements = self.driver.find_elements(By.CSS_SELECTOR, "li")
        target_statement = None
        
        for statement in statements:
            try:
                date_text = statement.find_element(
                    By.CSS_SELECTOR, 
                    "div.text-sm.text-gray-500"
                ).text.strip()
                
                if target_date in date_text:
                    # Find and click the view button within this statement
                    view_button = statement.find_element(
                        By.CSS_SELECTOR,
                        "button[hx-get^='/statements/view/']"
                    )
                    view_button.click()
                    print(f"Found and clicked statement for date: {target_date}")
                    return True
                    
            except Exception as e:
                print(f"Error processing statement: {e}")
                continue
        
        print(f"No statement found for date: {target_date}")
        return False
    def close_browser(self):
        """Close the browser"""
        self.driver.quit()

def main():
    navigator = AppNavigator()
    try:
        # Example navigation sequence
        # print("Navigating to customers list...")
        # navigator.navigate_to_customers()
        
        # input("Press Enter to view first customer details...")
        # navigator.navigate_to_customer_detail()
        
        # input("Press Enter to edit first customer...")
        # navigator.navigate_to_edit_customer()
        
        input("Press Enter to close the browser...")
        navigator.navigate_to_customer_statement()
        input("Press Enter to close the browser...")
    finally:
        navigator.close_browser()

if __name__ == "__main__":
    main()