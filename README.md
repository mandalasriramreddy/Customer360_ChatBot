# Customer360_ChatBot

🧑‍💻 Customer360 ChatBot

A Streamlit-based chatbot that converts English questions into SQL queries, runs them against your BigQuery Customer360 table, and returns results in natural language.

🚀 Features

Conversational chatbot (remembers context).

Converts plain English → SQL automatically.

Executes queries directly on Google BigQuery.

Works with Gemini API (default) or OpenAI API (future).

📂 Project Structure
Customer360_ChatBot/
│── app.py               # Main chatbot app
│── key.json             # Google Service Account key (not committed to Git!)
│── README.md            # This file
│── venv/                # Virtual environment (ignored in git)

🛠️ Prerequisites

Python 3.10+ installed

Google Cloud Project with:

BigQuery enabled

Service account key JSON downloaded

Gemini API Key (or OpenAI key if switched later)

⚡ Setup Instructions
1. Clone the repo
git clone <your-repo-url>
cd Customer360_ChatBot

2. Create a virtual environment
python -m venv venv
venv\Scripts\activate   # On Windows
# OR
source venv/bin/activate   # On Mac/Linux

3. Install dependencies
pip install -r requirements.txt


(If you don’t have a requirements.txt, install manually:)

pip install streamlit google-cloud-bigquery google-generativeai pandas

4. Add credentials

Place your Google Service Account key in the project folder as key.json.

Set environment variables before running:

set GOOGLE_APPLICATION_CREDENTIALS=key.json
set GEMINI_API_KEY=your_gemini_api_key_here


(On Mac/Linux use export instead of set)

5. Run the chatbot
streamlit run app.py

💡 Example Usage

Q: How many customers have I acquired in Jan 2025?
A: You have acquired 3566 customers in Jan 2025.

📝 Notes

Replace weezietowelsdaton.Prod_presentation.Customer360 with your actual BigQuery table if needed.

If using OpenAI API, set:

set OPENAI_API_KEY=your_openai_api_key_here


and adjust app.py accordingly.