import os

def display_home_page():
    print("Welcome to the Home Page!")
    print("Press 's' to signup")
    print("Press 'l' to login")

def run_signup():
    # Assuming signup.py contains the signup code
    os.system('python signup.py')

def run_login():
    # Assuming login.py contains the login code
    os.system('python login.py')

def home_page():
    while True:
        display_home_page()
        choice = input("Enter your choice: ")

        if choice.lower() == 's':
            run_signup()
        elif choice.lower() == 'l':
            run_login()
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    home_page()
