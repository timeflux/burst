class ERPClass {
    constructor() {
        this.setupSubscriptions();
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
        const time = erpMeanData.index;
    
        // Extract channel names (assuming they are column names of the DataFrame)
        const channels = Object.keys(erpMeanData.columns);
    
        // Extract amplitude data for each channel
        const amplitudeData = channels.map(channel => erpMeanData[channel]);
    
        // Create traces for each channel
        const traces = channels.map((channel, index) => ({
            x: time,
            y: amplitudeData[index],
            mode: 'lines',
            name: channel // Use channel name as trace name
        }));
    
        // Update the plot with the new data
        Plotly.newPlot('erp-plot', traces);
    }
}

let erpClass = new ERPClass();