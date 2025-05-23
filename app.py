
import streamlit as st
import pandas as pd
from itertools import combinations
from collections import Counter
import io

st.set_page_config(page_title="Machine Option Attach‑Rate Explorer", layout="wide")
st.title("Machine Option Attach‑Rate Explorer")

st.markdown(
    """Upload an order‑lines extract from your ERP/CSV.  
    **Required columns** (case/spacing insensitive):  
    • `CO_NUM` – order number  
    • `CO_LINE` – line number (`1` = base machine)  
    • `ITEM` – item code  
    • `DESCRIPTION` – optional but nice to have  
    The app computes how frequently each option appears on orders for a chosen machine
    and shows common option pairs.  You can export all underlying tables via the buttons below.""")

uploaded = st.file_uploader("Upload .csv or .xlsx", type=["csv", "xlsx"])

if uploaded is None:
    st.stop()

# ---- Load ------------------------------------------------------------
if uploaded.name.lower().endswith(".csv"):
    df = pd.read_csv(uploaded)
else:
    df = pd.read_excel(uploaded)

df.columns = df.columns.str.strip()

def find_col(pattern):
    import re
    for c in df.columns:
        if re.fullmatch(pattern, c.replace(" ", "_"), flags=re.I):
            return c
    return None

col_map = {
    'CO_NUM' : find_col(r"co[_]?num"),
    'CO_LINE': find_col(r"co[_]?line"),
    'ITEM'   : find_col(r"item"),
    'DESC'   : find_col(r"desc.*"),
}
missing = [k for k,v in col_map.items() if k!='DESC' and v is None]
if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

df = df.rename(columns={v:k for k,v in col_map.items() if v})

# Identify machine vs option lines
machines = df.loc[df['CO_LINE']==1, ['CO_NUM','ITEM']].rename(columns={'ITEM':'Machine'})
options  = df.loc[df['CO_LINE']!=1, ['CO_NUM','ITEM']]

merged = machines.merge(options, on='CO_NUM', how='left')

# Attach-rate table
attach = (merged.groupby(['Machine','ITEM'])['CO_NUM']
                .nunique()
                .reset_index(name='Order_Count'))

total_orders = (machines.groupby('Machine')['CO_NUM']
                       .nunique()
                       .rename('Total_Orders')
                       .reset_index())

attach = attach.merge(total_orders, on='Machine')
attach['Attach_Rate'] = attach['Order_Count'] / attach['Total_Orders']

# ---- Export full table -----------------------------------------------
csv_all = attach.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download full attach‑rate table (all machines)",
                   csv_all,
                   "attach_rates_full.csv",
                   "text/csv")

# ---- Machine selector with search ------------------------------------
machine_list = sorted(attach['Machine'].unique())
search = st.text_input("🔍  Search machine").strip().lower()
filtered = [m for m in machine_list if search in m.lower()] or ["< no match >"]

sel_machine = st.selectbox("Select a machine model", filtered)
if sel_machine == "< no match >":
    st.stop()

st.subheader(f"Attach‑rates for **{sel_machine}**")
singles = attach[attach['Machine']==sel_machine]             .sort_values('Attach_Rate', ascending=False)
st.dataframe(singles[['ITEM','Attach_Rate','Order_Count','Total_Orders']])

csv_singles = singles.to_csv(index=False).encode('utf-8')
st.download_button(f"⬇️ Download attach‑rates for {sel_machine}",
                   csv_singles,
                   f"{sel_machine}_attach_rates.csv",
                   "text/csv")

# ---- Option pair analysis --------------------------------------------
order_sets = (merged[merged['Machine']==sel_machine]
              .groupby('CO_NUM')['ITEM'].apply(set))

pair_counter = Counter()
for s in order_sets:
    for a,b in combinations(sorted(s),2):
        pair_counter[(a,b)] += 1

pair_df = pd.DataFrame(
    [{'Pair': f"{a}, {b}",
      'Count': c,
      'Support': c/len(order_sets)}
     for (a,b),c in pair_counter.items()])         .sort_values('Count', ascending=False)

st.subheader(f"Common option pairs for **{sel_machine}**")
st.dataframe(pair_df)

csv_pairs = pair_df.to_csv(index=False).encode('utf-8')
st.download_button(f"⬇️ Download option pairs for {sel_machine}",
                   csv_pairs,
                   f"{sel_machine}_option_pairs.csv",
                   "text/csv")
