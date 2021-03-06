# -*- coding: utf-8 -*-

#####   Imports   ####

import os
import pandas as pd
import dateutil

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

#####   Data loading ####

kickstarter_df = pd.read_csv(os.path.join('.', 'kickstarter-cleaned.csv'), parse_dates=True)
kickstarter_df['broader_category'] = kickstarter_df['category_slug'].str.split('/').str.get(0)
kickstarter_df['created_at'] = pd.to_datetime(kickstarter_df['created_at'])

kickstarter_df_sub = kickstarter_df.sample(10000)

CATEGORIES = kickstarter_df['broader_category'].unique().tolist()
COLUMNS = ['launched_at', 'deadline', 'blurb', 'usd_pledged', 'state', 'spotlight', 'staff_pick', 'category_slug',
           'backers_count', 'country']
COLORS = ['#7DFB6D', '#C7B815', '#D4752E', '#C7583F']
STATES = ['successful', 'suspended', 'failed', 'canceled']

print(kickstarter_df.describe())

#####   Main  ####

app = dash.Dash()

# This is optional but the app looks better with it
app.css.append_css({
    "external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"
})

#####   Layout   ####

app.layout = html.Div(children=[
    html.H1(children='Kickstarter Dashboard', style={
        'textAlign': 'center',
    }),
    dcc.Dropdown(
        id='categories',
        options=[{'label': i, 'value': i} for i in kickstarter_df['broader_category'].unique()],
        multi=True
    ),
    dcc.Graph(
        id='usd-pledged-vs-date',
    ),
    dcc.Graph(
        id='count-state-vs-category',
    )
])


#####   Interactions ####

@app.callback(
    dash.dependencies.Output('usd-pledged-vs-date', 'figure'),
    [
        dash.dependencies.Input('categories', 'value'),
    ])
def update_scatterplot(categories):
    if categories is None or categories == []:
        categories = CATEGORIES

    sub_df = kickstarter_df_sub[(kickstarter_df_sub['broader_category'].isin(categories))]

    return {
        'data': [
            go.Scatter(
                x=sub_df[(kickstarter_df_sub.state == state)]['created_at'],
                y=sub_df[(kickstarter_df_sub.state == state)]['usd_pledged'],
                text=sub_df[(kickstarter_df_sub.state == state)]['name'],
                mode='markers',
                opacity=0.7,
                marker={
                    'size': 15,
                    'color': color,
                    'line': {'width': 0.5, 'color': 'white'}
                },
                name=state,
            ) for (state, color) in zip(STATES, COLORS)
        ],
        'layout': go.Layout(
            xaxis={'title': 'Date'},
            yaxis={'title': 'USD pledged', 'type': 'log'},
            margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
            legend={'x': 0, 'y': 1},
            hovermode='closest'
        )
    }


@app.callback(
    dash.dependencies.Output('count-state-vs-category', 'figure'),
    [
        dash.dependencies.Input('categories', 'value'),
        dash.dependencies.Input('usd-pledged-vs-date', 'relayoutData')
    ])
def update_bar_chart(categories, relayout_data):
    if categories is None or categories == []:
        categories = CATEGORIES

    if relayout_data is not None and ('xaxis.autorange' in relayout_data) and ('yaxis.autorange' in relayout_data):
        print(relayout_data)
        x0 = dateutil.parser.parse(relayout_data['xaxis.range[0]'])
        x1 = dateutil.parser.parse(relayout_data['xaxis.range[1]'])
        y0 = 10 ** relayout_data['yaxis.range[0]']
        y1 = 10 ** relayout_data['yaxis.range[1]']

        sub_df = kickstarter_df[kickstarter_df.created_at.between(x0, x1) & kickstarter_df.usd_pledged.between(y0, y1)]
    else:
        sub_df = kickstarter_df

    stacked_barchart_df = (
        sub_df[sub_df['broader_category'].isin(categories)]['state'].groupby(sub_df['broader_category'])
            .value_counts(normalize=False)
            .rename('count')
            .to_frame()
            .reset_index('state')
            .pivot(columns='state')
            .reset_index()
    )
    return {
        'data': [
            go.Bar(
                x=stacked_barchart_df['broader_category'],
                y=stacked_barchart_df['count'][state],
                name=state,
                marker={
                    'color': color
                }
            ) for (state, color) in zip(STATES[::-1], COLORS[::-1])
        ],
        'layout': go.Layout(
            yaxis={'title': 'Number of projects'},
            barmode='stack',
            hovermode='closest'
        )
    }


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run_server(debug=True, host='0.0.0.0', port=port)
