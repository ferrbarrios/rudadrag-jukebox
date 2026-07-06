import streamlit as st
from supabase import create_client, Client
from postgrest import APIError
from googleapiclient.discovery import build
import re

# --- CONFIGURACIÓN DE APIS ---
SUPABASE_URL = "https://iolidngaqcjtumkcrtcx.supabase.co/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvbGlkbmdhcWNqdHVta2NydGN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzNTcwODUsImV4cCI6MjA5ODkzMzA4NX0.8RQU3yZvhjoZXQh6uZkDfcmG7y7bp7nJE8O7WjdoAtI"
YOUTUBE_API_KEY = "AIzaSyAQI05z55pZe3ltvltkxq2lbLCW8toELuc"

# Inicializar clientes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase.postgrest.schema("public")

youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

st.set_page_config(page_title="RudaDrag Jukebox", page_icon="🏳️‍🌈")
st.title("🏳️‍🌈 RudaDrag Jukebox")
st.write("Proponé tus temas favoritos y votá los que querés escuchar en la fiesta.")

# --- CONTROL DE ACCESO POR CORREO ---
if "correo_usuario" not in st.session_state:
    st.session_state.correo_usuario = ""

if not st.session_state.correo_usuario:
    st.subheader("🔑 Ingresá para votar o proponer")
    correo_input = st.text_input("Introduce tu correo electrónico:")
    
    if st.button("Ingresar"):
        if re.match(r"[^@]+@[^@]+\.[^@]+", correo_input):
            st.session_state.correo_usuario = correo_input.lower().strip()
            st.rerun()
        else:
            st.error("Por favor, ingresá un correo electrónico válido.")
    st.stop()

st.sidebar.write(f"Conectado como: **{st.session_state.correo_usuario}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.correo_usuario = ""
    st.rerun()

# --- FUNCIONES AUXILIARES ---
def buscar_en_youtube(query):
    try:
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=3
        )
        response = request.execute()
        resultados = []
        for item in response.get("items", []):
            resultados.append({
                "id": item["id"]["videoId"],
                "titulo": item["snippet"]["title"],
                "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
        return resultados
    except Exception as e:
        st.error("Error al conectar con la API de YouTube.")
        return []

# --- INTERFAZ PRINCIPAL (ESTILO Y DISEÑO STITCH) ---

# Inyección de CSS para transformar el diseño de la app
st.markdown("""
    <style>
    /* Fondo general de la app oscuro y tipografía limpia */
    .stApp {
        background-color: #0d0d13;
        color: #f3f4f6;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Personalización gigante y llamativa de las pestañas */
    button[data-baseweb="tab"] {
        background-color: #161622 !important;
        border: 1px solid #232336 !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        margin-right: 10px !important;
        transition: all 0.3s ease;
    }
    
    /* Efecto Hover en las pestañas */
    button[data-baseweb="tab"]:hover {
        border-color: #ff007f !important;
        box-shadow: 0 0 10px rgba(255, 0, 127, 0.2);
    }
    
    /* Pestaña activa (Estilo Drag/Neon) */
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #ff007f 0%, #7928ca 100%) !important;
        border: none !important;
    }
    
    button[data-baseweb="tab"] p {
        font-size: 22px !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px;
        color: #ffffff !important;
    }
    
    /* Tarjetas de canciones (Cards con relieve y bordes suaves) */
    .song-card {
        background-color: #161622;
        border: 1px solid #232336;
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .song-card:hover {
        transform: translateY(-2px);
        border-color: #7928ca;
    }
    
    /* Entradas de texto e inputs estilizados */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #161622 !important;
        color: #ffffff !important;
        border: 1px solid #232336 !important;
        border-radius: 10px !important;
    }
    
    .stTextInput input:focus {
        border-color: #ff007f !important;
        box-shadow: 0 0 0 1px #ff007f !important;
    }
    
    /* Customización de los botones de votación */
    .stButton button {
        border-radius: 10px !important;
        font-weight: bold !important;
        transition: all 0.2s ease !important;
    }
    </style>
""", unsafe_allow_html=True)

# Declaración de pestañas (Proponer primero por defecto)
tab2, tab1 = st.tabs(["🔍 Proponer Tema", "🔥 Lista de Votación"])

with tab2:
    st.markdown("<h2 style='color: #ff007f; font-weight: 800;'>Buscar y añadir canciones</h2>", unsafe_allow_html=True)
    busqueda = st.text_input("¿Qué canción querés buscar?", key="search_yt_input")

    if busqueda:
        try:
            busqueda_db = supabase.table("canciones_votadas").select("*").ilike("titulo", f"%{busqueda}%").execute()
            existentes = busqueda_db.data
        except Exception:
            existentes = []

        if existentes:
            st.markdown("""
                <div style='background-color: rgba(255, 165, 0, 0.1); border-left: 4px solid #ffa500; padding: 12px; border-radius: 8px; margin-bottom: 15px;'>
                    <strong style='color: #ffa500;'>⚠️ ¡Este tema ya fue propuesto!</strong><br>
                    Podés ir a buscarlo y votarlo directamente en la pestaña de 'Lista de Votación' para sumarle puntos.
                </div>
            """, unsafe_allow_html=True)
            for ex in existentes:
                st.markdown(f"• **[{ex['titulo']}]({ex['youtube_url']})** — ({ex['votos_count']} 👍)")
            st.markdown("---")

        st.write("Resultados directos de YouTube:")
        items = buscar_en_youtube(busqueda)
        for item in items:
            # Contenedor visual tipo Card para los resultados
            st.markdown(f"""
                <div class="song-card">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img src="{item['thumbnail']}" style="border-radius: 8px; width: 90px;">
                        <div style="flex-grow: 1;">
                            <a href="{item['url']}" target="_blank" style="color: #ffffff; font-weight: bold; text-decoration: none; font-size: 16px;">{item['titulo']}</a>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Botón nativo de Streamlit posicionado justo debajo para mantener la acción
            if st.button("✨ Proponer este tema", key=f"prop_{item['id']}", use_container_width=True):
                try:
                    supabase.table("canciones_votadas").upsert({
                        "youtube_id": item["id"],
                        "titulo": item["titulo"],
                        "youtube_url": item["url"],
                        "categoria": "General"
                    }, on_conflict="youtube_id").execute()
                    
                    supabase.table("registro_votos").insert({
                        "correo": st.session_state.correo_usuario,
                        "youtube_id": item["id"]
                    }).execute()
                    st.success("¡Tema propuesto con éxito!")
                    st.rerun()
                except Exception:
                    st.info("Ya apoyaste este tema o ya figura en la lista de votación.")

with tab1:
    st.markdown("<h2 style='color: #7928ca; font-weight: 800;'>Ranking de canciones</h2>", unsafe_allow_html=True)
    
    buscar_interno = st.text_input("🔍 Buscar entre los temas ya votados:", placeholder="Escribí parte del título o artista...", key="search_db_input")
    
    canciones = []
    try:
        query_db = supabase.table("canciones_votadas").select("*")
        if buscar_interno:
            query_db = query_db.ilike("titulo", f"%{buscar_interno}%")
            
        response = query_db.order("votos_count", desc=True).execute()
        canciones = response.data
    except APIError as e:
        st.error(f"Error de base de datos: {e.message}")

    if not canciones:
        st.info("No se encontraron canciones en la lista de votación.")
    else:
        for cancion in canciones:
            y_id = cancion["youtube_id"]
            titulo = cancion["titulo"]
            url = cancion["youtube_url"]
            votos = cancion["votos_count"]
            
            # Renderizado de la tarjeta con colores de marca definidos en el proyecto
            st.markdown(f"""
                <div class="song-card" style="border-left: 5px solid #ff007f;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="background-color: #ff007f; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-right: 10px;">
                                {votos} 👍
                            </span>
                            <a href="{url}" target="_blank" style="color: #f3f4f6; font-weight: 600; text-decoration: none; font-size: 18px;">{titulo}</a>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Botón de votación alineado de forma limpia debajo de la tarjeta
            if st.button(f"👍 Dar mi voto", key=f"vote_{y_id}", use_container_width=True):
                try:
                    supabase.table("registro_votos").insert({
                        "correo": st.session_state.correo_usuario,
                        "youtube_id": y_id
                    }).execute()
                    
                    nuevo_total = votos + 1
                    supabase.table("canciones_votadas").update({"votos_count": nuevo_total}).eq("youtube_id", y_id).execute()
                    st.success("¡Voto registrado!")
                    st.rerun()
                except Exception:
                    st.error("Ya votaste por esta canción.")
            st.markdown("---")
