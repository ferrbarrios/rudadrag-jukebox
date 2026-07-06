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

# --- INTERFAZ PRINCIPAL (PESTAÑAS) ---
# Estilo CSS inyectado para agrandar las etiquetas de las pestañas
st.markdown("""
    <style>
    button[data-baseweb="tab"] p {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# Las pestañas se declaran al revés para que "Proponer Tema" sea el índice 0 (por defecto)
tab2, tab1 = st.tabs(["🔍 Proponer Tema", "🔥 Lista de Votación"])

with tab2:
    st.subheader("Buscar y añadir canciones")
    busqueda = st.text_input("¿Qué canción querés buscar?")

    if busqueda:
        # Primero buscamos coincidencias parciales en Supabase para ahorrar cuota de API
        try:
            busqueda_db = supabase.table("canciones_votadas").select("*").ilike("titulo", f"%{busqueda}%").execute()
            existentes = busqueda_db.data
        except Exception:
            existentes = []

        if existentes:
            st.warning("⚠️ ¡Este tema (o uno muy similar) ya fue propuesto! Podés ir a buscarlo y votarlo directamente en la pestaña de 'Lista de Votación'.")
            for ex in existentes:
                st.markdown(f"• **[{ex['titulo']}]({ex['youtube_url']})** — ({ex['votos_count']} 👍)")
            st.markdown("---")

        # De todas formas ofrecemos los resultados de YouTube por si quiere un video diferente o no es el mismo
        st.write("Resultados directos de YouTube:")
        items = buscar_en_youtube(busqueda)
        for item in items:
            col_thumb, col_txt, col_btn = st.columns([1, 3, 1])
            with col_thumb:
                st.image(item["thumbnail"])
            with col_txt:
                st.markdown(f"**[{item['titulo']}]({item['url']})**")
            with col_btn:
                if st.button("Proponer", key=f"prop_{item['id']}"):
                    try:
                        # Insertamos sin el campo categoría
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
                        st.success("¡Tema propuesto y añadido a la lista!")
                    except Exception:
                        st.info("Ya apoyaste este tema o ya figura en la lista de votación.")

with tab1:
    st.subheader("Ranking de canciones")
    
    # Cuadro de búsqueda exclusivo sobre Supabase para la lista de temas votados
    buscar_interno = st.text_input("🔍 Buscar entre los temas ya votados:", placeholder="Escribí parte del título o artista...")
    
    canciones = []
    
    try:
        query_db = supabase.table("canciones_votadas").select("*")
        
        # Filtro de texto dinámico en Supabase si el usuario escribe algo
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
            
            col_info, col_vote = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"### {votos} 👍 | [{titulo}]({url})")
                st.caption(f"ID: {y_id}")
            
            with col_vote:
                if st.button("Votar", key=f"vote_{y_id}"):
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
