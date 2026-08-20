def plot_interactive_chart(df, ticker, prefix):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Close'], 
        mode='lines', 
        name='מחיר',
        line=dict(color='#0066cc', width=2.5),
        hovertemplate='%{x|%d/%m/%Y}<br>מחיר: ' + prefix + '%{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=5, r=5, t=10, b=10),
        height=300,
        dragmode=False,
        xaxis=dict(
            showgrid=True, 
            zeroline=False, 
            fixedrange=True,
            showspikes=True,       # 📍 מציג קו סמן אנכי
            spikethickness=1.5,
            spikecolor="#e63946", # צבע אדום בולט לסמן
            spikemode="across"
        ),
        yaxis=dict(
            showgrid=True, 
            zeroline=False, 
            fixedrange=True,
            showspikes=True,       # 📍 מציג קו סמן אופקי
            spikethickness=1.5,
            spikecolor="#e63946",
            spikemode="across"
        )
    )
    return fig
