#%%
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px

from montin import Deck, Plugins, Stage

# --- Standardized docs settings (docs/script-settings.yaml) -----------------
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _docs_settings import FONTSCALE

deck = Deck(
    fontsize_scale=FONTSCALE,
    title="My Report",
    author="André Dessimoni",
    plugins=[
        Plugins.MathJax(),
        Plugins.Highlight(),
        Plugins.Plotly(),
    ],
    theme='dark',
    stage=Stage(size=(1280, 720), scale_up=True),
)

# -----------------------------------------------------------------------------
# Example of grid and basic cell types
# -----------------------------------------------------------------------------

slide = deck.add_slide(
    'Grid of cells', subtitle="Example of grid and basic cell types",
    nrows=3, ncols=4, 
    row_heights=['40%', '40%', '20%'],
    col_widths=['20%', '20%', '20%', '40%']
)

slide.add_image('figs/c08c-isoq10-iso.webp', row=1, col=1, caption='Original Cylinder without strakes')
slide.add_image('figs/s05c-isoq10-iso.webp', row=1, col=2, caption='Cylinder with strake a')
slide.add_image('figs/s08c-isoq10-iso.webp', row=1, col=3, caption='Cylinder with strake b')

slide.add_text(
"""You can build a customizable grid using various cell types, featuring:\n\n
- **Flexible Layouts:** Merge multiple cells together to create larger display areas.
- **Smart Positioning:** Place cells by explicitly setting their row and column 
coordinates (using 1-based indexing), or let the system automatically find
the next available slot.
- **Rich Text Support:** Populate text cells with Markdown, including inline 
LaTeX for math equations like $f_n=\\sqrt{k/m}$.
- **Dynamic Metrics:** Display key performance indicators.
- **Figures:** Embed images. *Click on the images to view them in full size*.
""", row=1, col=4, rowspan=2)

slide.add_metric(value=0.750,  
    label=r"Max Displacement / Diameter", 
    delta_label="Reference - clylinder")
slide.add_metric(value=0.250,  
    label=r"Max Displacement / Diameter", 
    delta=-66, lower_is_better=True,
    delta_label="% Compared to original cylinder")
slide.add_metric(value=0.125,  
    label=r"Max Displacement / Diameter", 
    delta=-75, lower_is_better=True,
    delta_label="% Compared to original cylinder")

slide.add_text(
    'Reference: [Dessimoni, A. (2021)](http://doi.org/10.14393/ufu.di.2021.415).  '
    'Modelagem e aplicação de métodos de fronteira imersa para análise de '
    'escoamentos sobre atenuadores de VIV (Master\'s thesis, '
    'Universidade Federal de Uberlândia).',
    row=3, col=1, colspan=4
)


# -----------------------------------------------------------------------------
# Example of looping to create multiple similar cells
# -----------------------------------------------------------------------------

slide = deck.add_slide('Matplotlib and code cells', nrows=2, ncols=3)

slide.add_text('Looping is a good way to automate the creation of multiple similar cells. '
    'The figures were created using the code snippet below '
    '(*which used the `add_code` method*). \n\nNote that matplotlib '
    'figure objects can be directly added to the slide using the `add_matplotlib` '
    'method.', row=1, col=3)

slide.add_code("""for f in range(4):
    i, j = (f//2 + 1), (f%2  + 1)
    x, y = sinoidal_example(f)
    
    fig, ax = plt.subplots()
    ax.plot(x, y)
    
    # --- Add matplotlib fig to cell
 
    slide.add_matplotlib(
        fig, fmt="png", 
        caption=f"$f={f}Hz$", 
        row=i, col=j
    )
""", language='python', row=2, col=3)        

def sinoidal_example(freq):
    x = np.linspace(0, 2*np.pi, 100)
    y = np.sin(x*freq)
    return x, y

for f in range(4):
    i, j = (f//2 + 1), (f%2  + 1)
    x, y = sinoidal_example(f)
    
    fig, ax = plt.subplots()
    ax.plot(x, y)

    slide.add_matplotlib(
        fig, fmt="png", 
        caption=f"$f={f}Hz$", 
        row=i, col=j
    )
plt.close()


# -----------------------------------------------------------------------------
# Example of Iframe and Plotly cells
# -----------------------------------------------------------------------------

slide = deck.add_slide('Iframes, Plotly and Tables', nrows=2, ncols=2, 
                         row_heights=['70%', '30%'])
slide.add_iframe(
    "https://www.openstreetmap.org/export/embed.html?bbox=-46.504440307617195%2C-23.414107280167556%2C-45.62690734863281%2C-22.986841807912054&amp;layer=mapnik",
    caption='Example of an iframe cell embedding a interactive map.',
)
# -----------------------------------------------------------------------------

df = px.data.gapminder()
fig = px.scatter(df, x="year", y="lifeExp", size="pop", color="continent",
                 hover_name="country", log_x=True, size_max=60)

slide.add_plotly(fig, caption='Example of a Plotly cell displaying an '
    'interactive scatter plot.')

# -----------------------------------------------------------------------------

slide.add_text(
    'The **iframe** and **Plotly** cells are interactive, allowing you to '
    'embed live content and interactive visualizations directly '
    'into your deck.\n\n'
    'You can also add a **table cell** to display a DataFrame, as '
    'shown below. \n\n'
    'All cells support options to avoid **overflow** and add an '
    '**expand** button to view the full content.'
)

slide.add_table(df.query('continent=="Americas"'), 
                caption='Example of a table cell displaying a DataFrame.'
                    '**Click the expand button to view the full table.**',
                expand_button=True, overflow=False)

# -----------------------------------------------------------------------------
deck.write('../../_static/example1.html')
print('done')
