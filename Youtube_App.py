# Streamlit user interface elements
import streamlit as st
import pandas as pd
# Import SQLAlchemy for database interaction
from sqlalchemy import create_engine, text

# Define function to query data from the database
def query_data(sql_query):
    # Establish connection to the database
    engine = create_engine('mysql+mysqlconnector://root:root@localhost/Yoytube_Harvest') # Replace with your database name
    try:
        # Connect to the database and fetch data
        with engine.connect() as connection:
            result = connection.execute(sql_query)
            # Fetch column names from the result object
            columns = result.keys()
            # Construct DataFrame with fetched data and column names
            df = pd.DataFrame(result.fetchall(), columns=columns)
        return df, None
    except Exception as e:
        return None, str(e)

# User interface elements with proper indentation
def display_data():
    query_option = st.selectbox(
        "Select Option:",
        ["Videos of All channels",
         "Channels with the Most Number of Videos",
         "Top 10 Most Viewed Videos",
         "Video and its comments count",
         "Highest likes videos with channel name",
         "Total Likes and Dislikes with Video Names",
         "Total views per channel",
         "Channels that Published Videos in 2022",
         "Average Duration of Videos per Channel",
         "Highest comments"]
    )
    
    if st.button("Result"):
        if query_option == "Videos of All channels":
            sql_query = text("""
                SELECT v.video_name, c.channel_name
                FROM videos v
                LEFT JOIN channels c ON v.channel_id = c.channel_id
            """)
        elif query_option == "Channels with the Most Number of Videos":
            sql_query = text("""
                SELECT channel_name, COUNT(*) AS num_videos
                FROM channels
                JOIN videos ON channels.channel_id = videos.channel_id
                GROUP BY channel_name
                ORDER BY num_videos DESC LIMIT 1            
            """)
        elif query_option == "Top 10 Most Viewed Videos":
            sql_query = text("""
                SELECT v.video_name, v.view_count, c.channel_name
                FROM videos v
                INNER JOIN channels c ON v.channel_id = c.channel_id
                ORDER BY v.view_count DESC
                LIMIT 10;        
            """)
        elif query_option == "Video and its comments count":
            sql_query = text("""
                SELECT v.video_name, count(c.comment_id) as c_count
                FROM videos v
                INNER JOIN comments c ON v.video_id = c.video_id
                GROUP BY v.video_id 
                ORDER BY c_count desc
            """)
        elif query_option == "Highest likes videos with channel name":
            sql_query = text("""
                SELECT v.video_name,v.like_count, c.channel_name
                FROM videos v
                INNER JOIN channels c ON v.channel_id = c.channel_id
                ORDER BY v.like_count DESC
                LIMIT 10;          
            """)
        elif query_option == "Total Likes and Dislikes with Video Names":
            sql_query = text("""
                SELECT video_name,like_count, dislike_count
                FROM videos        
            """)
        elif query_option == "Total views per channel":
            sql_query = text("""
                SELECT channels.channel_name, SUM(videos.view_count) AS total_views
                FROM channels
                LEFT JOIN videos ON channels.channel_id = videos.channel_id
                GROUP BY channels.channel_id       
            """)
        elif query_option == "Channels that Published Videos in 2022":
            sql_query = text("""
                SELECT DISTINCT channels.channel_name
                FROM channels
                INNER JOIN videos ON channels.channel_id = videos.channel_id
                WHERE YEAR(videos.published_date) = 2022;      
            """)
        elif query_option == "Average Duration of Videos per Channel":
            sql_query = text("""
                SELECT 
                    channels.channel_name, 
                    CONCAT(
                        FLOOR(AVG(TIME_TO_SEC(videos.duration)) / 3600), ' hr ',
                        FLOOR(MOD(AVG(TIME_TO_SEC(videos.duration)), 3600) / 60), ' min ',
                        MOD(MOD(AVG(TIME_TO_SEC(videos.duration)), 3600), 60), ' sec'
                    ) AS average_duration
                FROM 
                    channels
                INNER JOIN 
                    videos ON channels.channel_id = videos.channel_id
                GROUP BY 
                    channels.channel_id;
            """)        
        elif query_option == "Highest comments":
            sql_query = text("""
                SELECT videos.video_name, channels.channel_name, videos.comment_count
                FROM videos
                INNER JOIN channels ON videos.channel_id = channels.channel_id
                ORDER BY videos.comment_count DESC
                LIMIT 5;      
            """)  
    
                      
        # Add other cases for different query options...
    
        # Call the query_data function and handle results
        data, error_message = query_data(sql_query)
        if error_message:
            st.error(error_message)
        else:
            if data is not None and not data.empty:
                # Display retrieved data
                st.header("Query Results:")
                st.dataframe(data)
            else:
                st.info("No data found for the selected query.")
