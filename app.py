import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.monday_client import fetch_deals, fetch_work_orders, fetch_deals_columns, fetch_work_orders_columns
from app.cleaner import clean_deals, clean_work_orders
from app.metrics import compute_deals_metrics, compute_work_orders_metrics, get_leadership_summary
from app.llm import parse_intent, generate_summary, generate_leadership_summary
from app.agent import run_agent

# Cache expensive calls to avoid re-fetching on every Streamlit rerun
@st.cache_data(ttl=300)
def cached_fetch_deals():
    return fetch_deals()

@st.cache_data(ttl=300)
def cached_fetch_deals_columns():
    return fetch_deals_columns()

@st.cache_data(ttl=300)
def cached_fetch_work_orders():
    return fetch_work_orders()

@st.cache_data(ttl=300)
def cached_fetch_work_orders_columns():
    return fetch_work_orders_columns()

st.set_page_config(page_title="Monday.com BI Agent", page_icon="📊", layout="wide")

st.title("📊 Monday.com BI Agent")
st.markdown("Your Business Intelligence Agent powered by Monday.com")

with st.sidebar:
    st.header("Menu")
    st.markdown("""
    Navigate between:
    - **Data** - View raw data from Monday
    - **Dashboard** - Key metrics overview
    - **Chat** - Ask AI questions
    """)

tab1, tab2, tab3 = st.tabs(["📊 Data", "📈 Dashboard", "💬 Chat"])

with tab1:
    st.subheader("Data from Monday.com")

    try:
        deals_raw = cached_fetch_deals()
        wo_raw = cached_fetch_work_orders()
        deals_cols = cached_fetch_deals_columns()
        wo_cols = cached_fetch_work_orders_columns()
        deals_list = clean_deals(deals_raw, deals_cols)
        wo_list = clean_work_orders(wo_raw, wo_cols)

        col1, col2 = st.columns(2)

        with col1:
            st.write("### Deals")
            if deals_list:
                st.write(f"Found **{len(deals_list)} deals**")
                for deal in deals_list[:10]:
                    st.write(f"""
                    - **{deal.get('name')}**
                      - Amount: ${deal.get('amount', 0):,.0f}
                      - Sector: {deal.get('sector', 'N/A')}
                      - Stage: {deal.get('stage', 'N/A')}
                      - Close Date: {deal.get('close_date', 'N/A')}
                    """)
                if len(deals_list) > 10:
                    st.info(f"Showing 10 of {len(deals_list)} deals")
            else:
                st.warning("No deals found")

        with col2:
            st.write("### Work Orders")
            if wo_list:
                st.write(f"Found **{len(wo_list)} work orders**")
                for wo in wo_list[:10]:
                    st.write(f"""
                    - **{wo.get('name')}**
                      - Revenue: ${wo.get('revenue', 0):,.0f}
                      - Status: {wo.get('status', 'N/A')}
                      - Start: {wo.get('start_date', 'N/A')}
                      - End: {wo.get('end_date', 'N/A')}
                    """)
                if len(wo_list) > 10:
                    st.info(f"Showing 10 of {len(wo_list)} work orders")
            else:
                st.warning("No work orders found")

    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        st.write("Check your config.py - make sure board IDs and API key are correct")

with tab2:
    st.subheader("Business Metrics")

    try:
        deals_raw = cached_fetch_deals()
        wo_raw = cached_fetch_work_orders()
        deals_cols = cached_fetch_deals_columns()
        wo_cols = cached_fetch_work_orders_columns()
        deals_list = clean_deals(deals_raw, deals_cols)
        wo_list = clean_work_orders(wo_raw, wo_cols)

        deals_metrics = compute_deals_metrics(deals_list)
        wo_metrics = compute_work_orders_metrics(wo_list)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Pipeline", f"${deals_metrics['total_pipeline']:,.0f}")
        with col2:
            st.metric("Active Deals", deals_metrics['deal_count'])
        with col3:
            st.metric("Total Revenue", f"${wo_metrics['total_revenue']:,.0f}")
        with col4:
            st.metric("Active Work Orders", wo_metrics['active_count'])

        st.markdown("---")
        st.subheader("Pipeline by Sector")
        
        if deals_metrics['by_sector']:
            sector_data = deals_metrics['by_sector']
            for sector, data in sorted(sector_data.items(), key=lambda x: x[1]['pipeline'], reverse=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{sector.title()}**")
                with col2:
                    st.write(f"${data['pipeline']:,.0f} ({data['count']} deals)")
        else:
            st.info("No sector data available")
    
    except Exception as e:
        st.error(f"Error loading metrics: {str(e)}")

with tab3:
    st.subheader("Ask a Question")
    
    question = st.text_area("Your question:", placeholder="e.g., 'What is our total pipeline?' or 'How much revenue from energy sector?'", height=100)
    
    if st.button("Ask AI", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please ask a question")
        else:
            with st.spinner("Thinking..."):
                try:
                    deals_raw = cached_fetch_deals()
                    wo_raw = cached_fetch_work_orders()
                    deals_cols = cached_fetch_deals_columns()
                    wo_cols = cached_fetch_work_orders_columns()
                    deals_list = clean_deals(deals_raw, deals_cols)
                    wo_list = clean_work_orders(wo_raw, wo_cols)
                    
                    st.info(f"Loaded: {len(deals_list)} deals, {len(wo_list)} work orders")
                    
                    # Try the LangChain agent first (will call API tools as needed).
                    try:
                        agent_answer = run_agent(question)
                        if agent_answer and not agent_answer.startswith('[agent error]'):
                            st.success(agent_answer)
                            st.stop()
                    except Exception:
                        # fallback to deterministic path below
                        pass

                    if any(word in question.lower() for word in ["summary", "leadership", "board"]):
                        summary_data = get_leadership_summary(deals_list, wo_list)
                        answer = generate_leadership_summary(summary_data)
                    else:
                        intent = parse_intent(question)
                        st.write(f"**Intent detected:** {intent}")

                        if "error" in intent:
                            answer = intent["error"]
                        else:
                            board = intent.get("board", "deals")
                            sector = intent.get("sector")
                            metric = intent.get("metric")

                            # handle columns question specially
                            if metric == "columns":
                                if board == "deals":
                                    cols = cached_fetch_deals_columns()
                                else:
                                    cols = cached_fetch_work_orders_columns()
                                col_names = [c.get('title') or c.get('name') or c.get('id') for c in cols]
                                answer = f"Board has {len(col_names)} columns: {', '.join(col_names[:10])}{'...' if len(col_names)>10 else ''}"
                                st.write(f"**Columns (sample):** {col_names[:10]}")
                            else:
                                answered = False
                                # compute metrics for requested board
                                if board == "deals":
                                    full_deals_metrics = compute_deals_metrics(deals_list)
                                    # normalize requested sector
                                    sector_key = (sector or '')
                                    sector_key = sector_key.lower().strip() if sector_key is not None else ''
                                    no_filter_values = {"", None, "all", "none", "overall", "total", "any"}

                                    # If user asked for 'all' or didn't specify sector, do not filter
                                    if sector_key in no_filter_values:
                                        metrics = full_deals_metrics
                                    else:
                                        by_sector = full_deals_metrics.get("by_sector", {})
                                        # exact-only match on normalized sector keys
                                        if sector_key in by_sector:
                                            metrics = by_sector.get(sector_key)
                                        else:
                                            # return available sector list (only true sector keys)
                                            available = [k for k in by_sector.keys() if k and k != 'unknown']
                                            if available:
                                                answer = f"No data for sector '{sector}'. Available sectors: {', '.join(sorted(available)[:10])}"
                                            else:
                                                answer = f"No sector data available."
                                            st.info(answer)
                                            answered = True
                                            metrics = None
                                else:
                                    metrics = compute_work_orders_metrics(wo_list)

                                if not answered:
                                    st.write(f"**Metrics:** {metrics}")
                                    # try deterministic fast answer first
                                    from app.llm import answer_from_metrics
                                    fast = answer_from_metrics(intent, metrics)
                                    if fast:
                                        answer = fast
                                    else:
                                        answer = generate_summary(question, metrics)
                                else:
                                    # already prepared an informative answer (no sector data)
                                    pass
                    
                    st.success(answer)
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    import traceback
                    st.write(traceback.format_exc())
