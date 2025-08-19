import streamlit as st

# App title
st.title("🧮 BMI Calculator")

# Input fields
weight = st.number_input("Enter your weight (kg):", min_value=1.0, format="%.2f")
height = st.number_input("Enter your height (cm):", min_value=1.0, format="%.2f")

# Button to calculate BMI
if st.button("Calculate BMI"):
    height_m = height / 100  # convert cm to meters
    bmi = weight / (height_m ** 2)
    
    # Display BMI
    st.write(f"Your BMI is: **{bmi:.2f}**")

    # Interpretation
    if bmi < 18.5:
        st.warning("You are underweight.")
    elif 18.5 <= bmi < 25:
        st.success("You have a normal weight.")
    elif 25 <= bmi < 30:
        st.info("You are overweight.")
    else:
        st.error("You are obese.")



