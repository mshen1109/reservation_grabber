import time
import datetime
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    
    # Optional: Set binary location from env (useful for Docker)
    chrome_binary = os.environ.get("CHROME_BINARY_LOCATION")
    if chrome_binary:
        options.binary_location = chrome_binary
    
    # Persistent Profile: Save session to a local folder
    profile_path = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"user-data-dir={profile_path}")
    
    # Initialize Chrome Driver with retries
    for attempt in range(3):
        try:
            # Check for system installed chromedriver (Docker)
            system_chromedriver = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
            if os.path.exists(system_chromedriver):
                service = Service(executable_path=system_chromedriver)
            else:
                # Fallback to webdriver_manager
                service = Service(ChromeDriverManager().install())
                
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Failed to start driver (attempt {attempt+1}/3): {e}")
            time.sleep(5)
    
    raise Exception("Could not start Chrome Driver after 3 attempts.")

def check_reservations():
    print("Starting Selenium Reservation Checker...")
    
    driver = setup_driver()
    consecutive_errors = 0
    
    try:
        # 1. Login Step (Smart)
        print("Checking login status...")
        driver.get("https://www.opentable.com")
        time.sleep(3)
        
        # Check if we are logged in (look for 'Sign in' button)
        try:
            sign_in_button = driver.find_elements(By.XPATH, "//button[contains(text(), 'Sign in')]")
            if sign_in_button:
                 print("Not logged in (found 'Sign in' button). Redirecting to login page...")
                 driver.get("https://www.opentable.com/signin")
                 print("\n" + "="*50)
                 print("PLEASE LOG IN TO OPENTABLE IN THE BROWSER WINDOW.")
                 print("Once you are logged in, press ENTER in this terminal to continue.")
                 print("="*50 + "\n")
                 if not is_headless:
                    input("Press Enter to start checking reservations...")
                 else:
                    print("Running in headless mode. Cannot manually log in. Proceeding and hoping for the best (or cookies are already set).")
            else:
                 print("Already logged in! Proceeding...")
        except Exception as e:
            print(f"Login check error: {e}. Assuming logged in...")
        
        # 2. Go to the restaurant page
        url = "https://www.opentable.com/house-of-prime-rib"
        driver.get(url)
        print("Navigated to House of Prime Rib...")
        
        # Wait for page to load
        time.sleep(5)
        
        while True:
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{current_time}] Checking for Saturdays...")
            
            # TODO: The UI interaction logic is complex because OpenTable's DOM changes.
            # For a robust "checker", the best bet with Selenium is actually to intercept 
            # the API calls or just use the browser to hold the session and hit the API 
            # from the console context, OR just automate the UI clicks.
            
            # Turbo Mode: Use browser's fetch API to check availability rapidly
            # This avoids full page reloads and checks 180 days in seconds.
            
            today = datetime.date.today()
            found_slot = False
            
            # Reverting to Navigation Mode: API is blocked (403).
            # We will navigate to the specific URL for each date.
            # This is slower but mimics a real user exactly.
            
            import random
            
            print("  > Scanning next 180 days via Smart Navigation...")
            
            # Smart Scan: Check first 4 Saturdays faster, then others
            saturdays_checked = 0
            
            for i in range(180):
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

                check_date = today + datetime.timedelta(days=i)
                
                if check_date.weekday() != 5: # 5 is Saturday
                    continue
                
                # Skip the immediate upcoming weekend (or today) as requested
                # This ensures we start checking from "next weekend"
                if check_date <= today + datetime.timedelta(days=2):
                    continue
                
                saturdays_checked += 1
                date_str = check_date.strftime("%Y-%m-%d")
                
                # Construct the search URL for this specific date and time
                # We target 6:30 PM to see a range of slots
                target_url = f"https://www.opentable.com/house-of-prime-rib?corrid=409&p=3&d={date_str}T18:30"
                
                try:
                    driver.get(target_url)
                    consecutive_errors = 0 # Reset on success
                    
                    # Smart Wait: Faster for first month (most urgent), slightly slower for rest to be safe
                    if saturdays_checked <= 4:
                         wait_time = random.uniform(2.0, 3.0)
                    else:
                         wait_time = random.uniform(2.5, 4.0)
                         
                    time.sleep(wait_time)
                    
                    # Check for "no availability" message
                    # OpenTable often puts this in a specific container, but checking body text is a good fallback
                    body_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    # DISABLE "No Availability" check for now - it might be false positive
                    # if "no online availability" in body_text.lower():
                    #    # print(f"  [x] No slots on {date_str}")
                    #    pass
                    # else:
                    
                    if True: # Always check buttons
                        # Scan for time slots (they are often divs with role='button' or actual links)
                        # We'll look for anything with text matching our time format
                        
                        # Strategy: Get all elements that might be time slots
                        # 1. Real buttons
                        # 2. Divs with role='button'
                        # 3. Links (a tags)
                        
                        potential_slots = []
                        potential_slots.extend(driver.find_elements(By.TAG_NAME, "button"))
                        potential_slots.extend(driver.find_elements(By.CSS_SELECTOR, "div[role='button']"))
                        potential_slots.extend(driver.find_elements(By.TAG_NAME, "a"))
                        
                        # DEBUG: Print count
                        print(f"  Found {len(potential_slots)} potential elements on {date_str}")
                        
                        # Times we want: 5:00 PM to 8:30 PM
                        valid_times = ["5:00 PM", "5:15 PM", "5:30 PM", "5:45 PM",
                                       "6:00 PM", "6:15 PM", "6:30 PM", "6:45 PM",
                                       "7:00 PM", "7:15 PM", "7:30 PM", "7:45 PM",
                                       "8:00 PM", "8:15 PM", "8:30 PM"]
                        
                        for btn in potential_slots:
                            btn_text = btn.text.strip()
                            if len(btn_text) > 0 and "PM" in btn_text:
                                # print(f"    Element text: '{btn_text}'") # Debug print
                                pass
                            
                            if btn_text in valid_times:
                                print(f"\n!!! FOUND SLOT: {btn_text} on {date_str} !!!")
                                print(f"\n!!! FOUND SLOT: {btn_text} on {date_str} !!!")
                                send_notification(f"FOUND SLOT: {btn_text} on {date_str} at House of Prime Rib! Go book now!")
                                
                                # 1. Click the time slot
                                driver.execute_script("arguments[0].click();", btn)
                                print("Clicked time slot. Waiting for booking form...")
                                
                                # 2. Auto-Book
                                try:
                                    # Wait for the "Complete reservation" button
                                    # It's usually a red button with text "Complete reservation"
                                    time.sleep(2) # Wait for modal/page load
                                    
                                    # Try multiple selectors for the book button
                                    book_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Complete reservation')]")
                                    if not book_btns:
                                         book_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Book')]")
                                    
                                    if book_btns:
                                        print("Found booking button! Clicking...")
                                        book_btns[0].click()
                                        print("RESERVATION ATTEMPTED!")
                                        found_slot = True
                                        break
                                    else:
                                        print("Could not find 'Complete reservation' button automatically.")
                                        print("Please finish booking manually in the browser!")
                                        found_slot = True
                                        break
                                        
                                except Exception as e:
                                    print(f"Auto-booking failed: {e}")
                                    print("Please finish booking manually!")
                                    found_slot = True
                                    break
                
                except Exception as e:
                    consecutive_errors += 1
                    print(f"Error checking {date_str}: {e}")
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
                        time.sleep(5) # Wait for it to initialize
                
                if found_slot:
                    break
            
            if found_slot:
                # Keep browser open
                while True:
                    time.sleep(1)
            
            print("Cycle complete. Waiting 1 minute before next scan...")
            time.sleep(60)
            
                
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        print("Script finished. Browser closing...")
        # driver.quit() # We might want to keep it open if it crashes?

if __name__ == "__main__":
    check_reservations()
