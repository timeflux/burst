class ERPClass {
    constructor() {
        // Initialize events using inherited IO class from timeflux.js
        this.io = new IO();
        this.io.on('connect', () => this.io.event('session_begins', this.options));
        window.onbeforeunload = () => {
            this.io.event('session_ends');
        }

        // Initialize scheduler
        this.scheduler = new Scheduler();
        this.scheduler.start();

        // Initialize class constants and variables with default values
        this.frequency = 500;
        this.plot_target = 'plot-container';
        this.plot_non_target = 'plot-non-container';
        this.plot_sliding = 'plot-sliding-container';
        this.electrodes_selector = 'electrode-selector';
        this.normalizeData = false;
        this.showNonTarget = false;
        this._electrodes = [];
        this.event_accumulation_stop = "calibration_ends";

        // Initialize normalize checkbox
        this.initNormalizeCheckbox();
        this.initNonTargetCheckbox();
        this.initSlidingCheckbox();
    }

    initElectrodes(data) {
        // Get the names of the electrodes from the first entry of the data
        // Initialize electrodes and selected electrodes
        const firstEntry = Object.values(data)[0];
        const electrodeNames = Object.keys(firstEntry);

        this._electrodes = electrodeNames;
        this.selected_electrodes = [...electrodeNames];
    }

    initElectrodeSelector() {
        // Create checkboxes for electrode selection and event listener for change
        const electrodeSelector = document.getElementById(this.electrodes_selector);
        for (let electrode of this._electrodes) {
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = electrode;
            checkbox.value = electrode;
            checkbox.checked = true; // Check all checkboxes by default
            checkbox.addEventListener('change', () => this.updateSelectedElectrodes());

            const label = document.createElement('label');
            label.htmlFor = electrode;
            label.appendChild(document.createTextNode(electrode));

            electrodeSelector.appendChild(checkbox);
            electrodeSelector.appendChild(label);
            electrodeSelector.appendChild(document.createElement('br'));
        }
    }

    initNormalizeCheckbox() {
        // Initialize the checkbox for normalizing the data
        const container = document.getElementById('options-container'); // Change this to the ID of the container where you want to append the checkbox
        const normalizeCheckbox = document.createElement('input');
        normalizeCheckbox.type = 'checkbox';
        normalizeCheckbox.id = 'normalize-checkbox';
        normalizeCheckbox.checked = this.normalizeData; // Set initial state based on this.normalizeData
        normalizeCheckbox.addEventListener('change', () => this.updateNormalizeState());
    
        const label = document.createElement('label');
        label.htmlFor = 'normalize-checkbox';
        label.textContent = 'Normalize Data';
    
        container.appendChild(normalizeCheckbox);
        container.appendChild(label);
    }

    initNonTargetCheckbox() {
        // Initialize the checkbox for showing the non target ERP plot
        const container = document.getElementById('options-container'); 
        const nonTargetCheckbox = document.createElement('input');
        nonTargetCheckbox.type = 'checkbox';
        nonTargetCheckbox.id = 'non-target-checkbox';
        nonTargetCheckbox.checked = this.showNonTarget; 
        nonTargetCheckbox.addEventListener('change', () => this.updateNonTargetState());
    
        const label = document.createElement('label');
        label.htmlFor = 'non-target-checkbox';
        label.textContent = 'Show Non Target ERP Plot';
    
        container.appendChild(nonTargetCheckbox);
        container.appendChild(label);
    }

    initSlidingCheckbox() {
        // Initialize the checkbox for showing the sliding ERP plot
        const container = document.getElementById('options-container');
        const slidingCheckbox = document.createElement('input');
        slidingCheckbox.type = 'checkbox';
        slidingCheckbox.id = 'sliding-checkbox';
        slidingCheckbox.checked = this.showSliding;
        slidingCheckbox.addEventListener('change', () => this.updateSlidingState());

        const label = document.createElement('label');
        label.htmlFor = 'sliding-checkbox';
        label.textContent = 'Show Sliding Mean ERP Plot';

        container.appendChild(slidingCheckbox);
        container.appendChild(label);
    }

    plotData(data,container) {
        // Plot the data for the selected electrodes
        // Check if selected electrodes are initialized
        if (!this.selected_electrodes) {
            return;  
        }

        // Initialize arrays to store the values for each electrode
        const traces = [];
        for (let electrode of this.selected_electrodes) {
            const meanTimeSeries = [];
            const x_time = [];
            for (let key in data) {
                const element = data[key];
                x_time.push(key)
                meanTimeSeries.push(element[electrode]);
            }

            // Calculate global maximum and minimum values across all electrodes and time points
            let allValues = [];
            for (let electrode of this.selected_electrodes) {
                for (let key in data) {
                    allValues.push(data[key][electrode]);
                }
            }

            // Normalize using global maximum and minimum
            if (this.normalizeData) {
                const globalMax = Math.max(...allValues);
                const globalMin = Math.min(...allValues);
                const normalizedMeanTimeSeries = meanTimeSeries.map(value => (value - globalMin) / (globalMax - globalMin));
                traces.push({
                    x: x_time.map((value, index) => (value - x_time[0]) / this.frequency),
                    y: normalizedMeanTimeSeries,
                    mode: 'lines',
                    name: electrode
                });
            } else {
                traces.push({
                    x: x_time.map((value, index) => (value - x_time[0]) / this.frequency),
                    y: meanTimeSeries,
                    mode: 'lines',
                    name: electrode
                });
            }
        }

        let title;
        if (container === this.plot_target) {
            title = 'Target ERP Plot';
        } else if (container === this.plot_non_target) {
            title = 'Non Target ERP Plot';
        } else if (container === this.plot_sliding) {
            title = 'Sliding Mean ERP Plot';
        }

        const layout = {
            xaxis: {
                title: 'Time (ms)'
            },
            yaxis: {
                title: 'Amplitude'
            },
            title: title 
        };

        Plotly.newPlot(container, traces, layout);
        return traces;
    }

    updateSelectedElectrodes() {
        // Update the selected electrodes based on the checkboxes
        const selectedElectrodes = [];
        const checkboxes = document.querySelectorAll('#electrode-selector input[type="checkbox"]');
        for (let checkbox of checkboxes) {
            if (checkbox.checked) {
                selectedElectrodes.push(checkbox.value);
            }
        }
        this.selected_electrodes = selectedElectrodes;
    }

    updateNonTargetState() {
        this.showNonTarget = document.getElementById('non-target-checkbox').checked;
    }

    updateNormalizeState() {
        this.normalizeData = document.getElementById('normalize-checkbox').checked;
    }

    updateSlidingState() {
        this.showSliding = document.getElementById('sliding-checkbox').checked;
    }

}

function exportTracesToCSV(traces) {
    // Create a CSV string
    let csvContent = "data:text/csv;charset=utf-8,";

    // Add headers
    csvContent += "x,y\n";

    // Add data from each trace
    traces.forEach((trace, index) => {
        trace.x.forEach((xValue, i) => {
            csvContent += `${xValue},${trace.y[i]}\n`;
        });
    });

    // Create a Blob object from the CSV string
    const blob = new Blob([csvContent], { type: "text/csv" });

    // Create a link element to download the CSV file
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "traces.csv";

    // Append the link to the body and trigger the click event
    document.body.appendChild(link);
    link.click();

    // Cleanup
    document.body.removeChild(link);
}

// Load settings and initialize ERPClass
load_settings().then(async settings => {
    // Initialize the ERP class
    let ERP = new ERPClass(settings.erp);

    // Subscribe to 'erp' data
    ERP.io.subscribe('erp');
    ERP.io.subscribe('erp_non_target');
    ERP.io.subscribe('events_hdf5');
    ERP.io.subscribe('erp_sliding')

    // Listen for 'erp' 
    ERP.io.on('erp', (data, meta) => {
        // Check if electrodes and selection are initialized : if not, initialize them
        if (ERP._electrodes.length === 0) {
            ERP.initElectrodes(data);
            ERP.initElectrodeSelector();
        }
        // Plot the data
        ERP.traces = ERP.plotData(data, ERP.plot_target);
    });

    // Listen for 'erp_non_target'
    ERP.io.on('erp_non_target', (data, meta) => {
        // Check if electrodes and selection are initialized : if not, initialize them
        if (ERP._electrodes.length === 0) {
            ERP.initElectrodes(data);
            ERP.initElectrodeSelector();
        }
        // Plot the data if non target asked : if not, clear the plot
        if (ERP.showNonTarget == true) {
            ERP.plotData(data, ERP.plot_non_target);
        }
        else {
            Plotly.purge(ERP.plot_non_target)
        }
    });

    ERP.io.on('erp_sliding', (data, meta) => {
        // Check if electrodes and selection are initialized : if not, initialize them
        if (ERP._electrodes.length === 0) {
            ERP.initElectrodes(data);
            ERP.initElectrodeSelector();
        }
        // Plot the data if non target asked : if not, clear the plot
        if (ERP.showSliding == true) {
            ERP.plotData(data, ERP.plot_sliding);
        }
        else {
            Plotly.purge(ERP.plot_sliding)
        }
    });

    ERP.io.on('events_hdf5', (data, meta) => {
        const timestamps = Object.keys(data); // Get all timestamps
        const firstTimestamp = timestamps[0]; // Get the first timestamp
        const firstEventData = data[firstTimestamp]; // Get the event data at the first timestamp
        const label = firstEventData.label; // Get the label value of the first event
        if (label === ERP.event_accumulation_stop) {
            // Export traces to CSV
            console.log('Exporting traces to CSV...');
            exportTracesToCSV(ERP.traces);
    }});
});
