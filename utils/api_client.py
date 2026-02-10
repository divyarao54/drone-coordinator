import requests
import streamlit as st

def call_api(endpoint, method="GET", data=None):
    """Helper function to call backend API"""
    try:
        # Get API URL from session state or default
        api_url = st.session_state.get("API_URL", "http://localhost:8000")
        
        url = f"{api_url}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return None
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None