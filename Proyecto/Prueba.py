# MusicMind: Recomendador Semántico de Canciones

# Requisitos: rdflib, flask
# pip install rdflib flask

from flask import Flask, request, render_template_string
from rdflib import Graph, Namespace, RDF, URIRef
import random

app = Flask(__name__)

# Ontología y RDF
MUSIC = Namespace("http://example.org/music#")
g = Graph()
g.parse("music_data.rdf")  # RDF con canciones, géneros y usuarios

# Agente de Perfil
class UserProfileAgent:
    def __init__(self):
        self.likes = []

    def update_profile(self, song_uri):
        genre = g.value(song_uri, MUSIC.genre)
        if genre:
            self.likes.append(genre)

    def most_liked_genre(self):
        if not self.likes:
            return None
        return max(set(self.likes), key=self.likes.count)

# Agente de Recomendación
class RecommendationAgent:
    def recommend(self, liked_genre):
        if not liked_genre:
            return "http://example.org/music#song1"  # Recomendación por defecto
        for s in g.subjects(RDF.type, MUSIC.Song):
            if g.value(s, MUSIC.genre) == liked_genre:
                return s
        return None

user_agent = UserProfileAgent()
rec_agent = RecommendationAgent()

# Plantilla HTML básica
html = """
<h1>MusicMind</h1>
<p>¿Te gusta esta canción?</p>
<p><strong>{{ song }}</strong> - Género: {{ genre }}</p>
<form method="post">
    <input type="hidden" name="song_uri" value="{{ song_uri }}">
    <button name="feedback" value="yes">Sí</button>
    <button name="feedback" value="no">No</button>
</form>
<p><a href="/recommend">Ver recomendación</a></p>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        song_uri = URIRef(request.form["song_uri"])
        if request.form["feedback"] == "yes":
            user_agent.update_profile(song_uri)
    songs = list(g.subjects(RDF.type, MUSIC.Song))
    song_uri = random.choice(songs)
    title = g.value(song_uri, MUSIC.title)
    genre = g.value(song_uri, MUSIC.genre)
    return render_template_string(html, song=title, genre=genre, song_uri=song_uri)

@app.route("/recommend")
def recommend():
    liked_genre = user_agent.most_liked_genre()
    song_uri = rec_agent.recommend(liked_genre)
    title = g.value(song_uri, MUSIC.title)
    genre = g.value(song_uri, MUSIC.genre)
    return f"<h1>Recomendación</h1><p><strong>{title}</strong> - Género: {genre}</p><p><a href='/'>Volver</a></p>"

if __name__ == "__main__":
    app.run(debug=True)
