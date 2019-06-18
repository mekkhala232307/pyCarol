# bokeh serve --show web_app.py

from pycarol.luigi_extension.taskviewer.test.pipeline_example import pipeline1

from bokeh.plotting import curdoc
doc = curdoc()

from pycarol.luigi_extension.taskviewer.bokeh_plot import get_plot_from_pipeline
plot = get_plot_from_pipeline(pipeline1)
doc.add_root(plot)