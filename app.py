response = supabase.table("predicciones_inundacion").select("*").execute()
st.write(response.data)





