class CorrClass {
    constructor(options = {}) {
        // Initialize events using inherited IO class from timeflux.js
        this.io = new IO();
        this.io.on('connect', () => {
            console.log('Connected to the server');
            this.io.event('session_begins', this.options);
        });

        window.onbeforeunload = () => {
            console.log('session_ends');
            this.io.event('session_ends');
        };

        // Initialize scheduler
        this.scheduler = new Scheduler();
        this.scheduler.start();

        // Initialize class constants and variables with default values
        this.frequency = 500;
        this.plot_target = 'plot-container';

        // Initialize the color array with enough colors for all targets
        this.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#aec7e8'];

        let default_options = {
            threshold: 0.0
        };

        this.options = merge(default_options, options);

        // Initialize topX with a default value
        this.topX = 1;

         // Use arrow function here
            // Get references to the slider and the plot container
            const slider = document.getElementById('curve-slider');
            const sliderValueDisplay = document.getElementById('slider-value');
        
            // Listen for changes on the slider
            slider.addEventListener('input', () => { // Use arrow function here as well
                this.topX = parseInt(slider.value, 10);
                sliderValueDisplay.textContent = this.topX;
            });
        
    }
    
    plotData(data, container, topX) {
        topX = topX || this.topX; // Use the latest topX value
        let traces = [];
    
        // Get the number of targets from the first entries in data
        let first_Entry = Object.values(data)[0];
        let n_targets = Object.values(first_Entry).length;
    
        // Iterate on the targets and then on the keys
        for (let i = 0; i < n_targets; i++) {
            let y = [];
            for (let key in data) {
                y.push(data[key][i]);
            }
            let x = Array.from({ length: y.length }, (v, k) => k + 1);
            let trace = {
                x: x,
                y: y,
                mode: 'lines',
                name: `Target ${i + 1}`,
                line : {color: this.colors[i % this.colors.length]}
            };
            traces.push(trace);
        }
    
        // Sort traces by the last value in the y array in descending order
        traces.sort((a, b) => b.y[b.y.length - 1] - a.y[a.y.length - 1]);
    
        // Select only the top X traces
        traces = traces.slice(0, topX);
    
        // Add the threshold line if needed
        let threshold = this.options.threshold;
        if (threshold !== undefined) {
            let threshold_trace = {
                x: [traces[0].x[0], traces[0].x[traces[0].x.length - 1]],
                y: [threshold, threshold],
                mode: 'lines',
                name: 'Correlation threshold',
                line: {
                    dash: 'dash',
                    color: 'red'
                }
            };
            traces.push(threshold_trace);
        }
    
        // Define the layout
        const layout = {
            xaxis: {
                title: 'Frame indices'
            },
            yaxis: {
                title: 'Correlation value'
            },
            title: 'Plot of the correlations for each candidate target'
        };
    
        // Plot the data using Plotly
        Plotly.newPlot(container, traces, layout);
        return traces;
    }
}

// Load settings and initialize CorrClass
load_settings().then(async settings => {
    let Corr = new CorrClass(settings.correlations);

    // Subscribe to 'correlations' data
    Corr.io.subscribe('correlations');
    console.log('Subscribed to correlations event');

    Corr.io.on('correlations', (data, meta) => {
        Corr.plotData(data, Corr.plot_target, Corr.topX);
    });
});
