#!/usr/bin/env python3
"""
Utility functions for Streamlit app.
"""

import streamlit as st
import os
from pathlib import Path

def load_css():
    """Load custom CSS styles from external file."""
    css_file = Path(__file__).parent / "styles.css"
    
    if css_file.exists():
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        st.markdown(f"""
        <style>
        {css_content}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.error(f"CSS file not found: {css_file}")