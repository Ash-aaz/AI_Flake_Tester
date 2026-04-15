import plotly.subplots
import plotly.graph_objects as go
import pandas as pd
import argparse

parser = argparse.ArgumentParser(
    prog= 'Data Visualiser',
    description= 'Creates graphs to see data gathered from flake tester',
    epilog= 'Check out model metrics'
)

parser.add_argument('--csv', default='models_info.csv', help='Enter path of file where model data is stored')

args = parser.parse_args()

df = pd.read_csv(args.csv)
latency_df = df.copy()

latency_df['P95 Latency'] = pd.to_numeric(latency_df['P95 Latency'], errors='coerce')
latency_df['P99 Latency'] = pd.to_numeric(latency_df['P99 Latency'], errors='coerce')
latency_df = latency_df.dropna(subset=['P95 Latency', 'P99 Latency'])

fig = plotly.subplots.make_subplots(rows=3, cols=1, subplot_titles=("Flake Score", "Avg T/s", "P95 vs P99 Latency"))

df['Models'] = df['Model Name'].astype(str) + ' (' + df['Test Difficulty'].astype(str) + ', runs=' + df['Total Runs'].astype(int).astype(str) + ')'

flake_trace = go.Bar(x=df['Models'], y=df['Flake Score'], name='Flake Score')
tokens_trace = go.Bar(x=df['Models'], y=df['Avg. T/s'], name='Avg. T/s')
p95_trace = go.Bar(x=df['Models'], y=latency_df['P95 Latency'], name='P95')
p99_trace = go.Bar(x=df['Models'], y=latency_df['P99 Latency'], name='P99')

fig.add_trace(flake_trace, row=1, col=1)
fig.add_trace(tokens_trace, row=2, col=1)
fig.add_trace(p95_trace, row=3, col=1)
fig.add_trace(p99_trace, row=3, col=1)

fig.write_html('results.html')