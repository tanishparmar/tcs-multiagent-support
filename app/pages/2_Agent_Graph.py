"""Visual representation of the LangGraph multi-agent graph."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Agent Graph | TCS AI", page_icon="🕸️", layout="wide")
st.title("🕸️ Multi-Agent Graph")
st.caption("Live graph structure exported from LangGraph.")

@st.cache_resource
def get_mermaid():
    from src.agents.graph import get_graph
    g = get_graph()
    return g.get_graph().draw_mermaid()

mermaid_str = get_mermaid()

# Show raw Mermaid source in expander
with st.expander("Raw Mermaid source"):
    st.code(mermaid_str, language="text")

# Render the graph visually using Mermaid.js
html = f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {{ background: #0e1117; display: flex; justify-content: center; padding: 20px; }}
    .mermaid {{ font-size: 16px; }}
  </style>
</head>
<body>
  <div class="mermaid">
{mermaid_str}
  </div>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'dark',
      flowchart: {{ curve: 'basis', padding: 20 }}
    }});
  </script>
</body>
</html>
"""

components.html(html, height=520, scrolling=True)

# Also show ASCII fallback
st.divider()
st.subheader("ASCII layout")
from src.agents.graph import get_graph
ascii_graph = get_graph().get_graph().draw_ascii()
st.code(ascii_graph, language="text")
