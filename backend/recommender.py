def recommend_books(df, genres, mood, liked_books):
    recommendations = []

    # Normalize and clean input
    genres = [g.lower() for g in genres] if genres else []
    liked_books = liked_books.lower().strip() if liked_books else ""
    keywords = [word for word in liked_books.split() if len(word) > 2]

    print("Initial dataset size:", df.shape)

    # Clean the data columns to avoid NaNs
    df["Category"] = df["Category"].fillna("").str.lower()
    df["Title"] = df["Title"].fillna("").str.lower()
    df["Description"] = df["Description"].fillna("").str.lower()

    # Filter by genre (substring match)
    if genres:
        df = df[df["Category"].apply(lambda x: any(g in x for g in genres))]
        print("After genre filter:", df.shape)

    # Filter by liked book keywords (match any word in title or description)
    if keywords:
        df = df[
            df["Title"].apply(lambda t: any(k in t for k in keywords)) |
            df["Description"].apply(lambda d: any(k in d for k in keywords))
        ]
        print("After liked_books filter:", df.shape)

    # Optional: You can add mood filtering later if your dataset supports it

    # Take top 5 matches
    top_books = df.head(5)

    for _, row in top_books.iterrows():
        recommendations.append({
            "title": row["Title"].title(),
            "reason": f"Matches genre '{row['Category']}' and shares keywords with books you liked."
        })

    print("Final recommendations count:", len(recommendations))
    return recommendations
