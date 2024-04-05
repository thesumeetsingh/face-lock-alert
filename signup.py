import os
import cv2
import numpy as np
import re
import subprocess  # For running another Python script

def validate_email(email):
    # Simple email validation using regular expression
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)

def validate_phone_number(phone_number):
    # Simple phone number validation using regular expression
    phone_regex = r'^\d{10}$'
    return re.match(phone_regex, phone_number)

def is_username_available(username):
    # Check if the username is already present in the 'users' folder
    user_info_filename = os.path.join('users', f"{username}.txt")
    return not os.path.exists(user_info_filename)

def save_user_info(username, password, email, phone_number):
    # Create the 'users' folder if it doesn't exist
    if not os.path.exists('users'):
        os.makedirs('users')

    # Save user information to a text file in the 'users' folder
    filename = os.path.join('users', f"{username}.txt")
    with open(filename, 'w') as file:
        file.write(f"Username: {username}\n")
        file.write(f"Password: {password}\n")
        file.write(f"Email: {email}\n")
        file.write(f"Phone Number: {phone_number}\n")
    print(f"User information saved to {filename}")

    # Create the 'passwords' folder if it doesn't exist
    if not os.path.exists('passwords'):
        os.makedirs('passwords')

    # Save the password to a text file in the 'passwords' folder
    password_filename = os.path.join('passwords', f"{username}_password.txt")
    with open(password_filename, 'w') as file:
        file.write(f"Password: {password}\n")
    print(f"Password saved to {password_filename}")

def capture_images(username):
    # Create the 'images' folder if it doesn't exist
    if not os.path.exists('images'):
        os.makedirs('images')

    # Create a subfolder for the user's images
    user_images_folder = os.path.join('images', username)
    if not os.path.exists(user_images_folder):
        os.makedirs(user_images_folder)

    # Use OpenCV to capture images
    cap = cv2.VideoCapture(0)
    print("Press 'y' and Enter to capture an image. Press 'q' to finish.")

    count = 0
    while True:
        ret, frame = cap.read()
        cv2.imshow('Capture Images', frame)

        key = cv2.waitKey(1)
        if key == ord('y'):
            # Save the captured image
            image_filename = os.path.join(user_images_folder, f"{username}_{count}.jpg")
            cv2.imwrite(image_filename, frame)
            print(f"Image {count + 1} captured and saved: {image_filename}")
            count += 1
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def train_model(username):
    # Create the 'trainedmodels' folder if it doesn't exist
    if not os.path.exists('trainedmodels'):
        os.makedirs('trainedmodels')

    # Load Haarcascade frontal face recognition XML file
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Read images from the 'images' folder
    images_folder = os.path.join('images', username)
    images = []
    labels = []

    for filename in os.listdir(images_folder):
        if filename.endswith('.jpg'):
            img_path = os.path.join(images_folder, filename)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            face = face_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5)
            for (x, y, w, h) in face:
                face_roi = img[y:y + h, x:x + w]
                images.append(face_roi)
                labels.append(1)  # Assuming label 1 for the user

    # Train the model
    labels = np.array(labels)
    model = cv2.face.LBPHFaceRecognizer_create()
    model.train(images, labels)

    # Save the trained model
    model_filename = os.path.join('trainedmodels', f"trainedmodel_{username}.xml")
    model.write(model_filename)
    print(f"Trained model saved: {model_filename}")

    # Return the trained model filename for later use
    return model_filename

def login_with_trained_model(trained_model_filename):
    # Implement the login functionality using the trained model
    print("Login with trained model functionality goes here.")

def signup():
    print("Welcome to the Signup Page!")

    # Infinite attempts to enter a unique username
    while True:
        username = input("Enter your username: ")

        if is_username_available(username):
            break
        else:
            print("Username already exists. Please choose a different username.")

    password = input("Create a password: ")
    confirm_password = input("Confirm your password: ")

    # Validate password match
    while password != confirm_password:
        print("Passwords do not match. Please try again.")
        password = input("Create a password: ")
        confirm_password = input("Confirm your password: ")

    # Get user input for email and validate format
    email = input("Enter your email address: ")
    while not validate_email(email):
        print("Invalid email format. Please enter a valid email address.")
        email = input("Enter your email address: ")

    # Get user input for phone number and validate format
    phone_number = input("Enter your phone number: ")
    while not validate_phone_number(phone_number):
        print("Invalid phone number format. Please enter a 10-digit phone number.")
        phone_number = input("Enter your phone number: ")

    # Save user information to a text file and save password to a separate text file
    save_user_info(username, password, email, phone_number)

    # Capture images
    capture_images(username)

    # Train the model and get the trained model filename
    trained_model_filename = train_model(username)

    print("Signup successful!\n")

    # Option to login using the trained model
    while True:
        login_choice = input("Press 'l' to login now, 's' to signup again, or any other key to exit: ")
        if login_choice.lower() == 'l':
            # Run the login script (login.py)
            subprocess.run(['python', 'login.py'])
            break
        elif login_choice.lower() == 's':
            # Signup again
            signup()
        else:
            print("Exiting.")
            break

# Run the signup function
signup()
