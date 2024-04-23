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
        } else {
            // Extract time points (assuming they are in the index of the DataFrame)
            //const time = Object.keys(erpMeanData.index || {});
            
            // Extract mean time series data
            const meanTimeSeries = erpMeanData['Mean_Time_Series'] || [];
            
            // Extract mean value data
            const meanValue = erpMeanData['Mean_Value'] || [];
            
            // Extract standard deviation data
            const stdValue = erpMeanData['Standard_Deviation'] || [];
            
            // Update existing traces with new data
            Plotly.restyle('erp-plot', {
                //x: [time, time, time], // Wrap x data for each trace in an array
                y: [meanTimeSeries, meanValue, stdValue] // Wrap y data for each trace in an array
            });
            
            // Manually set the range of y-axis
            // Plotly.relayout('erp-plot', {
            //    'yaxis.range': [Math.min(...meanTimeSeries, ...meanValue, ...stdValue), Math.max(...meanTimeSeries, ...meanValue, ...stdValue)]
            // });
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

class ERPClass2 {
    constructor() {
        // Initialize events
        this.io = new IO();
        this.io.on('connect', () => this.io.event('session_begins', this.options));
        window.onbeforeunload = () => {
            this.io.event('session_ends');
        }

        this.time = 0;

        // Initialize scheduler
        this.scheduler = new Scheduler();
        this.scheduler.start();

        // Initialize plots
        this.initPlots();
    }

    initPlots() {
        // Initialize erp-plot with empty data
        this.traces = [
            {
                x: [],
                y: [],
                mode: 'lines',
                name: 'Mean Time Series'
            },
            {
                x: [],
                y: [],
                mode: 'lines',
                name: 'Mean Value'
            },
            {
                x: [],
                y: [],
                mode: 'lines',
                name: 'Standard Deviation'
            }
        ];

        Plotly.newPlot('erp-plot', this.traces);
    }


    plotErpMean(erpMeanData) {
        // Extract mean time series data
        var meanTimeSeries = erpMeanData['Mean_Time_Series'];
        
        // Extract mean value data
        var meanValue = erpMeanData['Mean_Value'];
        
        // Extract standard deviation data
        var stdValue = erpMeanData['Standard_Deviation'];
    
        this.time += 1;
    
        // Push the new x value
        this.traces.forEach(trace => {
            trace.x.push(this.time);
            // Keep only the last 300 values
            if (trace.x.length > 300) {
                trace.x.shift(); // Remove the first element
            }
        });
    
        // Push the new y values
        this.traces[0].y.push(meanTimeSeries);
        this.traces[1].y.push(meanValue);
        this.traces[2].y.push(stdValue);
    
        // Keep only the last 300 values
        this.traces.forEach(trace => {
            if (trace.y.length > 300) {
                trace.y.shift(); // Remove the first element
            }
        })
        
        Plotly.newPlot('erp-plot', this.traces);
    }

    plotData(data) {
        // Initialize arrays to store the values
        var meanTimeSeries = [];
        var meanValue = [];
        var stdValue = [];
    
        for (let key in data) {
            const element = data[key];
            meanTimeSeries.push(element['Mean_Time_Series']);
            meanValue.push(element['Mean_Value']);
            stdValue.push(element['Standard_Deviation']);
        }

        var mean_plus_std = meanTimeSeries + stdValue;
        var mean_minus_std = meanTimeSeries - stdValue;
    
        // Plot the data
        var traces1 = [
            {
                x: Array.from({length: 300}, (_, i) => i), // Create an array of indices from 0 to 299
                y: meanTimeSeries,
                mode: 'lines',
                name: 'Mean Time Series'
            },
            {
                x: Array.from({length: 300}, (_, i) => i), // Create an array of indices from 0 to 299
                y: mean_plus_std,
                mode: 'lines',
                name: 'Mean - Std'
            },
            {
                x: Array.from({length: 300}, (_, i) => i), // Create an array of indices from 0 to 299
                y: mean_minus_std,
                mode: 'lines',
                name: 'Mean + Std'
            }
        ];
        var traces2 = {
            x: Array.from({length: 300}, (_, i) => i),
            y: meanValue,
            mode: 'lines',
            name: 'Mean Value'
        }
        
        var traces3 = [{
            x: Array.from({length: 300}, (_, i) => i),
            y: stdValue,
            mode: 'lines',
            name: 'Standard Deviation'
        }]
    
        Plotly.newPlot('erp-plot', traces3);
        // Plotly.newPlot('mean-plot', traces);
    }

}


function exploreObject(obj) {
    // Check if the object is an array
    if (Array.isArray(obj)) {
        console.log("Object is an array");
        // Iterate over the array elements
        obj.forEach(element => {
            exploreObject(element); // Recursively explore nested elements
        });
    } else if (typeof obj === 'object' && obj !== null) {
        console.log("Object is a non-null object");
        // Iterate over the object keys
        for (let key in obj) {
            console.log(`${key}:`);
            exploreObject(obj[key]); // Recursively explore nested objects
        }
    } else {
        console.log("Object is a primitive value or null");
        console.log(obj);
    }
}
function checkDataShape(data) {
    const columns = Object.keys(data);
    const numberOfRows = data[columns[0]].length; // Assuming the first column has the same length for all rows
    const numberOfColumns = columns.length;

    console.log("Number of rows:", numberOfRows);
    console.log("Number of columns:", numberOfColumns);
    console.log("Data shape")
}


// Load settings and initialize ERPClass
load_settings().then(async settings => {
    // Initialize the ERP class
    let ERP = new ERPClass2(settings.erp);

    // Subscribe to 'erp' data
    ERP.io.subscribe('erp');

    // Listen for 'erp' data and plot it immediately
    ERP.io.on('erp', (data, meta) => {
        //console.log(data);
        ERP.plotData(data);
    });


});
