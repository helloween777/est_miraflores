import streamlit as st
from supabase import create_client

@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

response = supabase.table("predicciones_inundacion").select("*").execute()
st.write(response.data)





