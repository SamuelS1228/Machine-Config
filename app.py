
import streamlit as st
import pandas as pd
from itertools import combinations
from collections import Counter

st.set_page_config(page_title="Machine Option Attach‑Rate Explorer", layout="wide")
st.title("Machine Option Attach‑Rate Explorer")

st.markdown(
    """Upload an order‑lines file exported from your ERP.  
    **Required columns**: `CO_NUM`, `CO_LINE`, `ITEM`, `DESCRIPTION` (others are ignored).  
    • `CO_LINE == 1` must be the base machine.  
    The app computes how frequently each option appears on orders for a chosen machine
    and highlights common option pairs inside those orders.""")

uploaded = st.file_uploader("Upload .csv or .xlsx", type=["csv", "xlsx"])

if uploaded is None:
    st.stop()

# ---- Load data -------------------------------------------------------
if uploaded.name.endswith(".csv"):
    df = pd.read_csv(uploaded)
else:
    df = pd.read_excel(uploaded)

df.columns = df.columns.str.strip()

required = {'CO_NUM','CO_LINE','ITEM','DESCRIPTION'}
if not required.issubset(df.columns):
    st.error(f"Missing columns: {required - set(df.columns)}")
    st.stop()

# Identify machine lines (CO_LINE==1) and option lines (CO_LINE!=1)
machines = df.loc[df['CO_LINE']==1, ['CO_NUM','ITEM']].rename(columns={'ITEM':'Machine'})
options  = df.loc[df['CO_LINE']!=1, ['CO_NUM','ITEM','DESCRIPTION']]

merged = machines.merge(options, on='CO_NUM', how='left')

# Attach‑rate calculation ------------------------------------------------
attach = (merged
          .groupby(['Machine','ITEM'])['CO_NUM']
          .nunique()
          .reset_index(name='Order_Count'))

total_orders = (machines.groupby('Machine')['CO_NUM']
                .nunique()
                .rename('Total_Orders')
                .reset_index())

attach = attach.merge(total_orders, on='Machine')
attach['Attach_Rate'] = attach['Order_Count'] / attach['Total_Orders']

# ---- UI widgets -------------------------------------------------------
sel_machine = st.selectbox("Select a machine model", sorted(attach['Machine'].unique()))
min_rate    = st.slider("Minimum attach rate", 0.0, 1.0, 0.1, 0.05)
top_n       = st.number_input("Show top N results", 1, 100, 20, step=1)

st.subheader("Most common single options for **{0}**".format(sel_machine))
singles = (attach.query("Machine == @sel_machine and Attach_Rate >= @min_rate")
                  .sort_values('Attach_Rate', ascending=False)
                  .head(int(top_n)))
st.dataframe(singles[['ITEM','Attach_Rate','Order_Count','Total_Orders']])

# ---- Pair analysis ----------------------------------------------------
st.subheader("Frequently paired options for **{0}**".format(sel_machine))
# build option sets per order for this machine
order_sets = (merged[merged['Machine']==sel_machine]
              .groupby('CO_NUM')['ITEM']
              .apply(set))

pair_counter = Counter()
for items in order_sets:
    for pair in combinations(sorted(items), 2):
        pair_counter[pair] += 1

pair_df = (pd.DataFrame(
            [{'Pair': f"{a}, {b}",
              'Count': c,
              'Support': c / len(order_sets)}
             for (a,b), c in pair_counter.items()])
           .sort_values('Count', ascending=False)
           .head(int(top_n)))

st.dataframe(pair_df)
