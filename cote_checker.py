import time
import datetime
import random
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def send_notification(message):
    topic = os.environ.get("NTFY_TOPIC", "mias_reservation_alerts")
    
    try:
        requests.post(f"https://ntfy.sh/{topic}", 
                      data=message.encode(encoding='utf-8'),
                      headers={"Title": "Reservation Found!", "Priority": "high"})
        print(f"Notification sent to ntfy.sh/{topic}")
    except Exception as e:
        print(f"Failed to send notification: {e}")

def setup_driver():
    is_headless = os.environ.get("HEADLESS", "false").lower() == "true"
    if not is_headless:
        print("This will open a Chrome window. DO NOT CLOSE IT.")

    # Setup Chrome options
    options = webdriver.ChromeOptions()
    if is_headless:
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Persistent Profile (optional, but good for stability)
    profile_path = os.path.join(os.getcwd(), "chrome_profile_cote")
    options.add_argument(f"user-data-dir={profile_path}")
    
    # Initialize Chrome Driver with retries
    for attempt in range(3):
        try:
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception as e:
            print(f"Failed to start driver (attempt {attempt+1}/3): {e}")
            time.sleep(5)
    
    raise Exception("Could not start Chrome Driver after 3 attempts.")

def check_cote_reservations():
    print("Starting Cote Las Vegas (SevenRooms) Checker...")
    print("Target: Fridays & Saturdays, 3 People")
    print("Time Range: 5:00 PM - 10:00 PM")
    
    driver = setup_driver()
    consecutive_errors = 0
    
    try:
        # URL with party size = 3
        base_url = "https://www.sevenrooms.com/explore/cotelv/reservations/create/search?tracking=website&party_size=3"
        
        while True:
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] Checking Cote Las Vegas...")
            
            # Check if we have too many errors
            if consecutive_errors >= 3:
                print("!!! TOO MANY ERRORS. FORCING DRIVER RESTART... !!!")
                try:
                    driver.quit()
                except:
                    pass
                driver = setup_driver()
                consecutive_errors = 0
                time.sleep(5)

            try:
                driver.get(base_url)
                time.sleep(5) # Wait for page load
                consecutive_errors = 0 # Reset on success
                
                # SevenRooms Structure:
                # Dates are often buttons or divs with text like "Fri, Dec 5"
                # Times are buttons following them.
                
                # 1. Get all text content to quickly see if any Fri/Sat is mentioned
                body_text = driver.find_element(By.TAG_NAME, "body").text
                
                # 2. Find all potential date headers
                # We look for elements containing "Fri," or "Sat,"
                # This is a broad search, then we refine
                
                # Get all buttons and divs that might be dates or times
                all_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Fri,') or contains(text(), 'Sat,') or contains(text(), 'PM')]")
                
                found_slot = False
                
                # We need to parse the visual flow. 
                # Simpler approach: Look for specific time buttons that are "good"
                # But we need to know WHICH date they belong to.
                
                # Let's grab the main container if possible, or iterate through buttons
                buttons = driver.find_elements(By.TAG_NAME, "button")
                
                current_date = None
                
                for btn in buttons:
                    text = btn.text.strip()
                    
                    # Check if this button is a Date Header
                    if "Fri," in text or "Sat," in text:
                        current_date = text
                        # print(f"  Checking Date: {current_date}")
                        continue
                        
                    # Check if this button is a Time Slot
                    # Time slots usually have "PM" or "AM"
                    if ("PM" in text or "AM" in text) and current_date:
                        # We found a time slot under a Fri/Sat date!
                        time_str = text.split('\n')[0] # Sometimes text is "9:15 PM\nDINNER"
                        
                        # Parse time to see if it's in our range (5pm - 10pm)
                        # Valid times: 5:00 PM to 10:00 PM
                        # Simple string matching for now
                        valid_hours = ["5:", "6:", "7:", "8:", "9:", "10:"]
                        is_valid_time = any(h in time_str for h in valid_hours) and "PM" in time_str
                        
                        if is_valid_time:
                            print(f"\n!!! FOUND SLOT: {time_str} on {current_date} !!!")
                            print(f"\n!!! FOUND SLOT: {time_str} on {current_date} !!!")
                            send_notification(f"FOUND SLOT: {time_str} on {current_date} at Cote Las Vegas! Go book now!")
                            
                            # Click it!
                            driver.execute_script("arguments[0].click();", btn)
                            print("Clicked slot! Please finish booking in browser.")
                            found_slot = True
                            break
                
                if found_slot:
                    # Keep browser open
                    while True:
                        time.sleep(1)
                
            except Exception as e:
                consecutive_errors += 1
                print(f"Error during check: {e}")
                # Check for fatal driver errors
                error_msg = str(e).lower()
                print(f"DEBUG: Error message length: {len(error_msg)}")
                # Broaden check for any session/connection issues
                fatal_errors = ["invalid session id", "no such window", "chrome not reachable", "connection refused", "target window already closed"]
                if any(err in error_msg for err in fatal_errors) or consecutive_errors >= 3:
                    print("!!! BROWSER CRASHED OR CLOSED. RESTARTING... !!!")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = setup_driver()
                    consecutive_errors = 0
                    time.sleep(5)
            
            # Wait before next check
            wait_time = random.uniform(30, 60)
            print(f"Waiting {int(wait_time)} seconds...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\nStopping script...")
        driver.quit()
    except Exception as e:
        print(f"Fatal error: {e}")
        driver.quit()

if __name__ == "__main__":
    check_cote_reservations()
