class ERPClass {
    constructor() {
        // Initialize events
        this.io = new IO();
        this.io.on('connect', () => this.io.event('session_begins', this.options));
        window.onbeforeunload = () => {
            this.io.event('session_ends');
        }

        // Initialize scheduler
        this.scheduler = new Scheduler();
        this.scheduler.start();

        // Initialize plots
        this.initPlots();
    }

    initPlots() {
        // Initialize erp-plot with empty data
        Plotly.newPlot('erp-plot', []);

        // Initialize dumb-plot with dummy data
        this.plotDummy();
    }

    plotErpMean(erpMeanData) {

        if (erpMeanData == null) {
            return;
        }
        else {
        // Extract time points (assuming they are in the index of the DataFrame)
        const time = Object.keys(erpMeanData.index);
    
        // Extract mean time series data
        const meanTimeSeries = erpMeanData['Mean_Time_Series'];
    
        // Extract mean value data
        const meanValue = erpMeanData['Mean_Value'];
    
        // Extract standard deviation data
        const stdValue = erpMeanData['Standard_Deviation'];
    
        // Update existing traces with new data
        Plotly.restyle('erp-plot', {
            x: [time, time, time], // Wrap x data for each trace in an array
            y: [meanTimeSeries, meanValue, stdValue] // Wrap y data for each trace in an array
        });
    
        // Manually set the range of y-axis
        Plotly.relayout('erp-plot', {
            'yaxis.range': [Math.min(...meanTimeSeries, ...meanValue, ...stdValue), Math.max(...meanTimeSeries, ...meanValue, ...stdValue)]
        });
    }
    }
    

    plotDummy() {

        var trace1 = {
            x: [1, 2, 3, 4],
            y: [10, 15, 13, 17],
            type: 'scatter'
          };
          
          var trace2 = {
            x: [1, 2, 3, 4],
            y: [16, 5, 11, 9],
            type: 'scatter'
          };
          
          var data = [trace1, trace2];
          
          Plotly.newPlot('dumb-plot', data);
    }
}

// Load settings and initialize ERPClass
load_settings().then(async settings => {
    // Initialize the ERP class
    let ERP = new ERPClass(settings.erp);

    // Subscribe to 'erp' data
    ERP.io.subscribe('erp');

    // Listen for 'erp' data and plot it immediately
    ERP.io.on('erp', (data, meta) => {
        if (data == null) {
            return;
        }
        else {
            ERP.plotErpMean(data);
        }
    });
});
