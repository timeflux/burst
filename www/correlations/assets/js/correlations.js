class CorrClass {
    constructor(options = {}) {
        // Initialize events using inherited IO class from timeflux.js
        this.io = new IO();
        this.io.on('connect', () => {
            console.log('Connected to the server');
            this.io.event('session_begins', this.options)}
        );
        window.onbeforeunload = () => {
            console.log('session_ends');
            this.io.event('session_ends');
        }

        // Initialize scheduler
        this.scheduler = new Scheduler();
        this.scheduler.start();

        // Initialize class constants and variables with default values
        this.frequency = 500;
        this.plot_target = 'plot-container';

        let default_options = {
            threshold : 0.0
        }

        this.options = merge(default_options, options);
    }

    

    plotData(data,container) {
        // Plot the data for each frame we accumulated.
        // Initialize the arrays to store the data for each target
        let traces = [];

        // Get the number of target from the first entries in data
        let first_Entry = Object.values(data)[0];
        // Get the number of keys in the first entry
        let n_targets = Object.values(first_Entry).length;

        // Iterate on the targets and then on the keys
        for (let i = 0; i < n_targets; i++) {
            // Initialize the array to store the data for each target
            let y = [];
            for (let key in data) {
                // Append the data for each frame
                y.push(data[key][i]);
            }
            // x is a span from 1 to the number of elements in y
            let x = Array.from({length: y.length}, (v, k) => k + 1);
            // Create the trace
            let trace = {
                // x is the number of frames from 1 to number of elements in y
                x: x,
                y: y,
                mode: 'lines',
                name: `Target ${i + 1}`
            };
            traces.push(trace);
        }

        let title;
        title = 'Correlations';

        const layout = {
            xaxis: {
                title: 'Frame indices'
            },
            yaxis: {
                title: 'Correlation value'
            },
            title: 'Plot of the correlations for each candidate target'
        };

        // Add a horizontal line at the threshold value
        let threshold = this.options.threshold;
        let threshold_trace = {
            x: [traces[0].x[0], traces[traces.length - 1].x[traces[traces.length - 1].x.length - 1]],
            y: [threshold, threshold],
            mode: 'lines',
            name: 'Correlation threshold',
            line: {
                dash: 'dash',
                color: 'red'
            }
        };
        traces.push(threshold_trace);

        Plotly.newPlot(container, traces, layout);
        return traces;
    }


}

// Load settings and initialize CorrClass
load_settings().then(async settings => {
    // Initialize the Corr class
    let Corr = new CorrClass(settings.correlations);

    // Subscribe to 'correlations' data
    Corr.io.subscribe('correlations');
    console.log('Subscribed to correlations event');

    Corr.io.on('correlations', (data, meta) => {
        Corr.plotData(data, Corr.plot_target);
    });
});
