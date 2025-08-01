from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

# --- Local Imports ---
from data_loader import load_books
from recommender import recommend_books

from flask import send_from_directory
import os



# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests (frontend to backend)

# --- Load Dataset on Startup ---
book_df = load_books("BooksDataset.csv")

@app.route("/")
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Serve CSS or JS files if needed
    if os.path.exists(path):
        return send_from_directory('.', path)
    else:
        return "File Not Found", 404

# --- API Route for Book Recommendation ---
@app.route("/recommend", methods=["POST"])
def recommend():
    # Get JSON input from frontend
    data = request.get_json()

    # Extract individual fields from the request
    genres = data.get("genre", [])
    if isinstance(genres, str):
        genres = [genres]  # Convert single string to list

    mood = data.get("mood", "")
    liked_books = data.get("liked_books", "")

    # Get recommendation results from the recommender logic
    results = recommend_books(book_df, genres, mood, liked_books)

    print("Incoming data:", data)
    print("Genres:", genres)
    print("Mood:", mood)
    print("Liked Books:", liked_books)

    # Return the results as JSON
    return jsonify(results)

# --- Run the Flask App ---
if __name__ == "__main__":
    app.run(debug=True)
