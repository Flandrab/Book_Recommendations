import pandas as pd

def load_books(csv_path):
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=['Title', 'Description', 'Category'])
    df = df.reset_index(drop=True)

    # Optional: lower-case genres
    df['Category'] = df['Category'].str.lower()

    return df
