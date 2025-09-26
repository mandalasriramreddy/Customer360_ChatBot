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
st.title("💬 Customer360 Chatbot ")

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
    Important Notes:
    - This is a CUSTOMER-LEVEL table (one row per customer).
    - Ignore any rolling-window or derived fields (like `orders_last_12_months_q1_25`). 
    These are not relevant for SQL generation unless explicitly requested.
    - Always use these base columns for metrics:
        - total_orders (INTEGER): Total orders placed by the customer.
        - total_net_sales (FLOAT64): Total sales amount across all orders of the customer.
    - To calculate metrics:
        - Total customers → COUNT(DISTINCT customer_key) or COUNT(email).
        - Total orders → SUM(total_orders).
        - Total sales → SUM(total_net_sales).
        - Average Order Value (AOV) → SUM(total_net_sales) / SUM(total_orders).
        *Do not try to compute AOV per row, always compute at the aggregated level.*
        *AOV is always defined, do not say it's unavailable.*
        - Average Order Value (AOV) → SUM(total_net_sales) / SUM(total_orders).
        *Do not compute AOV per row, always aggregate first.*
        *Always return AOV when asked, do not say it is unavailable.*
        - When the user specifies a time period (month, year, quarter):
        * Always filter using acquisition_date unless explicitly asked for last_order_date.
        * Example: "January 2025" → 
            WHERE EXTRACT(YEAR FROM acquisition_date) = 2025
            AND EXTRACT(MONTH FROM acquisition_date) = 1
    - When grouping (e.g., by zipcode, state, acquisition_product):
        - Use SUM(total_orders) for orders.
        - Use SUM(total_net_sales) for sales.
        - Use SUM(total_net_sales) / SUM(total_orders) for AOV.
    - Always return valid BigQuery Standard SQL.
    Columns:
    - email (STRING): Customer email
    - customer_key (STRING): Unique identifier for the customer.
    - first_name (STRING): Customer's first name.
    - last_name (STRING): Customer's last name.
    - address1, address2, city, state, country, zipcode (STRING): Customer address details.
    - phone (STRING): Customer's phone number.
    - acquisition_date (DATE): Date when the customer made their first purchase.
    - acquisition_order_id (STRING): ID of the customer's first order.
    - first_order_value (FLOAT): Net sales of first or acquisition order
    - acquisition_product (STRING): Product purchased in the acquisition order.
    - acquisition_product_category (STRING): Category of the acquisition product.
    - acquisition_product_selling_group (STRING): Selling group of the acquisition product.
    - last_order_date (DATE): Date of the customer's most recent order.
    - most_purchased_product (STRING): Most frequently purchased product.
    - total_orders (INTEGER): Total orders placed by the customer.
    - total_net_sales (FLOAT64): Total sales amount or LTV of the customer.
    - second_order_product_category (STRING): Category of the product purchased in the customer's second order.
    - second_order_product_selling_group (STRING): Selling group of the product purchased in the customer's second order.
    - Acquisition_orderid_online (STRING): Order ID of the customer's acquisition made through the online channel.
    - Acquisition_date_online (DATE): Date of online acquisition order.
    - Acquisition_Product_online (STRING): Product bought in online acquisition.
    - Acquisition_ProductCategory_Basket_online (STRING): Product category basket for online acquisition.
    - Acquisition_Product_Sku_Basket_online (STRING): SKU(s) for online acquisition basket.
    - Acquisition_product_type_basket (STRING): Product type for acquisition basket.
    - Acquisition_Product_Category_online (STRING): Product category for online acquisition.
    - Acquisition_mktg_channel (STRING): Marketing channel of acquisition.
    - Acquisition_Sourcemedium_online (STRING): Source/medium for online acquisition.
    - Acquisition_Campaign_online (STRING): Campaign name for online acquisition.
    - Acquisition_Channel_type_online (STRING): Acquisition channel type for online orders.
    - Acquisition_orderid_store (STRING): Store acquisition order ID.
    - Acquisition_date_store (DATE): Date of store acquisition order.
    - Acquisition_Product_store (STRING): Product purchased in acquisition store order.
    - Acquisition_ProductCategory_Basket_store (STRING): Product category basket in acquisition store order.
    - Acquisition_Product_Sku_Basket_store (STRING): SKU(s) for store acquisition basket.
    - Acquisition_Product_Category_store (STRING): Product category for acquisition store order.
    - Last_order_id (STRING): ID of the last order placed by the customer.
    - Last_order_product (STRING): Product purchased in the last order.
    - Last_order_product_category (STRING): Category of the last order product.
    - Last_order_selling_group (STRING): Selling group of the last order product.
    - Last_Orderid_online (STRING): Online last order ID, if available.
    - LastOrder_online (DATE): Date of last online order.
    - Last_Order_mktg_Channel (STRING): Marketing channel of last online order.
    - Last_Order_Sourcemedium_online (STRING): Source/medium for last online order.
    - Last_Order_Campaign_online (STRING): Campaign for last online order.
    - Last_Order_Channel_type_online (STRING): Channel type of last online order.
    - Last_Orderid_store (STRING): Store last order ID.
    - LastOrder_store (DATE): Date of last store order.
    - Last_Order_Product_Category_online (STRING): Product category for last online order.
    - Last_Order_Selling_Group_online (STRING): Selling group for last online order.
    - Last_Order_Product_Category_store (STRING): Product category for last store order.
    - Last_Order_Selling_Group_store (STRING): Selling group for last store order.
    - Tenure (INTEGER): Number of days since customer's first acquisition.
    - Days_Since_Last_Order (INTEGER): Number of days since the last order.
    - total_orders (INTEGER): Total orders placed by the customer.
    - total_orders_online (INTEGER): Number of online orders.
    - total_orders_store (INTEGER): Number of store orders.
    - total_discounted_orders (INTEGER): Number of discounted orders.
    - discounted_orders_online (INTEGER): Discounted online orders.
    - discounted_orders_store (INTEGER): Discounted store orders.
    - total_full_price_orders (INTEGER): Number of orders placed at full price.
    - full_price_orders_online (INTEGER): Number of full-price orders placed through the online channel.
    - full_price_orders_store (INTEGER): Number of full-price orders placed through store.
    - total_refunded_orders (INTEGER): Number of refunded orders.
    - refunded_orders_online (INTEGER): Refunded online orders.
    - refunded_orders_store (INTEGER): Refunded store orders.
    - total_quantity_sold (INTEGER): Total items purchased.
    - quantity_sold_online (INTEGER): Items purchased online.
    - quantity_sold_store (INTEGER): Items purchased in store.
    - total_returned_quantity (INTEGER): Total quantity returned.
    - quantity_returned_online (INTEGER): Returned quantity online.
    - quantity_returned_store (INTEGER): Returned quantity store.
    - total_gross_sales (FLOAT): Total gross sales amount.
    - gross_sales_online (FLOAT): Gross sales online.
    - gross_sales_store (FLOAT): Gross sales in store.
    - total_gross_sales_excl_markdowns (FLOAT): Gross sales excluding markdowns.
    - gross_sales_excl_markdowns_online (FLOAT): Gross sales excluding markdowns online.
    - gross_sales_excl_markdowns_store (FLOAT): Gross sales excluding markdowns in store.
    - sales_2024 (FLOAT): Total sales in year 2024.
    - sales_2023 (FLOAT): Total sales in year 2023.
    - orders_2024 (INTEGER): Orders in year 2024.
    - orders_2023 (INTEGER): Orders in year 2023.
    - total_Markdowns (FLOAT): Total markdowns applied.
    - Markdowns_online (FLOAT): Markdown value online.
    - Markdowns_store (FLOAT): Markdown value in store.
    - total_net_sales (FLOAT): Net sales after discounts/refunds.
    - net_sales_online (FLOAT): Net sales online.
    - net_sales_store (FLOAT): Net sales in store.
    - total_discounts (FLOAT): Total discounts applied.
    - total_discounts_online (FLOAT): Discounts online.
    - total_discounts_store (FLOAT): Discounts in store.
    - total_refunds (FLOAT): Total refunds processed.
    - total_refunds_online (FLOAT): Total refund amount issued for the customer's online orders.
    - total_refunds_store (FLOAT): Total refund initiated for the customer's orders placed in stores.
    - ltv_13_months (FLOAT): Customer lifetime value within 13 months from today.
    - ltv_24_months (FLOAT): Customer lifetime value within 24 months from today.
    - ltv_36_months (FLOAT): Customer lifetime value within 36 months from today.
    - ltv_12_to_24_months (FLOAT): Lifetime value from 12 to 24 months.
    - ltv_24_to_36_months (FLOAT): Lifetime value from 24 to 36 months.
    - acq_ltv_12_months (FLOAT): Acquisition LTV within 12 months.
    - acq_ltv_24_months (FLOAT): Acquisition LTV within 24 months.
    - acq_ltv_36_months (FLOAT): Acquisition LTV within 36 months.
    - acq_ltv_12_to_24_months (FLOAT): Acquisition LTV from 12 to 24 months.
    - acq_ltv_24_to_36_months (FLOAT): Acquisition LTV from 24 to 36 months.
    - aov_13_months (FLOAT): Average order value over 13 months.
    - avg_day_diff (FLOAT): Average days between orders.
    - median_day_diff (INTEGER): Median days between orders.
    - day_diff_order1_order2 (INTEGER): Days between order 1 and order 2.
    - day_diff_order2_order3 (INTEGER): Days between order 2 and order 3.
    - day_diff_order3_order4 (INTEGER): Days between order 3 and order 4.
    - day_diff_order4_order5 (INTEGER): Days between order 4 and order 5.
    - orders_last_3_months (INTEGER): Orders in the last 3 months.
    - orders_last_6_months (INTEGER): Orders in the last 6 months.
    - orders_last_12_months (INTEGER): Orders in the last 12 months.
    - orders_last_6_to_18_months (INTEGER): Orders in the 6 to 18 month window.
    - orders_last_12_to_24_months (INTEGER): Orders in the 12 to 24 month window.
    - orders_last_18_to_36_months (INTEGER): Orders in the 18 to 36 month window.
    - orders_last_24_to_36_months (INTEGER): Orders in the 24 to 36 month window.
    - orders_prior_to_36_months (INTEGER): Orders prior to 36 months.
    - orders_last_12_months_q3_24 (INTEGER): Orders in last 12 months (Q3 2024).
    - orders_last_12_to_24_months_q3_24 (INTEGER): Orders 12 to 24 months back (Q3 2024).
    - orders_last_24_to_36_months_q3_24 (INTEGER): Orders 24 to 36 months back (Q3 2024).
    - orders_prior_to_36_months_q3_24 (INTEGER): Orders prior to 36 months (Q3 2024).
    - last_order_date_q3_24 (DATE): Last order date for Q3 2024.
    - orders_last_12_months_q4_24 (INTEGER): Orders in last 12 months (Q4 2024).
    - orders_last_12_to_24_months_q4_24 (INTEGER): Orders 12 to 24 months back (Q4 2024).
    - orders_last_24_to_36_months_q4_24 (INTEGER): Orders 24 to 36 months back (Q4 2024).
    - orders_prior_to_36_months_q4_24 (INTEGER): Orders prior to 36 months (Q4 2024).
    - last_order_date_q4_24 (DATE): Last order date for Q4 2024.
    - orders_last_12_months_q1_25 (INTEGER): Orders in last 12 months (Q1 2025).
    - orders_last_12_to_24_months_q1_25 (INTEGER): Orders 12 to 24 months back (Q1 2025).
    - orders_last_24_to_36_months_q1_25 (INTEGER): Orders 24 to 36 months back (Q1 2025).
    - orders_prior_to_36_months_q1_25 (INTEGER): Orders prior to 36 months (Q1 2025).
    - last_order_date_q1_25 (DATE): Last order date for Q1 2025.
    - orders_last_12_months_q2_25 (INTEGER): Orders in last 12 months (Q2 2025).
    - orders_last_12_to_24_months_q2_25 (INTEGER): Orders 12 to 24 months back (Q2 2025).
    - orders_last_24_to_36_months_q2_25 (INTEGER): Orders 24 to 36 months back (Q2 2025).
    - orders_prior_to_36_months_q2_25 (INTEGER): Orders prior to 36 months (Q2 2025).
    
    (... store means the order is a retail order else it's a DTC order)
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
        - For customer counts → use COUNT(DISTINCT customer_key) or COUNT(email).
        - For total orders → use SUM(total_orders), not COUNT(*).
        - For total sales → use SUM(total_net_sales).
        - When ranking by zipcode/city/state, always aggregate first, then ORDER BY the metric.

        Schema:
        {schema}

        Chat history so far:
        {history_str}

        New Question: {user_question}

        SQL:
        """

    model = genai.GenerativeModel("gemini-2.5-flash")
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
