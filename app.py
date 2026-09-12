import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# Database Setup
conn = sqlite3.connect('events.db', check_same_thread=False)
c = conn.cursor()

# Table Create Karna (Agar pehle se nahi hai)
c.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        club TEXT,
        category TEXT,
        event_date TEXT,
        venue TEXT,
        description TEXT
    )
''')
conn.commit()

# App Title & Layout
st.set_page_config(page_title="Campus Event Hub", layout="wide")
st.title("🎓 College Campus Event Hub")

# Sidebar navigation
menu = ["Browse Events", "Add New Event (Admin)"]
choice = st.sidebar.selectbox("Navigation", menu)

# SECTION 1: ADD NEW EVENT
if choice == "Add New Event (Admin)":
    st.subheader("➕ Add a New Campus Event")
    
    with st.form(key='add_event_form'):
        title = st.text_input("Event Title")
        club = st.text_input("Organizing Club Name")
        category = st.selectbox("Category", ["Tech", "Cultural", "Sports", "Workshop"])
        event_date = st.date_input("Event Date", min_value=date.today())
        venue = st.text_input("Venue / Location")
        description = st.text_area("Event Description")
        
        submit_button = st.form_submit_button(label='Publish Event')
        
        if submit_button:
            if title and club and venue:
                c.execute('''
                    INSERT INTO events (title, club, category, event_date, venue, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (title, club, category, str(event_date), venue, description))
                conn.commit()
                st.success(f"🎉 '{title}' has been successfully published!")
            else:
                st.warning("Please fill out all required fields.")

# SECTION 2: BROWSE EVENTS
elif choice == "Browse Events":
    st.subheader("📅 Upcoming Campus Events")
    
    # Category Filter
    selected_cat = st.selectbox("Filter by Category", ["All", "Tech", "Cultural", "Sports", "Workshop"])
    
    # Database se data fetch karna
    if selected_cat == "All":
        df = pd.read_sql_query("SELECT * FROM events ORDER BY id DESC", conn)
    else:
        df = pd.read_sql_query(f"SELECT * FROM events WHERE category='{selected_cat}' ORDER BY id DESC", conn)
        
    if df.empty:
        st.info("No events found. Be the first to add one from the sidebar!")
    else:
        # Events ko Grid Cards me dikhana
        for index, row in df.iterrows():
            with st.container():
                st.markdown(f"### 📌 {row['title']}")
                col1, col2, col3 = st.columns(3)
                col1.write(f"*Club:* {row['club']}")
                col2.write(f"*Date:* {row['event_date']}")
                col3.write(f"*Venue:* {row['venue']}")
                
                st.write(f"*Category:* {row['category']}")
                st.write(row['description'])
                
                # RSVP Button
                if st.button(f"Register / RSVP", key=f"rsvp_{row['id']}"):
                    st.balloons()
                    st.success("✅ You have successfully registered for this event!")
                st.divider()