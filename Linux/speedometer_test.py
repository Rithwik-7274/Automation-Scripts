import os
import sys
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROMIUM_BINARY_PATH = "/usr/bin/chromium"
CHROMEDRIVER_BINARY_PATH = "/usr/bin/chromedriver"
SPEEDOMETER_URL = "http://localhost:8080/"

UI_TIMEOUT_SEC = 20
BENCHMARK_TIMEOUT_SEC = 200
DOM_TRANSITION_DELAY_SEC = 5
FILE_FLUSH_DELAY_SEC = 5
SERVER_START_DELAY_SEC = 5

SERVER_CMD = ["python", "-m", "http.server", "8080", "--directory", "./Speedometer"]

def run_benchmark():
    current_dir = os.path.join(os.path.abspath(os.getcwd()), sys.argv[1])

    # Start Speedometer on a server
    server_process = subprocess.Popen(SERVER_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(SERVER_START_DELAY_SEC)

    service = Service(executable_path=CHROMEDRIVER_BINARY_PATH)
    options = webdriver.ChromeOptions()
    options.binary_location = CHROMIUM_BINARY_PATH
    
    # Configure silent downloads to the current working directory
    prefs = {
        "download.default_directory": current_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # Disable background network telemetry and sync for clean power readings
    options.add_argument("--start-maximized")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-extensions")
    
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(SPEEDOMETER_URL)
        
        start_btn = WebDriverWait(driver, UI_TIMEOUT_SEC).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.start-tests-button, #home button"))
        )
        start_btn.click()
        
        # Wait for the results DOM elements to populate
        WebDriverWait(driver, BENCHMARK_TIMEOUT_SEC).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#result-number, .result-score, #results"))
        )

        try:
            details_btn = WebDriverWait(driver, UI_TIMEOUT_SEC).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//*[contains(translate(text(), 'DETAILS', 'details'), 'details')]"
                ))
            )
            details_btn.click()
            time.sleep(DOM_TRANSITION_DELAY_SEC) 
        except Exception as e:
            print("ERROR: Failed to click Details button:", e)

        try:
            download_btn = WebDriverWait(driver, UI_TIMEOUT_SEC).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download JSON')]"))
            )
            download_btn.click()
            time.sleep(FILE_FLUSH_DELAY_SEC)
        except Exception as e:
            print("ERROR: Failed to click the Download JSON button:", e)
            
    finally:
        driver.quit()
        server_process.terminate()

if __name__ == "__main__":
    run_benchmark()