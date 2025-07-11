import os
import logging
import requests
import json
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, flash

# --- Flask App Setup ---
app = Flask(__name__)
# A secret key is needed for flashing messages. For production, it's better to set this
# as an environment variable in Railway's "Variables" tab.
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)

# --- Core Logic: TED.com Scraping ---
def find_ted_video_url(ted_url: str) -> str | None:
    """
    Scrapes a TED.com talk page to find the direct MP4 video URL.
    """
    logging.info(f"Attempting to scrape URL: {ted_url}")
    try:
        # **FIX:** The User-Agent string must be on a single line.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(ted_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})

        if not next_data_script:
            logging.error("Could not find '__NEXT_DATA__' script tag.")
            return None

        data = json.loads(next_data_script.string)
        player_data_str = data.get('props', {}).get('pageProps', {}).get('videoData', {}).get('playerData', '')

        if not player_data_str:
            logging.error("Could not find 'playerData' in JSON structure.")
            return None

        player_data = json.loads(player_data_str)
        downloads = player_data.get('nativeDownloads')

        if downloads and 'high' in downloads:
            logging.info("Found high-quality video URL.")
            return downloads['high']
        elif downloads and 'medium' in downloads:
            logging.info("Found medium-quality video URL.")
            return downloads['medium']
        else:
            logging.warning("No high/medium quality downloads found.")
            return None

    except Exception as e:
        logging.error(f"An error occurred during scraping: {e}")
        return None

# --- Flask Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        ted_url = request.form.get('url')
        if not ted_url or "ted.com/talks/" not in ted_url:
            flash("Please enter a valid TED talk URL.", "error")
            return redirect(url_for('index'))
        
        video_url = find_ted_video_url(ted_url)

        if video_url:
            # Render the page again with the success message and download link
            return render_template('index.html', video_url=video_url, original_url=ted_url)
        else:
            # If the video URL couldn't be found
            flash("Sorry, I couldn't find a downloadable video from that link. Please check the URL or try another.", "error")
            return redirect(url_for('index'))

    return render_template('index.html')

# This block is only for running the app on your local machine.
# Railway does NOT use this. It uses the 'Procfile' instead.
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)