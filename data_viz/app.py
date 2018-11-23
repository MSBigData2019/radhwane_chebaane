# -*- coding: utf-8 -*-

#####   Imports   ####

import os
import pandas as pd
import datetime
from itertools import product

from bokeh.core.properties import value
from bokeh.events import Reset
from bokeh.events import SelectionGeometry
from bokeh.layouts import column
from bokeh.models import ColumnDataSource
from bokeh.models import HoverTool
from bokeh.models import NumeralTickFormatter
from bokeh.models.widgets import CheckboxButtonGroup
from bokeh.models.widgets import Div
from bokeh.plotting import figure
from bokeh.plotting import curdoc


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

#####   Interactions ####

def filter_categories(indexes):
    categories_filtered = [CATEGORIES[ind] for ind in indexes] if indexes != [] else CATEGORIES
    update_num_categories_source(categories_filtered, force_categories=True)
    update_usd_vs_date_source(categories_filtered, force_categories=True)


def update_usd_vs_date_source(categories=None, force_categories=False):
    # To get the current state of the categories
    if categories is None:
        categories = source_num_categories.data['categories']
    elif not force_categories:
        categories = list(set(categories) & set(source_num_categories.data['categories']))
    df_categories = kickstarter_df_sub[kickstarter_df_sub.broader_category.isin(categories)]
    for color, state in zip(COLORS, STATES):
        df_by_state = df_categories[df_categories.state == state]
        data = {
            'x': df_by_state['created_at'],
            'y': df_by_state['usd_pledged'],
            'name': df_by_state['name'],
            'state': [state] * len(df_by_state),
        }
        sources_usd_vs_date[state].data = data


def update_on_usd_vs_date_selection(event):
    geometry = event.geometry
    if geometry['type'] == 'rect':
        x0 = datetime.datetime.fromtimestamp(geometry['x0'] / 1000)
        x1 = datetime.datetime.fromtimestamp(geometry['x1'] / 1000)
        y0 = geometry['y0']
        y1 = geometry['y1']
        sub_df = kickstarter_df[kickstarter_df.created_at.between(x0, x1) & kickstarter_df.usd_pledged.between(y0, y1)]
        update_num_categories_source(source_num_categories.data['categories'], sub_df)


def update_num_categories_source(categories=None, df=kickstarter_df, force_categories=False):
    # To get the current state of the categories
    if categories is None:
        categories = source_num_categories.data['categories']
    elif not force_categories:
        categories = list(set(categories) & set(source_num_categories.data['categories']))
    stacked_barchart_df = (
        df['state'].groupby(df['broader_category'])
            .value_counts(normalize=False)
            .rename('count')
    )

    data = {
        'categories': categories,
    }

    # Sadly, I could not find a more efficient method to prepare a pandas array for a stacked bar chart
    for state, category in product(STATES, categories):
        data.setdefault(state, [])

        try:
            data[state].append(stacked_barchart_df.loc[category, state])
        except KeyError:
            data[state].append(0)
    source_num_categories.data = data


#####   Data sources ####

sources_usd_vs_date = {state: ColumnDataSource({
    'x': [],
    'y': [],
    'name': [],
    'state': [],
}) for state in STATES}

source_num_categories = ColumnDataSource(data={
    'categories': CATEGORIES
})

update_usd_vs_date_source()
update_num_categories_source()


#####   Layout   ####

title = Div(text='<h1 style="text-align: center">Kickstarter Dashboard</h1>')

# This looks better than the multiselect widget
select = CheckboxButtonGroup(labels=CATEGORIES)
select.on_click(filter_categories)

hover_usd_vs_date = HoverTool(tooltips=[
    ("Name", "@name"),
    ("State", "@state"),
])

p_usd_vs_date = figure(
    plot_height=200,
    y_axis_type='log',
    x_axis_type='datetime',
    tools=[hover_usd_vs_date, 'box_select', 'reset']
)

for color, state in zip(COLORS, STATES):
    p_usd_vs_date.circle(
        x='x',
        y='y',
        line_color='white',
        fill_color=color,
        alpha=0.7,
        size=15,
        legend=state,
        source=sources_usd_vs_date[state]
    )

p_usd_vs_date.xaxis.axis_label = 'Date'
p_usd_vs_date.yaxis.axis_label = 'USD pledged'
# See http://bokeh.pydata.org/en/latest/docs/reference/models/formatters.html for all formatters
p_usd_vs_date.yaxis.formatter = NumeralTickFormatter(format='0a')
p_usd_vs_date.legend.click_policy = 'hide'
p_usd_vs_date.legend.location = "top_left"

p_usd_vs_date.on_event(Reset, lambda _: update_num_categories_source())
p_usd_vs_date.on_event(SelectionGeometry, update_on_usd_vs_date_selection)

# Can't seem to be able to put the state in there or the number of student in the tooltip though
hover_num_categories = HoverTool(tooltips=[
    ("Category", "@categories"),
])

p_num_categories = figure(
    x_range=CATEGORIES,
    plot_height=200,
    tools=[hover_num_categories]
)

p_num_categories.vbar_stack(
    STATES,
    x='categories',
    width=0.9,
    color=COLORS,
    source=source_num_categories,
    legend=[value(x) for x in STATES]
)

p_num_categories.yaxis.axis_label = 'Number of projects'

layout = column(title, select, p_usd_vs_date, p_num_categories, sizing_mode='scale_width')


#####   Main  ####

curdoc().add_root(layout)
