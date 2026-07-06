import streamlit as st
from supabase import create_client, Client
from googleapiclient.discovery import build
import re

# --- CONFIGURACIÓN DE APIS (Reemplazar con tus credenciales) ---
# Es mejor usar st.secrets para producción, pero acá va la estructura de inicio:
SUPABASE_URL = "https://iolidngaqcjtumkcrtcx.supabase.co/rest/v1/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvbGlkbmdhcWNqdHVta2NydGN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzNTcwODUsImV4cCI6MjA5ODkzMzA4NX0.8RQU3yZvhjoZXQh6uZkDfcmG7y7bp7nJE8O7WjdoAtI"
YOUTUBE_API_KEY = "AIzaSyAQI05z55pZe3ltvltkxq2lbLCW8toELuc"

# Inicializar clientes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
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
    
    # Validación simple de formato de email
    if st.button("Ingresar"):
        if re.match(r"[^@]+@[^@]+\.[^@]+", correo_input):
            st.session_state.correo_usuario = correo_input.lower().strip()
            st.rerun()
        else:
            st.error("Por favor, ingresá un correo electrónico válido.")
    st.stop() # Frena la app acá si no se identificó

# Si ya ingresó, mostrar saludo y botón de salir
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
tab1, tab2 = st.tabs(["🔥 Lista de Votación", "🔍 Proponer Tema"])

with tab2:
    st.subheader("Buscar y añadir canciones")
    busqueda = st.text_input("¿Qué canción querés buscar?")
    categoria_sel = st.selectbox("Categoría del tema:", ["Pop/Diva", "Reggaeton/RKT", "Electrónica", "Clásicos Bizarros"])

    if busqueda:
        items = buscar_en_youtube(busqueda)
        for item in items:
            col_thumb, col_txt, col_btn = st.columns([1, 3, 1])
            with col_thumb:
                st.image(item["thumbnail"])
            with col_txt:
                st.markdown(f"**[{item['titulo']}]({item['url']})**")
            with col_btn:
                if st.button("Proponer", key=f"prop_{item['id']}"):
                    # 1. Intentar insertar la canción
                    try:
                        supabase.table("canciones_votadas").insert({
                            "youtube_id": item["id"],
                            "titulo": item["titulo"],
                            "youtube_url": item["url"],
                            "categoria": categoria_sel,
                            "votos_count": 1
                        }).execute()
                        
                        # Registrar el voto inicial del creador
                        supabase.table("registro_votos").insert({
                            "correo": st.session_state.correo_usuario,
                            "youtube_id": item["id"]
                        }).execute()
                        st.success("¡Tema propuesto y añadido a la lista!")
                    except Exception:
                        # Si ya existía la canción, solo le intentamos sumar el voto de este usuario
                        st.info("Este tema ya estaba propuesto. ¡Andá a la pestaña de votación para darle tu apoyo!")

with tab1:
    st.subheader("Ranking de canciones")
    
    # Filtro opcional por categoría
    filtro_categoria = st.selectbox("Filtrar por estilo:", ["Todos", "Pop/Diva", "Reggaeton/RKT", "Electrónica", "Clásicos Bizarros"])
    
    # Traer canciones ordenadas de Mayor a Menor votos
    query_db = supabase.table("canciones_votadas").select("*")
    if filtro_categoria != "Todos":
        query_db = query_db.eq("categoria", filtro_categoria)
    
    # Orden estricto: Más votados arriba
    canciones = query_db.order("votos_count", desc=True).execute().data

    if not canciones:
        st.info("Todavía no hay canciones propuestas en esta categoría.")
    else:
        for cancion in canciones:
            # Traer datos de la canción
            y_id = cancion["youtube_id"]
            titulo = cancion["titulo"]
            url = cancion["youtube_url"]
            votos = cancion["votos_count"]
            cat = cancion["categoria"]
            
            # Formato visual de la fila
            col_info, col_vote = st.columns([4, 1])
            
            with col_info:
                # Mostramos el título indexado a su URL pública de YouTube directamente
                st.markdown(f"### {votos} 👍 | [{titulo}]({url})")
                st.caption(f"Categoría: {cat} | ID: {y_id}")
            
            with col_vote:
                if st.button("Votar", key=f"vote_{y_id}"):
                    # Intentar registrar el voto en la tabla relacional
                    try:
                        supabase.table("registro_votos").insert({
                            "correo": st.session_state.correo_usuario,
                            "youtube_id": y_id
                        }).execute()
                        
                        # Si no falla por duplicado, actualizamos el contador en la tabla principal
                        nuevo_total = votos + 1
                        supabase.table("canciones_votadas").update({"votos_count": nuevo_total}).eq("youtube_id", y_id).execute()
                        st.success("¡Voto registrado!")
                        st.rerun()
                    except Exception:
                        st.error("Ya votaste por esta canción.")
            st.markdown("---")
