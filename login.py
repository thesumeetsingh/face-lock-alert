import os
import getpass
import cv2

def recognize_face(username):
    verification = None
    confidence_values = []

    video = cv2.VideoCapture(0)
    facedetect = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    try:
        for _ in range(5):
            ret, frame = video.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = facedetect.detectMultiScale(gray, 1.3, 5)

            if len(faces) == 0:
                raise Exception("No face detected")

            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]

                # Load the trained model
                trained_model_filename = f"trainedmodels/trainedmodel_{username}.xml"
                if not os.path.exists(trained_model_filename):
                    raise FileNotFoundError(f"Trained model not found: {trained_model_filename}")

                trained_model = cv2.face.LBPHFaceRecognizer_create()
                trained_model.read(trained_model_filename)

                label, confidence = trained_model.predict(roi_gray)
                confidence_values.append(confidence)

                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        video.release()
        cv2.destroyAllWindows()

        average_confidence = sum(confidence_values) / len(confidence_values)

        if average_confidence < 50:
            verification = True
        else:
            verification = False

    except Exception as e:
        video.release()
        cv2.destroyAllWindows()
        print(f"Error: {e}")
        print("No user detected")
        verification = False
    
    return verification

def login():
    print("Welcome to the Login Page!")

    while True:
        # Get user input for username
        username = input("Enter your username: ")

        # Create a 'temp' folder if it doesn't exist
        temp_folder = 'temp'
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)

        # Create and write to 'temp_userdetails.txt' in the 'temp' folder
        temp_userdetails_filename = os.path.join(temp_folder, 'temp_userdetails.txt')
        with open(temp_userdetails_filename, 'w') as temp_file:
            temp_file.write(f"username: {username}\n")

        # Check if the user exists in the 'users' folder
        user_info_filename = os.path.join('users', f"{username}.txt")
        if not os.path.exists(user_info_filename):
            print("User not found.")
            choice = input("Press 's' to go to the signup page, 'l' to try again, or 'q' to quit: ")
            if choice.lower() == 's':
                # Redirect to the signup page
                os.system('python signup.py')
            elif choice.lower() == 'l':
                # Try again with the same username
                continue
            elif choice.lower() == 'q':
                print("Exiting.")
                return
            else:
                print("Invalid choice. Exiting.")
                return

        # Get email from 'username.txt' in 'users' folder
        with open(user_info_filename, 'r') as user_file:
            lines = user_file.readlines()
            for line in lines:
                if line.startswith("Email"):
                    email = line.split(":")[1].strip()
                    # Append email to 'temp_userdetails.txt' in the 'temp' folder
                    with open(temp_userdetails_filename, 'a') as temp_file:
                        temp_file.write(f"Email: {email}\n")
                    break

        # Get user input for password
        entered_password = getpass.getpass("Enter your password: ")

        # Check the password from the 'passwords' folder
        password_filename = os.path.join('passwords', f"{username}_password.txt")
        with open(password_filename, 'r') as file:
            stored_password = file.readline().split(":")[1].strip()

        if entered_password != stored_password:
            while True:
                print("Incorrect password.")
                choice = input("Press 'r' to retry, 'l' to try again with a different username, 's' to signup, or 'q' to quit: ")
                if choice.lower() == 'r':
                    entered_password = getpass.getpass("Enter your password: ")
                    if entered_password == stored_password:
                        break
                elif choice.lower() == 'l':
                    # Try again with a different username
                    break
                elif choice.lower() == 's':
                    # Run signup.py
                    os.system('python signup.py')
                    return
                elif choice.lower() == 'q':
                    print("Exiting.")
                    return
                else:
                    print("Invalid choice.")
        else:
            # Check face recognition using the trained model
            if recognize_face(username):
                print("Login successful!")
                choice = input("Press 's' to go to signup, 'l' to go to the login page, 'q' to quit, or 'h' to go to the home page: ")
                if choice.lower() == 's':
                    # Redirect to the signup page
                    os.system('python signup.py')
                    return
                elif choice.lower() == 'l':
                    # Redirect to the login page
                    continue
                elif choice.lower() == 'q':
                    print("Exiting.")
                    return
                elif choice.lower() == 'h':
                    # Redirect to the home page (or whatever the home page logic is)
                    print("Redirecting to the home page...")
                    return
                else:
                    print("Invalid choice.")
            else:
                print("Breach detected")
                os.system('python alert.py')
                choice = input("Press 'l' to login again, 's' to signup, 'h' to go to the home page, or 'q' to quit: ")
                if choice.lower() == 'l':
                    # Retry login
                    continue
                elif choice.lower() == 's':
                    # Run signup.py
                    os.system('python signup.py')
                    return
                elif choice.lower() == 'h':
                    # Redirect to the home page (or whatever the home page logic is)
                    print("Redirecting to the home page...")
                    return
                elif choice.lower() == 'q':
                    print("Exiting.")
                    return
                else:
                    print("Invalid choice.")

# Run the login function
login()
