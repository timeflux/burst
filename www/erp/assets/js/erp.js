class ERPClass {
    constructor() {
        // this.setupSubscriptions();
    }

    setupSubscriptions() {
        // Subscribe to 'erp' data
        this.io.subscribe('erp');
        
        // Listen for 'erp' data and plot it immediately
        this.io.on('erp', (data, meta) => {
            this.plotErpData(data);
        });
    }

    plotErpMean(erpMeanData) {
        // Extract time points (assuming they are in the index of the DataFrame)
        const time = Object.keys(erpMeanData.index);
    
        // Extract mean time series data
        const meanTimeSeries = erpMeanData['mean-time series'];
    
        // Extract mean value data
        const meanValue = erpMeanData['mean value'];
    
        // Extract standard deviation data
        const stdValue = erpMeanData['std value'];
    
        // Create traces
        const traces = [
            {
                x: time,
                y: meanTimeSeries,
                mode: 'lines',
                name: 'Mean Time Series'
            },
            {
                x: time,
                y: meanValue,
                mode: 'lines',
                name: 'Mean Value'
            },
            {
                x: time,
                y: stdValue,
                mode: 'lines',
                name: 'Standard Deviation'
            }
        ];
    
        // Update the plot with the new data
        Plotly.newPlot('erp-plot', traces);
    }
}

load_settings().then(async settings => {
    // Initialize the ERP class
    let ERP = new ERPClass(settings.erp);

    // Subscribe to 'erp' data
    ERP.io.subscribe('erp');
        
    // Listen for 'erp' data and plot it immediately
    ERP.io.on('erp', (data, meta) => {
        ERP.plotErpData(data);
    });
});
