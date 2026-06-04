# firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore
import os

def initialize_firebase():
    """Initializes the Firebase Admin SDK using your service account JSON key."""
    # Check if already initialized to prevent errors during Flask hot-reloads
    if not firebase_admin._apps:
        # Expecting the JSON file in your project root directory
        cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json')
        
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("🔥 Firebase Admin SDK initialized successfully.")
        else:
            raise FileNotFoundError(
                f"❌ Error: Firebase credentials file '{cred_path}' not found!\n"
                "Please download your private key JSON from the Firebase Console, "
                "rename it to 'serviceAccountKey.json', and place it in the Backend root directory."
            )

    return firestore.client()

# Create a single, exportable database instance
db = initialize_firebase()

