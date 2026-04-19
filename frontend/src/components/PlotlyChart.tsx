import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-basic-dist-min";

// plotly.js-basic-dist-min has no bundled type declarations; the factory
// consumes a plotly runtime handle and returns a typed React component.
export const Plot = createPlotlyComponent(Plotly as never);
