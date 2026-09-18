import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import qrcode
from io import BytesIO
from datetime import datetime
import urllib.parse
from streamlit_qrcode_scanner import qrcode_scanner

# 1. Page Configuration & Custom CSS
st.set_page_config(page_title="College Campus Event Hub", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        border-left: 5px solid #2563eb;
        padding: 18px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .event-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .badge-seats {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-soldout {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Database Setup & Auto-Migrations
conn = sqlite3.connect('events.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        date TEXT,
        time TEXT,
        venue TEXT,
        description TEXT,
        image_url TEXT,
        capacity INTEGER DEFAULT 100,
        organizer TEXT DEFAULT 'Campus Student Council',
        speaker TEXT DEFAULT 'N/A'
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS rsvp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        user_name TEXT,
        user_email TEXT,
        ticket_code TEXT,
        attended INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        user_name TEXT,
        rating INTEGER,
        comments TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# Helper Functions
def generate_google_calendar_url(title, description, venue, date_str, time_str):
    try:
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except:
        start_dt = datetime.now()
    dates = f"{start_dt.strftime('%Y%m%dT%H%M%SZ')}/{start_dt.strftime('%Y%m%dT%H%M%SZ')}"
    params = {
        'action': 'TEMPLATE',
        'text': title,
        'details': description,
        'location': venue,
        'dates': dates
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# Application Header
st.title("🎓 College Campus Event Hub")
st.caption("Discover, organize, and participate in campus events effortlessly.")

# 3. Admin Authentication
if 'admin_logged_in' not in st.session_state:
    st.session_state['admin_logged_in'] = False

st.sidebar.title("Navigation & Admin")

if not st.session_state['admin_logged_in']:
    st.sidebar.subheader("🔒 Admin Login")
    admin_user = st.sidebar.text_input("Username", key="admin_u")
    admin_pass = st.sidebar.text_input("Password", type="password", key="admin_p")
    if st.sidebar.button("Login"):
        if admin_user == "admin" and admin_pass == "admin123":
            st.session_state['admin_logged_in'] = True
            st.sidebar.success("Logged in successfully!")
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials!")
else:
    st.sidebar.success("Logged in as Admin")
    if st.sidebar.button("Logout"):
        st.session_state['admin_logged_in'] = False
        st.rerun()

menu_options = ["Dashboard & Browse", "Register / RSVP", "Submit Feedback"]
if st.session_state['admin_logged_in']:
    menu_options.extend(["Add New Event", "Manage Events", "Analytics & CSV Export", "Attendance Scanner"])

choice = st.sidebar.radio("Go to", menu_options)

# 4. Feature: Dashboard & Browse
if choice == "Dashboard & Browse":
    c.execute("SELECT COUNT(*) FROM events")
    total_events = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rsvp")
    total_rsvps = c.fetchone()[0]
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"<div class='metric-card'><h4>Total Active Events</h4><h2>{total_events}</h2></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><h4>Total Registrations</h4><h2>{total_rsvps}</h2></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'><h4>Platform Status</h4><h2>🟢 Live</h2></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.header("📌 Upcoming Campus Events")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Search Events (by Title, Venue, or Organizer)", "")
    with col2:
        category_filter = st.selectbox("Filter by Category", ["All", "Tech", "Cultural", "Sports", "Workshop"])

    query = "SELECT * FROM events WHERE (title LIKE ? OR venue LIKE ? OR organizer LIKE ?)"
    params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]
    
    if category_filter != "All":
        query += " AND category = ?"
        params.append(category_filter)
        
    query += " ORDER BY date ASC"
    c.execute(query, params)
    events = c.fetchall()

    if not events:
        st.info("No matching events found!")
    else:
        for ev in events:
            c.execute("SELECT COUNT(*) FROM rsvp WHERE event_id = ?", (ev[0],))
            rsvp_count = c.fetchone()[0]
            capacity = ev[8] if len(ev) > 8 and ev[8] else 100
            seats_left = capacity - rsvp_count
            organizer = ev[9] if len(ev) > 9 and ev[9] else 'Campus Student Council'
            speaker = ev[10] if len(ev) > 10 and ev[10] else 'N/A'

            # Calculate Average Rating for Event
            c.execute("SELECT AVG(rating), COUNT(*) FROM feedback WHERE event_id = ?", (ev[0],))
            rating_res = c.fetchone()
            avg_rating = rating_res[0]
            total_reviews = rating_res[1]

            with st.container():
                st.markdown("<div class='event-card'>", unsafe_allow_html=True)
                st.subheader(f"🎉 {ev[1]} ({ev[2]})")
                
                if avg_rating:
                    st.write(f"⭐ *Average Rating:* {round(avg_rating, 1)} / 5 ({total_reviews} reviews)")
                else:
                    st.write("⭐ *Average Rating:* No reviews yet")

                if ev[7]:
                    st.image(ev[7], width=400)
                
                c_a, c_b, c_c = st.columns(3)
                c_a.write(f"📅 *Date:* {ev[3]}")
                c_b.write(f"⏰ *Time:* {ev[4]}")
                c_c.write(f"📍 *Venue:* {ev[5]}")

                st.write(f"🎤 *Speaker:* {speaker} | 👥 *Organizer:* {organizer}")
                st.write(f"📝 {ev[6]}")

                # Google Calendar Button
                cal_url = generate_google_calendar_url(ev[1], ev[6], ev[5], ev[3], ev[4])
                st.markdown(f"[📅 Add to Google Calendar]({cal_url})", unsafe_allow_html=True)

                if seats_left > 0:
                    st.markdown(f"<span class='badge-seats'>🎟️ Seats Remaining: {seats_left} / {capacity}</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='badge-soldout'>🚫 HOUSEFULL</span>", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

# 5. Feature: Registration with QR Ticket Generation
elif choice == "Register / RSVP":
    st.header("🎟️ Event Registration & QR Ticket")
    c.execute("SELECT id, title, capacity FROM events")
    event_list = c.fetchall()
    
    if not event_list:
        st.info("No active events for registration.")
    else:
        event_dict = {ev[1]: (ev[0], ev[2]) for ev in event_list}
        selected_title = st.selectbox("Select Event", list(event_dict.keys()))
        event_id, capacity = event_dict[selected_title]

        c.execute("SELECT COUNT(*) FROM rsvp WHERE event_id = ?", (event_id,))
        seats_left = capacity - c.fetchone()[0]

        if seats_left <= 0:
            st.error("🚫 Registration Closed! Event is Housefull.")
        else:
            st.info(f"Available Seats: *{seats_left} / {capacity}*")
            
            with st.form("rsvp_form", clear_on_submit=False):
                user_name = st.text_input("Full Name*")
                user_email = st.text_input("Email*")
                submit_rsvp = st.form_submit_button("Generate Ticket & Register")

            if submit_rsvp:
                if user_name.strip() and user_email.strip():
                    ticket_code = f"TICK-{event_id}-{int(datetime.now().timestamp())}"
                    c.execute("INSERT INTO rsvp (event_id, user_name, user_email, ticket_code) VALUES (?, ?, ?, ?)",
                              (event_id, user_name, user_email, ticket_code))
                    conn.commit()
                    
                    st.session_state['last_ticket'] = ticket_code
                    st.session_state['last_user'] = user_name
                    st.success(f"Successfully registered for {selected_title}!")
                else:
                    st.error("Please enter Name and Email.")

            if 'last_ticket' in st.session_state:
                ticket_code = st.session_state['last_ticket']
                qr_bytes = generate_qr_code(ticket_code)
                st.image(qr_bytes, caption=f"Your Entry Pass (Ticket ID: {ticket_code})", width=200)
                st.download_button(label="📥 Download Ticket QR Code", data=qr_bytes, file_name=f"{ticket_code}.png", mime="image/png")

# 6. Feature: Post-Event Ratings & Feedback
elif choice == "Submit Feedback":
    st.header("⭐ Post-Event Feedback")
    c.execute("SELECT id, title FROM events")
    events = c.fetchall()
    if not events:
        st.info("No events found.")
    else:
        event_opts = {ev[1]: ev[0] for ev in events}
        selected_ev = st.selectbox("Select Event to Rate", list(event_opts.keys()))
        
        with st.form("feedback_form", clear_on_submit=True):
            user_name = st.text_input("Your Name (Optional)")
            rating = st.slider("Rating (1 = Poor, 5 = Excellent)", 1, 5, 5)
            comments = st.text_area("Your Review / Feedback")
            fb_submit = st.form_submit_button("Submit Review")

            if fb_submit:
                c.execute("INSERT INTO feedback (event_id, user_name, rating, comments) VALUES (?, ?, ?, ?)",
                          (event_opts[selected_ev], user_name or "Anonymous", rating, comments))
                conn.commit()
                st.success("Thank you for your feedback!")

# 7. Add New Event (Admin Only)
elif choice == "Add New Event" and st.session_state['admin_logged_in']:
    st.header("➕ Create Professional Event")
    with st.form("add_form", clear_on_submit=True):
        col_t, col_c = st.columns(2)
        with col_t:
            title = st.text_input("Event Title*")
        with col_c:
            category = st.selectbox("Category", ["Tech", "Cultural", "Sports", "Workshop"])
        
        col_d, col_tm, col_cap = st.columns(3)
        with col_d:
            event_date = st.date_input("Event Date")
        with col_tm:
            event_time = st.time_input("Event Time")
        with col_cap:
            capacity = st.number_input("Total Seat Capacity", min_value=5, max_value=2000, value=100)

        venue = st.text_input("Venue / Location*")
        
        col_o, col_s = st.columns(2)
        with col_o:
            organizer = st.text_input("Organizer", "Campus Student Council")
        with col_s:
            speaker = st.text_input("Guest Speaker", "N/A")

        image_url = st.text_input("Poster Image Link/URL (Optional)")
        description = st.text_area("Event Description")
        submit = st.form_submit_button("Publish Event")

        if submit and title.strip() and venue.strip():
            c.execute("""
                INSERT INTO events (title, category, date, time, venue, description, image_url, capacity, organizer, speaker)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, category, str(event_date), str(event_time), venue, description, image_url, capacity, organizer, speaker))
            conn.commit()
            st.success("Event Published!")
            st.rerun()

# 8. Manage Events (Admin Only)
elif choice == "Manage Events" and st.session_state['admin_logged_in']:
    st.header("⚙️ Manage & Delete Events")
    c.execute("SELECT id, title FROM events")
    events = c.fetchall()
    if events:
        event_options = {ev[1]: ev[0] for ev in events}
        selected_label = st.selectbox("Select Event to Delete", list(event_options.keys()))
        if st.button("Delete Event", type="primary"):
            e_id = event_options[selected_label]
            c.execute("DELETE FROM events WHERE id=?", (e_id,))
            c.execute("DELETE FROM rsvp WHERE event_id=?", (e_id,))
            c.execute("DELETE FROM feedback WHERE event_id=?", (e_id,))
            conn.commit()
            st.success("Event deleted!")
            st.rerun()

# 9. Feature: Analytics Dashboard, Reviews & Export
elif choice == "Analytics & CSV Export" and st.session_state['admin_logged_in']:
    st.header("📊 Interactive Analytics & Export")
    
    # Registration Table
    c.execute("""
        SELECT events.title as Event_Title, rsvp.user_name as Student_Name, rsvp.user_email as Email, 
               rsvp.ticket_code as Ticket_ID, rsvp.attended as Attended_Status
        FROM rsvp JOIN events ON rsvp.event_id = events.id
    """)
    rsvps = c.fetchall()
    
    if rsvps:
        st.subheader("📋 Registrations Data")
        df = pd.DataFrame(rsvps, columns=["Event Title", "Student Name", "Email", "Ticket ID", "Attended Status"])
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Registrations (CSV)", data=csv, file_name="registrations.csv", mime="text/csv")
    else:
        st.info("No registration data available yet.")

    # Student Reviews Table
    st.markdown("---")
    st.subheader("💬 Student Reviews & Ratings")
    c.execute("""
        SELECT events.title, feedback.user_name, feedback.rating, feedback.comments, feedback.submitted_at 
        FROM feedback JOIN events ON feedback.event_id = events.id ORDER BY feedback.submitted_at DESC
    """)
    fb_data = c.fetchall()
    if fb_data:
        fb_df = pd.DataFrame(fb_data, columns=["Event Title", "Student Name", "Rating", "Comments", "Submitted At"])
        st.dataframe(fb_df, use_container_width=True)
    else:
        st.info("No feedback submitted yet.")

    # Plotly Charts
    st.markdown("---")
    st.subheader("📈 Event Category Distribution")
    c.execute("SELECT category, COUNT(*) FROM events GROUP BY category")
    cat_data = c.fetchall()
    if cat_data:
        cat_df = pd.DataFrame(cat_data, columns=["Category", "Count"])
        fig_pie = px.pie(cat_df, values="Count", names="Category", title="Events Distribution by Category")
        st.plotly_chart(fig_pie, use_container_width=True)

# 10. Feature: Attendance Scanner (Admin Only)
elif choice == "Attendance Scanner" and st.session_state['admin_logged_in']:
    st.header("📷 Live Gate Attendance Camera Scanner")
    st.write("Scan the student's QR code using your device camera or enter manually below.")

    # Live Camera Scanner Component
    scanned_code = qrcode_scanner(key="qr_scanner")

    # Manual Input Fallback
    ticket_input = st.text_input("Manual Ticket ID Input (e.g., TICK-1-...)", value=scanned_code if scanned_code else "")
    
    if st.button("Verify & Mark Present") or scanned_code:
        final_code = scanned_code if scanned_code else ticket_input.strip()
        
        if final_code:
            c.execute("SELECT id, user_name, attended FROM rsvp WHERE ticket_code = ?", (final_code,))
            record = c.fetchone()
            if record:
                if record[2] == 1:
                    st.warning(f"⚠️ Ticket already scanned! Student: {record[1]}")
                else:
                    c.execute("UPDATE rsvp SET attended = 1 WHERE ticket_code = ?", (final_code,))
                    conn.commit()
                    st.success(f"✅ Verified! Attendance marked for {record[1]}")
            else:
                st.error("❌ Invalid Ticket ID!")