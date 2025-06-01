from flask import Flask, render_template, request, redirect, url_for
from rdflib import Graph, Namespace
from rdflib.namespace import RDF
import os
import random
from collections import defaultdict
from rdflib.plugins.parsers.notation3 import BadSyntax
from rdflib.exceptions import ParserError

app = Flask(__name__)

# Configuración de namespaces
MUSIC_NS = Namespace("http://www.semantic-music.org/")

# Almacenamiento en memoria de gustos de usuarios
user_preferences = {}
user_genre_profiles = defaultdict(dict)

# Géneros disponibles (12 géneros)
ALL_GENRES = [
    "Pop", "Rock", "Electronica", "Jazz", 
    "Hip_Hop", "Metal", "Reggaeton", "Salsa", 
    "Country", "Blues", "K_Pop", "Indie"
]

# Similitud entre géneros usando SOLO géneros existentes
GENRE_SIMILARITY = {
    "Pop": ["K_Pop", "Indie"],
    "Rock": ["Metal", "Indie"],
    "Electronica": ["Pop", "Indie"],
    "Jazz": ["Blues", "Salsa"],
    "Hip_Hop": ["Reggaeton", "Pop"],
    "Metal": ["Rock", "Hip_Hop"],
    "Reggaeton": ["Salsa", "Hip_Hop"],
    "Salsa": ["Reggaeton", "Jazz"],
    "Country": ["Blues", "Rock"],
    "Blues": ["Jazz", "Country"],
    "K_Pop": ["Pop", "Electronica"],
    "Indie": ["Rock", "Electronica"]
}

def load_songs():
    """Carga las canciones desde el archivo RDF"""
    try:
        g = Graph()
        if not os.path.exists("canciones.rdf"):
            print("❌ Error: Archivo canciones.rdf no encontrado")
            return []
        
        g.parse("canciones.rdf")
        
        songs = []
        for s in g.subjects(RDF.type, MUSIC_NS.Cancion):
            try:
                title = g.value(s, MUSIC_NS.titulo)
                genre_res = g.value(s, MUSIC_NS.perteneceAGenero)
                genre = genre_res.split("#")[-1] if genre_res else "Desconocido"
                
                # Filtrar géneros no válidos
                if genre not in ALL_GENRES:
                    print(f"⚠️ Género no válido: {genre} para canción {s}")
                    continue
                
                views = g.value(s, MUSIC_NS.visualizaciones)
                
                views_int = 0
                if views:
                    try:
                        views_int = int(str(views))
                    except ValueError:
                        print(f"⚠️ Valor inválido para visualizaciones: {views}")
                
                song_data = {
                    "id": s.split("#")[-1],
                    "title": str(title) if title else "Sin título",
                    "genre": str(genre),
                    "views": views_int
                }
                songs.append(song_data)
            except (AttributeError, TypeError, ValueError) as e:
                print(f"⚠️ Error procesando canción {s}: {str(e)}")
        
        print(f"✅ Canciones cargadas: {len(songs)}")
        return songs
    
    except (ParserError, BadSyntax) as e:
        print(f"❌ Error de sintaxis en el archivo RDF: {str(e)}")
        return []
    except TimeoutError as e:
        print(f"❌ Error de tiempo de espera: {str(e)}")
        return []
    except ConnectionError as e:
        print(f"❌ Error de conexión: {str(e)}")
        return []
    except OSError as e:
        print(f"❌ Error de sistema al leer el archivo: {str(e)}")
        return []
    except RuntimeError as e:
        print(f"❌ Error de tiempo de ejecución: {str(e)}")
        return []
    except ImportError as e:
        print(f"❌ Error de importación: {str(e)}")
        return []
    except MemoryError as e:
        print(f"❌ Error de memoria: {str(e)}")
        return []
    except NameError as e:
        print(f"❌ Error de nombre: {str(e)}")
        return []
    except KeyError as e:
        print(f"❌ Error de clave: {str(e)}")
        return []
    except IndexError as e:
        print(f"❌ Error de índice: {str(e)}")
        return []
    except UnicodeError as e:
        print(f"❌ Error de unicode: {str(e)}")
        return []

# Cargar canciones al iniciar
all_songs = load_songs()

def get_recommendations(user_id):
    """Genera recomendaciones personalizadas basadas en gustos y descubrimiento"""
    # 1. Recomendaciones principales: mismo género que las gustadas
    main_recommendations = []
    
    # 2. Recomendaciones de descubrimiento: géneros no explorados
    discovery_recommendations = []
    
    # 3. Recomendaciones basadas en popularidad global
    popular_recommendations = sorted(
        [s for s in all_songs],
        key=lambda x: x['views'], 
        reverse=True
    )[:20]  # Top 20 global
    
    liked_songs = user_preferences.get(user_id, [])
    
    # Obtener canciones no gustadas
    non_liked_songs = [s for s in all_songs if s['id'] not in liked_songs]
    
    if user_id in user_preferences and user_preferences[user_id]:
        # Obtener géneros preferidos
        liked_genres = set()
        for song_id in user_preferences[user_id]:
            song = next((s for s in all_songs if s['id'] == song_id), None)
            if song:
                liked_genres.add(song['genre'])
                # Actualizar perfil de género
                if song['genre'] not in user_genre_profiles[user_id]:
                    user_genre_profiles[user_id][song['genre']] = 0
                user_genre_profiles[user_id][song['genre']] += 1
        
        # MEJORA CLAVE: Limitar a 2 canciones por género para evitar dominancia
        genre_limits = {genre: 0 for genre in liked_genres}
        
        # Primero recolectar todas las canciones candidatas
        candidate_songs = []
        for song in non_liked_songs:
            if song['genre'] in liked_genres:
                candidate_songs.append(song)
        
        # Ordenar por popularidad
        candidate_songs = sorted(candidate_songs, key=lambda x: x['views'], reverse=True)
        
        # Seleccionar hasta 2 canciones por género
        for song in candidate_songs:
            if genre_limits[song['genre']] < 2:
                main_recommendations.append(song)
                genre_limits[song['genre']] += 1
                if len(main_recommendations) >= 5:  # Limite total
                    break
        
        # Recomendaciones de descubrimiento: géneros no explorados
        # Obtener todos los géneros disponibles
        all_genres_set = set(ALL_GENRES)
        # Géneros no explorados por el usuario
        unexplored_genres = list(all_genres_set - liked_genres)
        
        # Si hay géneros no explorados
        if unexplored_genres:
            # Seleccionar 2 géneros al azar para descubrimiento
            selected_genres = random.sample(unexplored_genres, min(2, len(unexplored_genres)))
            
            for genre in selected_genres:
                # Canciones más populares de ese género no gustadas
                genre_songs = [s for s in non_liked_songs if s['genre'] == genre]
                if genre_songs:
                    # Tomar las 2 canciones más populares del género
                    top_songs = sorted(genre_songs, key=lambda x: x['views'], reverse=True)[:2]
                    discovery_recommendations.extend(top_songs)
        else:
            # Si ya exploró todos los géneros, sugerir géneros relacionados
            for genre in liked_genres:
                related_genres = GENRE_SIMILARITY.get(genre, [])
                # Filtrar solo géneros válidos
                valid_related_genres = [g for g in related_genres if g in ALL_GENRES]
                
                for related_genre in valid_related_genres:
                    # Si el género relacionado no es ya un género gustado
                    if related_genre not in liked_genres:
                        # Canciones de géneros relacionados
                        genre_songs = [s for s in non_liked_songs if s['genre'] == related_genre]
                        if genre_songs:
                            top_song = max(genre_songs, key=lambda x: x['views'])
                            discovery_recommendations.append(top_song)
            
            # Eliminar duplicados
            seen_ids = set()
            unique_discovery = []
            for song in discovery_recommendations:
                if song['id'] not in seen_ids:
                    unique_discovery.append(song)
                    seen_ids.add(song['id'])
            discovery_recommendations = unique_discovery[:4]
    else:
        # Para nuevos usuarios: no hay recomendaciones principales
        main_recommendations = []
        
        # Seleccionar géneros diversos para descubrimiento
        discovery_genres = random.sample(ALL_GENRES, min(2, len(ALL_GENRES)))
        
        for genre in discovery_genres:
            genre_songs = [s for s in non_liked_songs if s['genre'] == genre]
            if genre_songs:
                # Tomar la canción más popular del género
                top_song = max(genre_songs, key=lambda x: x['views'])
                discovery_recommendations.append(top_song)
    
    # Combinar todas las recomendaciones, evitando duplicados
    combined = []
    seen_ids = set()
    
    # Agregar en orden de prioridad
    for rec_list in [main_recommendations, discovery_recommendations, popular_recommendations]:
        for song in rec_list:
            if song['id'] not in seen_ids:
                combined.append(song)
                seen_ids.add(song['id'])
    
    return {
        'main': main_recommendations,
        'discovery': discovery_recommendations,
        'combined': combined[:15],  # Limitar a 15 recomendaciones
        'has_main': bool(main_recommendations)  # Bandera para saber si hay recomendaciones principales
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        if not user_id:
            return render_template('index.html', error="Por favor ingrese un ID de usuario")
        return redirect(url_for('dashboard', user_id=user_id))
    return render_template('index.html')

@app.route('/dashboard/<user_id>', methods=['GET', 'POST'])
def dashboard(user_id):
    if request.method == 'POST':
        action = request.form.get('action')
        song_id = request.form.get('song_id')
        
        if not action or not song_id:
            print("⚠️ Advertencia: Faltan parámetros en la solicitud")
            return redirect(url_for('dashboard', user_id=user_id))
        
        # Inicializar preferencias si es necesario
        if user_id not in user_preferences:
            user_preferences[user_id] = []
        
        # Actualizar preferencias
        if action == 'like' and song_id not in user_preferences[user_id]:
            user_preferences[user_id].append(song_id)
            print(f"✅ Usuario {user_id} dio like a canción {song_id}")
        elif action == 'unlike' and song_id in user_preferences[user_id]:
            user_preferences[user_id].remove(song_id)
            print(f"✅ Usuario {user_id} quitó like a canción {song_id}")
    
    # Preparar datos para la plantilla
    liked_songs = user_preferences.get(user_id, [])
    recommendations = get_recommendations(user_id)
    
    # Filtrar canciones no gustadas para mostrar
    non_liked_songs = [s for s in all_songs if s['id'] not in liked_songs]
    
    return render_template(
        'dashboard.html',
        user_id=user_id,
        all_songs=non_liked_songs,  # Solo canciones no gustadas
        liked_songs=liked_songs,
        main_recommendations=recommendations['main'],
        discovery_recommendations=recommendations['discovery'],
        combined_recommendations=recommendations['combined'],
        original_all_songs=all_songs,
        has_preferences=bool(user_preferences.get(user_id, [])),
        has_main_recommendations=recommendations['has_main']
    )

@app.route('/buscar/<user_id>', methods=['POST'])
def search(user_id):
    genre = request.form.get('genre', '')
    liked_songs = user_preferences.get(user_id, [])
    
    # Filtrar por género y excluir gustadas
    if genre and genre in ALL_GENRES:  # Solo si es un género válido
        filtered_songs = [s for s in all_songs if s['genre'] == genre and s['id'] not in liked_songs]
    else:
        filtered_songs = [s for s in all_songs if s['id'] not in liked_songs]
    
    recommendations = get_recommendations(user_id)
    
    return render_template(
        'dashboard.html',
        user_id=user_id,
        all_songs=filtered_songs,
        liked_songs=liked_songs,
        main_recommendations=recommendations['main'],
        discovery_recommendations=recommendations['discovery'],
        combined_recommendations=recommendations['combined'],
        original_all_songs=all_songs,
        has_preferences=bool(user_preferences.get(user_id, [])),
        has_main_recommendations=recommendations['has_main']
    )

if __name__ == '__main__':
    # Verificar que las plantillas existan
    TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    required_templates = ['index.html', 'dashboard.html']
    
    missing_templates = []
    for template in required_templates:
        path = os.path.join(TEMPLATE_DIR, template)
        if not os.path.exists(path):
            missing_templates.append(template)
            print(f"❌ Plantilla no encontrada: {path}")
    
    if missing_templates:
        print(f"⚠️ Error crítico: Faltan {len(missing_templates)} plantillas")
    else:
        print("✅ Todas las plantillas encontradas")
    
    app.run(debug=True)