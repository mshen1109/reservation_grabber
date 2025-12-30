import requests
import json
import datetime
import time
import webbrowser
import os

def check_availability(party_size=3, search_days=60):
    url = "https://www.opentable.com/dapi/fe/gql?opname=Availability"
    
    headers = {
        "authority": "www.opentable.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://www.opentable.com",
        "referer": "https://www.opentable.com/house-of-prime-rib",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # House of Prime Rib ID
    restaurant_id = "409"
    
    while True:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Checking availability for {party_size} people (Saturdays 5-8pm)...")
        start_date = datetime.date.today()
        found_any = False
        
        for i in range(search_days):
            check_date = start_date + datetime.timedelta(days=i)
            
            # Filter: Only check Saturdays (weekday() == 5)
            if check_date.weekday() != 5:
                continue
                
            date_str = check_date.strftime("%Y-%m-%d")
            
            # We'll check 6:00 PM (18:00) as the anchor time
            payload = {
                "operationName": "Availability",
                "variables": {
                    "rid": restaurant_id,
                    "date": date_str,
                    "time": "18:00",
                    "partySize": party_size,
                    "forwardDays": 0,
                    "backwardDays": 0
                },
                "query": """
                query Availability($rid: String!, $date: String!, $time: String!, $partySize: Int!, $forwardDays: Int!, $backwardDays: Int!) {
                  availability(rid: $rid, date: $date, time: $time, partySize: $partySize, forwardDays: $forwardDays, backwardDays: $backwardDays) {
                    date
                    time
                    isAvailable
                    slotHash
                  }
                }
                """
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data and 'availability' in data['data']:
                        slots = data['data']['availability']
                        if slots:
                            # Filter for available slots between 17:00 and 20:00
                            available_slots = []
                            for s in slots:
                                if s.get('isAvailable'):
                                    slot_time = s.get('time') # Format "19:00"
                                    # Simple string comparison works for 24h format "17:00" to "20:00"
                                    if "17:00" <= slot_time <= "20:00":
                                        available_slots.append(s)
                            
                            if available_slots:
                                print(f"\n!!! FOUND SATURDAY SLOT ON {date_str} !!!")
                                for slot in available_slots:
                                    print(f"  - {slot.get('time')}")
                                    
                                    # ALERT AND OPEN
                                    print('\a') # System beep
                                    # Construct booking URL (approximate, redirects to specific slot usually)
                                    booking_url = f"https://www.opentable.com/house-of-prime-rib?corrid={restaurant_id}&p={party_size}&d={date_str}T{slot.get('time')}"
                                    print(f"Opening: {booking_url}")
                                    webbrowser.open(booking_url)
                                    
                                found_any = True
                                # Optional: Break after finding one to avoid opening too many tabs?
                                # break 
                else:
                    print(f"Error {response.status_code} for {date_str}")
                    
            except Exception as e:
                print(f"Exception checking {date_str}: {e}")
                
            # Be nice to the API
            time.sleep(1)

        if not found_any:
            print("No matching slots found. Sleeping for 1 hour...")
        else:
            print("Check complete. Sleeping for 1 hour...")
            
        time.sleep(3600) # Sleep for 1 hour

if __name__ == "__main__":
    check_availability()
