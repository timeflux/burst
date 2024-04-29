class ERPClass {
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
                name: 'Mean Epoch'
            },
        ];

        this._electrodes = [];

        Plotly.newPlot('erp-plot', this.traces);
    }

    plotData_std(data) {
        // Get the length of the data
        const length = Object.keys(data).length;
    
        // Initialize arrays to store the values
        const meanTimeSeries = [];
        const meanValue = data[0]['Mean_Value'];
        const stdValue = [];
    
        // Iterate through each data point
        for (let key in data) {
            const element = data[key];
            meanTimeSeries.push(element['Mean_Time_Series']);
            stdValue.push(element['Standard_Deviation']);
        }
    
        // Calculate the upper and lower bounds for the envelope
        const upperBound = meanTimeSeries.map((value, index) => value + stdValue[index]);
        const lowerBound = meanTimeSeries.map((value, index) => value - stdValue[index]);
    
        // Plot the data
        const traces = [
            {
                x: Array.from({length}, (_, i) => i), // Create an array of indices from 0 to (length - 1)
                y: meanTimeSeries,
                mode: 'lines',
                name: 'Mean Epoch'
            },
            {
                x: Array.from({length}, (_, i) => i), // Create an array of indices from 0 to (length - 1)
                y: upperBound,
                fill: 'tonexty', // Fill the area between upper and lower bounds
                mode: 'none', // No line for the envelope
                name: 'Mean + Std'
            },
            {
                x: Array.from({length}, (_, i) => i), // Create an array of indices from 0 to (length - 1)
                y: lowerBound,
                fill: 'tonexty', 
                mode: 'none',
                name: 'Mean - Std'
            }
        ];


        const layout = {
            xaxis: {
                title: 'Time step'
            },
            yaxis: {
                title: 'Amplitude'
            }
        };
    
        Plotly.newPlot('erp-plot', traces, layout);
    }

    plotData_obsolete(data) {
        // Get the length of the data
        const length = Object.keys(data).length;
    
        // Initialize arrays to store the values
        const meanTimeSeries = [];

        // Iterate through each data point
        for (let key in data) {
            const element = data[key];
            meanTimeSeries.push(element['Mean_Time_Series']);
        }
    
        // Plot the data
        const traces = [
            {
                x: Array.from({length}, (_, i) => i), // Create an array of indices from 0 to (length - 1)
                y: meanTimeSeries,
                mode: 'lines',
                name: 'Mean Epoch'
            }
        ];

        const layout = {
            xaxis: {
                title: 'Time step'
            },
            yaxis: {
                title: 'Amplitude'
            }
        };
    
        Plotly.newPlot('erp-plot', traces, layout);
    }

    plotData(data) {
        // Get the length of the data
        const length = Object.keys(data).length;
    
        // Initialize arrays to store the values for each electrode
        const traces = [];
        for (let electrode of this._electrodes) {
            const meanTimeSeries = [];
            for (let key in data) {
                const element = data[key];
                meanTimeSeries.push(element[electrode]);
            }
            traces.push({
                x: Array.from({length}, (_, i) => i), // Create an array of indices from 0 to (length - 1)
                y: meanTimeSeries,
                mode: 'lines',
                name: electrode
            });
        }
        
        const layout = {
            xaxis: {
                title: 'Time step'
            },
            yaxis: {
                title: 'Amplitude'
            }
        };

        Plotly.newPlot('erp-plot', traces, layout);
    }

    electrode_update(data) {
        const firstEntry = Object.values(data)[0];
        const electrodeNames = Object.keys(firstEntry);

        this._electrodes = electrodeNames;
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
    let ERP = new ERPClass(settings.erp);

    // Subscribe to 'erp' data
    ERP.io.subscribe('erp');

    // Listen for 'erp' data and plot it immediately
    ERP.io.on('erp', (data, meta) => {
        if (ERP._electrodes.length === 0) {
            ERP.electrode_update(data);
        }
        //console.log(data);
        //console.log(ERP._electrodes);
        ERP.plotData(data);
    });
});
