from twilio.rest import Client
from datetime import datetime, timezone, timedelta
import twilio_keys

def send_SMS():
    #calculating time of image capturing
    current_utc_time = datetime.utcnow()  # Add parentheses to call the method
    indian_time_offset = timedelta(hours=5, minutes=30)
    current_indian_time = current_utc_time + indian_time_offset

    current_date_and_time = current_indian_time.strftime("%d %B %Y at %I:%M %p")

    client= Client(twilio_keys.twilio_accountSID, twilio_keys.twilio_authToken)
    message= client.messages.create(
        body=f"""Alert!!! someone with your password tried to access your device at time {current_date_and_time}For furhter details please check your email.""",
        from_=twilio_keys.twilio_number,
        to=twilio_keys.destination_number
    )
    print("ALERT SMS SENT")
