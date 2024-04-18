import streamlit as st
from StoreDataApp import display_store_data
from Youtube_App import display_data

def main():
    menu_selection = st.sidebar.radio("Menu", ["Store Data", "Show Data"])

    if menu_selection == "Store Data":
        display_store_data()  
    elif menu_selection == "Show Data":  
        display_data()

if __name__ == "__main__":
    main()
