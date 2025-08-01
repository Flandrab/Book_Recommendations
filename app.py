from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
from recommender import recommend_books

app = Flask(__name__)
CORS(app)

# Load your dataset once
df = pd.read_csv("BooksDataset.csv")

@app.route("/")
def home():
    return render_template("index.html")  # serves templates/index.html

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()
    genres = data.get("genre", [])
    if isinstance(genres, str):
        genres = [genres]
    mood = data.get("mood", "")
    liked_books = data.get("liked_books", "")
    results = recommend_books(df, genres, mood, liked_books)
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)

