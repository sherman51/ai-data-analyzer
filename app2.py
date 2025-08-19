import streamlit as st

#Setup
st.title("BMI Calculator")
st.sidebar.title("Enter your details:")
height = st.sidebar.number_input("Height (in m)", min_value = 0.5, max_value = 2.5, step = 0.01)
weight = st.sidebar.number_input("Weight (in kg)", min_value = 10.0, max_value = 300.0, step = 0.1)


# Calculate BMI
if st.sidebar.button("Calculate BMI")
bmi = weight/(height**2)

st.write("Your BMI is:**bmi"

