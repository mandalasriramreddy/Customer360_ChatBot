import streamlit as st
from google.cloud import bigquery
import google.generativeai as genai
import os
import re

# ----------------------------
# 🔑 Setup keys and clients
# ----------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
bq_client = bigquery.Client()

# ----------------------------
# ⚙️ Streamlit UI Setup
# ----------------------------
st.title("💬 Customer360 Chatbot (Context-Aware with BigQuery)")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# ----------------------------
# Helpers
# ----------------------------
def clean_sql(text: str) -> str:
    """Remove markdown-style code block wrappers."""
    text = re.sub(r"```sql", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    return text.strip()

def generate_sql(user_question: str, chat_history: list) -> str:
    """Generate SQL from natural language using Gemini with context awareness."""
    schema = """
    Table: `weezietowelsdaton.Prod_presentation.Customer360`
    Columns:
    - email (STRING): Customer email
    - orders (INT64): Number of orders placed
    - total_net_sales (FLOAT64): Total sales amount
    - acquisition_date (DATE): Date customer was acquired
    - acquisition_product (STRING): First product purchased
    - most_purchased_product (STRING): Most frequently purchased product
    -
    (... there are ~150 columns total in this table)
    """

    last_sql = chat_history[-1]["sql"] if chat_history else None

    if last_sql and not user_question.lower().startswith(("how", "what", "show", "list", "give")):
        # Treat as a follow-up (modify last query)
        prompt = f"""
        You are an expert SQL assistant.
        The last SQL query was:

        {last_sql}

        The user asked a follow-up: "{user_question}"

        Modify the previous SQL to incorporate the new filter or condition,
        while keeping the same structure and logic where possible.

        Only return valid BigQuery SQL.
        """
    else:
        # Fresh SQL query
        history_str = "\n".join(
            [f"User: {m['user']}\nSQL: {m['sql']}\nAnswer: {m['answer']}" for m in chat_history]
        )

        prompt = f"""
        You are an expert SQL generator.
        Convert the following natural language question into a BigQuery Standard SQL SELECT query.

        Rules:
        - Use ONLY the table: `weezietowelsdaton.Prod_presentation.Customer360`.
        - Do NOT use any other tables or datasets.
        - Do NOT generate DML (INSERT, UPDATE, DELETE, MERGE) or DDL (CREATE, DROP, ALTER).
        - Do NOT use non-SELECT queries.
        - Only valid BigQuery Standard SQL is allowed.

        Schema:
        {schema}

        Chat history so far:
        {history_str}

        New Question: {user_question}

        SQL:
        """

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    sql_query = clean_sql(response.text)
    return sql_query

def validate_sql(sql: str) -> bool:
    """Validate SQL query for safety."""
    if not sql.strip().lower().startswith("select"):
        return False
    forbidden = ["insert", "update", "delete", "drop", "alter", "create", "merge"]
    if any(word in sql.lower() for word in forbidden):
        return False
    if "`weezietowelsdaton.Prod_presentation.Customer360`" not in sql:
        return False
    return True

def run_query(sql: str):
    """Run SQL in BigQuery and return results as list of dicts."""
    results = bq_client.query(sql).result()
    return [dict(row) for row in results]

# ----------------------------
# Chat Input
# ----------------------------
if user_input := st.chat_input("Ask a question about your customers..."):
    try:
        # Generate SQL (with context)
        sql = generate_sql(user_input, st.session_state.messages)

        if not validate_sql(sql):
            answer = "⚠️ Unsafe or invalid SQL detected. Query blocked."
            rows = []
        else:
            rows = run_query(sql)

            if len(rows) == 1 and len(rows[0]) == 1:
                col_name = list(rows[0].keys())[0]
                answer = f"{col_name}: {rows[0][col_name]}"
            elif len(rows) == 0:
                answer = "No results found."
            else:
                answer = f"Returned {len(rows)} rows."

        # Save to chat history
        st.session_state.messages.append(
            {"user": user_input, "sql": sql, "answer": answer, "rows": rows}
        )

    except Exception as e:
        st.session_state.messages.append(
            {"user": user_input, "sql": "N/A", "answer": f"⚠️ Error: {str(e)}", "rows": []}
        )

# ----------------------------
# Render Chat History
# ----------------------------
for msg in st.session_state.messages:
    with st.chat_message("user"):
        st.markdown(msg["user"])

    with st.chat_message("assistant"):
        st.markdown(f"**SQL:**\n```sql\n{msg['sql']}\n```")
        st.markdown(f"**Answer:** {msg['answer']}")

        if msg.get("rows") and not (len(msg["rows"]) == 1 and len(msg["rows"][0]) == 1):
            st.dataframe(msg["rows"])
