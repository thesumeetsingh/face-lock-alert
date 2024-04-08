# Import necessary libraries and modules
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import facelockalert_data
import os
from datetime import datetime
import cv2
from datetime import datetime, timezone, timedelta
import device_location

maplink = device_location.get_mapslink()
smtp_port = 587
smtp_server = "smtp.gmail.com"

def send_emails(username):
    # Get the user's email address from their signup information
    user_info_filename = os.path.join('users', f"{username}.txt")
    
    if not os.path.exists(user_info_filename):
        print(f"Error: User information not found for {username}")
        return

    with open(user_info_filename, 'r') as file:
        lines = file.readlines()
        email_line = next((line for line in lines if line.startswith("Email:")), None)
    
    if email_line:
        user_email = email_line.split(":")[1].strip()
    else:
        print(f"Error: Email not found for {username}")
        return

    # Calculate current date and time
    current_utc_time = datetime.utcnow()
    indian_time_offset = timedelta(hours=5, minutes=30)
    current_indian_time = current_utc_time + indian_time_offset
    current_date_and_time = current_indian_time.strftime("%d %B %Y at %I:%M %p")

    # Capture an image
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    folder_path = "threat_images"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file_path = os.path.join(folder_path, f"{username}_IMG.jpg")
    cv2.imwrite(file_path, frame)

    try:
        # Create the email content
        body = f"""Hello {username},

        This is to notify you that a person attempted to sign in to your device at {current_date_and_time}, but the system detected that it was not you.
        The photograph of the person has been attached to this email for reference.
            Location : {maplink}
            Time : {current_date_and_time}
            Kindly check for any action and consider changing your password.

        Thanks and Regards
        FACELOCK ALERT TEAM
        """

        msg = MIMEMultipart()
        msg['From'] = facelockalert_data.facelockalertemail
        msg['To'] = user_email
        msg['Subject'] = "THREAT DETECTED"

        msg.attach(MIMEText(body, 'plain'))

        # Attach the captured image to the email
        with open(file_path, 'rb') as attachment:
            attachment_package = MIMEBase('application', 'octet-stream')
            attachment_package.set_payload((attachment).read())
            encoders.encode_base64(attachment_package)
            attachment_package.add_header('Content-Disposition', "attachment; filename= " + file_path)
            msg.attach(attachment_package)

        text = msg.as_string()

        # Connect to the SMTP server and send the email
        print("Connecting to server...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(facelockalert_data.facelockalertemail, facelockalert_data.facelockalertemailpassword)
        print("Successfully connected to server")
        print()

        # Send the email
        print(f"Sending email to: {user_email}")
        server.sendmail(facelockalert_data.facelockalertemail, user_email, text)
        print("Email sent successfully")
        print()

        # Clean up: close the server connection and remove the temporary image file
        server.quit()
        os.remove(file_path)
        print("EMAIL SENT")

    except Exception as e:
        print(f"Error sending email: {e}")

# Example usage: send_emails('example_username')
