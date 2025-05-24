import streamlit as st
from supabase import create_client

# Conexión directa sin caché
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Prueba la conexión
response = supabase.table("predicciones_inundacion").select("*").execute()
st.write(response.data)





