import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

# Define the selector for the modal backdrop which causes the click interception error
MODAL_BACKDROP_SELECTOR = (By.CLASS_NAME, "modal-two-backdrop")
CONFIRM_BUTTON_SELECTOR = (By.CSS_SELECTOR, ".button-solid-norm:nth-child(2)")

# Constants
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloaded_configs")
TARGET_COUNTRY_NAME = "United States"
MAX_DOWNLOADS_PER_SESSION = 20 # <--- NEW: Maximum downloads before relogin
RELOGIN_DELAY = 120 # Delay in seconds between sessions to cool down the IP

# Create the download directory if it doesn't exist
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
    print(f"Created download directory: {DOWNLOAD_DIR}")


class ProtonVPN:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        
        # --- Optimization for GitHub Actions/Server Environments ---
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        
        # *** Key Configuration: Setting the Download Path in Chrome ***
        prefs = {
            "download.default_directory": DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True 
        }
        self.options.add_experimental_option("prefs", prefs)

        self.driver = None

    def setup(self):
        """Initializes the WebDriver (Chrome) with Headless options."""
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.set_window_size(1936, 1048)
        self.driver.implicitly_wait(10)
        print("WebDriver initialized successfully in Headless mode (Chrome).")

    def teardown(self):
        """Closes the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")
            
    def login(self, username, password):
        try:
            self.driver.get("https://protonvpn.com/")
            time.sleep(2)
            self.driver.find_element(By.XPATH, "//a[contains(@href, 'https://account.protonvpn.com/login')]").click()
            time.sleep(2)
            user_field = self.driver.find_element(By.ID, "username")
            user_field.clear()
            user_field.send_keys(username)
            time.sleep(1)
            self.driver.find_element(By.CSS_SELECTOR, ".button-large").click()
            time.sleep(2)
            pass_field = self.driver.find_element(By.ID, "password")
            pass_field.clear()
            pass_field.send_keys(password)
            time.sleep(1)
            self.driver.find_element(By.CSS_SELECTOR, ".button-large").click()
            time.sleep(5)
            print("Login Successful.")
            return True
        except Exception as e:
            print(f"Error Login: {e}")
            return False

    def navigate_to_downloads(self):
        try:
            downloads_link_selector = (By.CSS_SELECTOR, ".navigation-item:nth-child(7) .text-ellipsis")
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(downloads_link_selector)
            ).click()
            time.sleep(3)
            print("Navigated to Downloads section.")
            return True
        except Exception as e:
            print(f"Error Navigating to Downloads: {e}")
            return False

    def logout(self):
        try:
            self.driver.get("https://account.protonvpn.com/logout") # Direct logout link is faster
            time.sleep(3)
            print("Logout Successful.")
            return True
        except Exception as e:
            # If direct link fails, try clicking
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".p-1").click()
                time.sleep(1)
                self.driver.find_element(By.CSS_SELECTOR, ".mb-4 > .button").click()
                time.sleep(2)
                print("Logout Successful via UI.")
                return True
            except Exception as e:
                print(f"Error Logout: {e}")
                return False

    def process_downloads(self):
        """Processes downloads for the target country with a limit per call."""
        try:
            self.driver.execute_script("window.scrollTo(0,0)")
            time.sleep(2)

            # Click the configuration type tab (e.g., OpenVPN)
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".flex:nth-child(4) > .mr-8:nth-child(3) > .relative").click()
                time.sleep(2)
            except:
                pass

            countries = self.driver.find_elements(By.CSS_SELECTOR, ".mb-6 details")
            print(f"Found {len(countries)} total countries to check.")
            
            download_counter = 0
            all_downloads_finished = True # Assume true until we start downloading

            for country in countries:
                try:
                    country_name_element = country.find_element(By.CSS_SELECTOR, "summary")
                    country_name = country_name_element.text.split('\n')[0].strip()
                    
                    if TARGET_COUNTRY_NAME not in country_name:
                        continue
                    
                    print(f"--- Processing target country: {country_name} ---")

                    self.driver.execute_script("arguments[0].open = true;", country)
                    time.sleep(0.5)

                    buttons = country.find_elements(By.CSS_SELECTOR, "tr .button")

                    for index, btn in enumerate(buttons):
                        
                        # --- NEW: Check session limit ---
                        if download_counter >= MAX_DOWNLOADS_PER_SESSION:
                            print(f"Session limit reached ({MAX_DOWNLOADS_PER_SESSION}). Stopping for relogin...")
                            all_downloads_finished = False # We still have more to download
                            return all_downloads_finished
                        
                        random_delay = random.randint(60, 90)
                        
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(0.5)

                            ActionChains(self.driver).move_to_element(btn).click().perform()

                            confirm_btn = WebDriverWait(self.driver, 30).until(
                                EC.element_to_be_clickable(CONFIRM_BUTTON_SELECTOR)
                            )
                            confirm_btn.click()

                            WebDriverWait(self.driver, 30).until(
                                EC.invisibility_of_element_located(MODAL_BACKDROP_SELECTOR)
                            )
                            
                            download_counter += 1
                            print(f"Successfully downloaded config {index + 1} (Total: {download_counter}). Waiting {random_delay}s...")
                            time.sleep(random_delay) 

                        except (TimeoutException, ElementClickInterceptedException) as e:
                            print(f"CRITICAL ERROR: Failed to download config {index + 1}. Rate limit or session issue detected. Shutting down session.")
                            all_downloads_finished = False
                            return all_downloads_finished
                        
                        except Exception as e:
                            print(f"General error during download {index + 1}: {e}. Shutting down session.")
                            all_downloads_finished = False
                            return all_downloads_finished

            return all_downloads_finished # Returns True if it finished all loops

        except Exception as e:
            print(f"Error in main download loop: {e}")
            return False

    def run(self, username, password):
        """Executes the full automation workflow with relogin cycle."""
        
        all_downloads_finished = False
        session_count = 0
        
        try:
            while not all_downloads_finished and session_count < 10: # Limit to 10 sessions (200 downloads) for safety
                
                session_count += 1
                print(f"\n###################### Starting Session {session_count} ######################")
                
                # 1. Setup Driver and Login
                self.setup()
                if not self.login(username, password):
                    print("Failed to log in. Aborting run.")
                    break
                
                # 2. Navigate and Download
                if self.navigate_to_downloads():
                    all_downloads_finished = self.process_downloads()
                
                # 3. Logout
                self.logout()
                self.teardown() # Fully close the browser instance
                
                if all_downloads_finished:
                    print("\n###################### All configurations downloaded successfully! ######################")
                else:
                    print(f"Session {session_count} completed. Waiting {RELOGIN_DELAY} seconds before relogging in...")
                    time.sleep(RELOGIN_DELAY) # Wait 2 minutes before trying again

        except Exception as e:
            print(f"Runtime Error in main loop: {e}")
        finally:
            self.teardown()


if __name__ == "__main__":
    USERNAME = os.environ.get("VPN_USERNAME")
    PASSWORD = os.environ.get("VPN_PASSWORD")
    
    if not USERNAME or not PASSWORD:
        print("---")
        print("ERROR: VPN_USERNAME or VPN_PASSWORD not loaded from environment variables.")
        print("Please configure them as Secrets in your GitHub repository.")
        print("---")
    else:
        print("Account info loaded from environment variables. Starting workflow...")
        proton = ProtonVPN()
        proton.run(USERNAME, PASSWORD)
