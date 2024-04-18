import streamlit as st
import mysql.connector
from googleapiclient.discovery import build
import googleapiclient.errors

# Establish MySQL connection
cnx = mysql.connector.connect(user='root', password='root',
                               host='localhost',
                               database='Yoytube_Harvest')
cursor = cnx.cursor()

# Function to create tables if they don't exist
def create_tables():
    # Table creation queries
    channel_table_query = """
        CREATE TABLE IF NOT EXISTS channels (
            channel_id VARCHAR(255) PRIMARY KEY,
            channel_name VARCHAR(255),
            channel_views INT,
            channel_description TEXT,
            channel_status VARCHAR(50),
            channel_type VARCHAR(50)
        )
    """
    playlist_table_query = """
        CREATE TABLE IF NOT EXISTS playlists (
            playlist_id VARCHAR(255) PRIMARY KEY,
            channel_id VARCHAR(255),
            playlist_name VARCHAR(255),
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        )
    """
    video_table_query = """
        CREATE TABLE IF NOT EXISTS videos (
            video_id VARCHAR(255) PRIMARY KEY,
            channel_id VARCHAR(255),
            playlist_id VARCHAR(255),
            video_name VARCHAR(255),
            video_description TEXT,
            published_date DATETIME,
            view_count INT,
            like_count INT,
            dislike_count INT,
            favorite_count INT,
            comment_count INT,
            duration TIME,
            thumbnail BLOB,
            caption_status VARCHAR(50),
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id)
        )
    """
    comment_table_query = """
        CREATE TABLE IF NOT EXISTS comments (
            comment_id VARCHAR(255) PRIMARY KEY,
            video_id VARCHAR(255),
            comment_text TEXT,
            comment_author VARCHAR(255),
            comment_published_at DATETIME,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    """
    # Execute table creation queries
    cursor.execute(channel_table_query)
    cursor.execute(playlist_table_query)
    cursor.execute(video_table_query)
    cursor.execute(comment_table_query)
    cnx.commit()

# Function to get channel info
def get_channel_info(channel_id, api_key):
      youtube = build('youtube', 'v3', developerKey=api_key)
      channel_info = {}
      channel_request = youtube.channels().list(
       part='snippet,contentDetails,statistics',
       id=channel_id
      )
      channel_response = channel_request.execute()

      if 'items' in channel_response and len(channel_response['items']) > 0:
        channel_data = channel_response['items'][0]
        channel_info['channel_id'] = channel_data['id']
        channel_info['channel_name'] = channel_data['snippet']['title']
        channel_info['channel_views'] = channel_data['statistics']['viewCount']
        channel_info['channel_description'] = channel_data['snippet']['description']
        channel_info['channel_status'] = channel_data['snippet'].get('status', 'Unknown')
        channel_info['channel_type'] = infer_channel_type(channel_data)
    
      # Retrieve playlists for the channel
      playlist_info = []
      playlist_request = youtube.playlists().list(
        part='snippet',
        channelId=channel_id,
        maxResults=200
      )
      playlist_response = playlist_request.execute()
      print(playlist_response)
      if 'items' in playlist_response:
        for playlist_item in playlist_response['items']:
          playlist_info.append({
            'playlist_id': playlist_item['id'],
            'channel_id': channel_id,
            'playlist_name': playlist_item['snippet']['title']
          })
    
      # Retrieve uploaded videos for the channel
      video_info = []
      video_request = youtube.search().list(
        part='snippet',
        channelId=channel_id,
        type='video',
        maxResults=200
      )
      """video_request = youtube.videos().list(
          part='snippet,contentDetails,statistics',
          channelId=channel_id,
          maxResults=50
      )
      video_response = video_request.execute()"""
    
      video_response = video_request.execute()    
      print(video_response)
      # Accumulate comments for all videos
      comments_info = []    
      if 'items' in video_response:
        for video_item in video_response['items']:
          video_id = video_item['id']['videoId']    
          # Retrieve video details
          video_details_request = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
          )
          video_details_response = video_details_request.execute()    
          if 'items' in video_details_response:
            video_data = video_details_response['items'][0]['snippet']
            video_statistics = video_details_response['items'][0]['statistics']
    
            # Retrieve comments for each video
            try:
                comments_request = youtube.commentThreads().list(
                  part='snippet',
                  videoId=video_id
                )
                comments_response = comments_request.execute()
        
                if 'items' in comments_response:
                  for comment_item in comments_response['items']:
                    comment_snippet = comment_item['snippet']['topLevelComment']['snippet']
                    comments_info.append({
                      'comment_id': comment_item['id'],
                      'video_id': video_id,
                      'comment_text': comment_snippet['textDisplay'],
                      'comment_author': comment_snippet['authorDisplayName'],
                      'comment_published_at': comment_snippet['publishedAt']
                    })
            except googleapiclient.errors.HttpError as e:
                if e.resp.status == 403:
                    print(f"Comments are disabled for video {video_id}")
                    # You can handle this situation as you see fit, such as skipping the video
                else:
                    raise e  # Raise the exception if it's not a 403 error
            video_info.append({
              'video_id': video_id,
              'playlist_id': video_item['snippet'].get('playlistId'),
              'video_name': video_data['title'],
              'video_description': video_data['description'],
              'published_date': video_data['publishedAt'],
              'view_count': video_statistics.get('viewCount', 0),
              'like_count': video_statistics.get('likeCount', 0),
              'dislike_count': video_statistics.get('dislikeCount', 0),
              'favorite_count': video_statistics.get('favoriteCount', 0),
              'comment_count': video_statistics.get('commentCount', 0),
              'duration': format_duration(video_details_response['items'][0]['contentDetails']['duration']),
              #print("video_details_response:", video_details_response)  # Check the structure of video_details_response
              'thumbnail': video_data['thumbnails']['default']['url'],
              'caption_status': video_details_response['items'][0]['contentDetails'].get('caption', 'Not available')
              #print("video_details_response:", video_details_response)  # Check the structure of video_details_response
            })     
      return channel_info, playlist_info, video_info, comments_info

def format_duration(duration):
    # Remove the leading "PT" and trailing "S"
    duration = duration[2:]

    # Initialize hours, minutes, and seconds
    hours = 0
    minutes = 0
    seconds = 0

    # Check if 'H' (hours) is present
    if 'H' in duration:
        hours_str, remaining = duration.split("H")
        hours = int(hours_str)
        duration = remaining

    # Check if 'M' (minutes) is present
    if 'M' in duration:
        # Split duration into minutes and potentially seconds
        minutes_str, remaining = duration.split("M")
        minutes = int(minutes_str)

        # Check if there are seconds
        if 'S' in remaining:
            seconds_str = remaining.split("S")[0]
            seconds = int(seconds_str)

    # If only seconds are present
    elif 'S' in duration:
        seconds_str = duration.split("S")[0]
        seconds = int(seconds_str)

    # Convert excess seconds to minutes
    if seconds >= 60:
        minutes += seconds // 60
        seconds %= 60

    # Convert excess minutes to hours
    if minutes >= 60:
        hours += minutes // 60
        minutes %= 60

    # Return the formatted duration

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def infer_channel_type(channel_data):
    if 'customUrl' in channel_data['snippet']:
      return 'User'
    else:
      return 'Other'

# Streamlit UI
# Function to display store data in Streamlit
def display_store_data():
    create_tables()
    st.title("Store Data")

    # Input form for YouTube Channel ID
    channel_id = st.text_input('Enter YouTube Channel ID:')
    api_key = 'AIzaSyBmCzmnDo4kUybZpg3j0WohwUKejBp7RP4'  # Update with your YouTube API key

    if st.button('Submit'):
        if channel_id:
            # Call function to fetch and store channel data
            channel_info, playlist_info, video_info, comments_info = get_channel_info(channel_id, api_key)
            
            # Insert channel data into the database
            channel_insert_query = ("INSERT IGNORE INTO channels "
                            "(channel_id, channel_name, channel_views, channel_description, channel_status, channel_type) "
                            "VALUES (%s, %s, %s, %s, %s, %s)")
            channel_data = (channel_info['channel_id'], channel_info['channel_name'], channel_info['channel_views'],
                        channel_info['channel_description'], channel_info['channel_status'], channel_info['channel_type'])
            #print("Inserting channel data:", channel_data)
            cursor.execute(channel_insert_query, channel_data)
            cnx.commit()

            # Insert playlist data into the database
            for playlist in playlist_info:
              playlist_insert_query = ("INSERT IGNORE INTO playlists "
                               "(playlist_id, channel_id, playlist_name) "
                               "VALUES (%s, %s, %s)")
              # Access playlist information using dictionary-style syntax
              playlist_data = (playlist['playlist_id'], channel_id, playlist['playlist_name'])
              print("Inserting playlist data:", playlist_data)
              cursor.execute(playlist_insert_query, playlist_data)
              cnx.commit()

            # Insert video data into the database
            for video in video_info:
              video_insert_query = ("INSERT IGNORE INTO videos "
                         "(video_id, channel_id, playlist_id, video_name, video_description, published_date, "
                         "view_count, like_count, dislike_count, favorite_count, comment_count, "
                         "duration, thumbnail, caption_status) "
                         "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
              video_data = (video['video_id'], channel_id, video['playlist_id'], video['video_name'], video['video_description'],
                     video['published_date'], video['view_count'], video['like_count'], video['dislike_count'],
                     video['favorite_count'], video['comment_count'], video['duration'], video['thumbnail'],
                     video['caption_status'])
             
              #print("Inserting video data:", video_data)
                
              try:
                  cursor.execute(video_insert_query, video_data)
                  cnx.commit()
              except mysql.connector.Error as err:
                  print("Error:", err)

            # Insert comment data into the database
            for comment in comments_info:
              #print(comment)
              from datetime import datetime
              # Convert the datetime string to MySQL-compatible format
              comment_published_at = datetime.strptime(comment['comment_published_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S')
               
              # Construct and execute the SQL query
              comment_insert_query = ("INSERT IGNORE INTO comments "
                          "(comment_id, video_id, comment_text, comment_author, comment_published_at) "
                          "VALUES (%s, %s, %s, %s, %s)")
              comment_data = (comment['comment_id'], comment['video_id'], comment['comment_text'],
                      comment['comment_author'], comment_published_at)
              cursor.execute(comment_insert_query, comment_data)
            cnx.commit()

            st.success('Data stored successfully!')
        else:
            st.error('Failed to fetch data. Please check the YouTube Channel ID.')

# Streamlit UI and main function
def main():
    create_tables()  # Call to create tables if they don't exist

    st.title('YouTube Data Harvest')

    # Input form for YouTube Channel ID
    channel_id = st.text_input('Enter YouTube Channel ID:')
    api_key = 'AIzaSyBmCzmnDo4kUybZpg3j0WohwUKejBp7RP4'  # Update with your YouTube API key

    if st.button('Submit'):
        if channel_id:
            # Call function to fetch and store channel data
            channel_info, playlist_info, video_info, comments_info = get_channel_info(channel_id, api_key)
            
            # Insert channel data into the database
            channel_insert_query = ("INSERT IGNORE INTO channels "
                            "(channel_id, channel_name, channel_views, channel_description, channel_status, channel_type) "
                            "VALUES (%s, %s, %s, %s, %s, %s)")
            channel_data = (channel_info['channel_id'], channel_info['channel_name'], channel_info['channel_views'],
                        channel_info['channel_description'], channel_info['channel_status'], channel_info['channel_type'])
            #print("Inserting channel data:", channel_data)
            cursor.execute(channel_insert_query, channel_data)
            cnx.commit()

            # Insert playlist data into the database
            for playlist in playlist_info:
              playlist_insert_query = ("INSERT IGNORE INTO playlists "
                               "(playlist_id, channel_id, playlist_name) "
                               "VALUES (%s, %s, %s)")
              # Access playlist information using dictionary-style syntax
              playlist_data = (playlist['playlist_id'], channel_id, playlist['playlist_name'])
              print("Inserting playlist data:", playlist_data)
              cursor.execute(playlist_insert_query, playlist_data)
              cnx.commit()

            # Insert video data into the database
            for video in video_info:
              video_insert_query = ("INSERT IGNORE INTO videos "
                         "(video_id, channel_id, playlist_id, video_name, video_description, published_date, "
                         "view_count, like_count, dislike_count, favorite_count, comment_count, "
                         "duration, thumbnail, caption_status) "
                         "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
              video_data = (video['video_id'], channel_id, video['playlist_id'], video['video_name'], video['video_description'],
                     video['published_date'], video['view_count'], video['like_count'], video['dislike_count'],
                     video['favorite_count'], video['comment_count'], video['duration'], video['thumbnail'],
                     video['caption_status'])
             
              #print("Inserting video data:", video_data)
                
              try:
                  cursor.execute(video_insert_query, video_data)
                  cnx.commit()
              except mysql.connector.Error as err:
                  print("Error:", err)

            # Insert comment data into the database
            for comment in comments_info:
              #print(comment)
              from datetime import datetime
              # Convert the datetime string to MySQL-compatible format
              comment_published_at = datetime.strptime(comment['comment_published_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S')
               
              # Construct and execute the SQL query
              comment_insert_query = ("INSERT IGNORE INTO comments "
                          "(comment_id, video_id, comment_text, comment_author, comment_published_at) "
                          "VALUES (%s, %s, %s, %s, %s)")
              comment_data = (comment['comment_id'], comment['video_id'], comment['comment_text'],
                      comment['comment_author'], comment_published_at)
              cursor.execute(comment_insert_query, comment_data)
            cnx.commit()

            st.success('Data stored successfully!')
        else:
            st.error('Failed to fetch data. Please check the YouTube Channel ID.')

if __name__ == '__main__':
    main()
