# filename: app.py

import streamlit as st

# Title of the app
st.title("👋 Simple Greeting App")

# Get user input
name = st.text_input("Enter your name:")

# When the button is clicked
if st.button("Greet Me"):
    if name:
        st.success(f"Hello, {name}! 👋 Welcome to Streamlit!")
    else:
        st.warning("Please enter your name first.")
