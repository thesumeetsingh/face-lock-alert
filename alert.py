import image_attachment_email
import alert_sms
import facelockalert_data
import os

def get_and_delete_temp_userdetails():
    temp_folder = 'temp'
    temp_userdetails_filename = os.path.join(temp_folder, 'temp_userdetails.txt')

    if not os.path.exists(temp_userdetails_filename):
        print("Error: temp_userdetails.txt not found.")
        return None

    try:
        with open(temp_userdetails_filename, 'r') as temp_file:
            lines = temp_file.readlines()
            username_line = next((line for line in lines if line.startswith("username:")), None)

        if username_line:
            username = username_line.split(":")[1].strip()
            return username
        else:
            print("Error: Username not found in temp_userdetails.txt.")
            return None

    except Exception as e:
        print(f"Error reading temp_userdetails.txt: {e}")
        return None

    finally:
        # Delete the temp_userdetails.txt file
        try:
            os.remove(temp_userdetails_filename)
        except OSError as e:
            print(f"Error deleting temp_userdetails.txt: {e}")

def alert_message():
    username = get_and_delete_temp_userdetails()

    if username:
        print("Your username is:", username)
        image_attachment_email.send_emails(username)
        alert_sms.send_SMS()
        print("ALERT SMS AND EMAIL SENT")
    else:
        print("Unable to retrieve username from temp_userdetails.txt.")

if __name__ == "__main__":
    alert_message()
