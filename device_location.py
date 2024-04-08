import geocoder

def get_current_location():
    try:
        # Get the current location using the geocoder library
        location = geocoder.ip('me')

        # Extract latitude and longitude from the location object
        latitude = location.latlng[0]
        longitude = location.latlng[1]

        return latitude, longitude
    except Exception as e:
        print(f"Error getting location: {e}")
        return None

def generate_google_maps_link(latitude, longitude, zoom=15):
    # Generate the Google Maps link with an optional zoom level
    maps_link = f"https://www.google.com/maps?q={latitude},{longitude}&z={zoom}"

    return maps_link

def get_mapslink():
# Get the current location
    current_location = get_current_location()

    if current_location:
        # Display the coordinates
        print("Current Location Coordinates:")
        print(f"Latitude: {current_location[0]}")
        print(f"Longitude: {current_location[1]}")

        # Generate and display the Google Maps link
        maps_link = generate_google_maps_link(*current_location)
        print("\nGoogle Maps Link:")
        print(maps_link)
        return maps_link



