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

        // Initialize class constants and variables
        this.frequency = 500;
        this.plot_target = 'plot-container';
        this.plot_non_target = 'plot-non-container';
        this.electrodes_selector = 'electrode-selector';
        this.normalizeData = false;
        this.showNonTarget = false;
        this._electrodes = [];

        // Initialize plots
        this.initPlots();

        // Initialize normalize checkbox
        this.initNormalizeCheckbox();
        this.initNonTargetCheckbox();
    }

    initPlots() {
        // Initialize erp-plot with empty data
        this.traces = [];

        Plotly.newPlot(this.plot_target, this.traces);
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

    updateNormalizeState() {
        this.normalizeData = document.getElementById('normalize-checkbox').checked;
    }

    initNonTargetCheckbox() {
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

    updateNonTargetState() {
        this.showNonTarget = document.getElementById('non-target-checkbox').checked;
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
            const globalMax = Math.max(...allValues);
            const globalMin = Math.min(...allValues);

            // Normalize using global maximum and minimum
            if (this.normalizeData) {
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

}

// Load settings and initialize ERPClass
load_settings().then(async settings => {
    // Initialize the ERP class
    let ERP = new ERPClass(settings.erp);

    // Subscribe to 'erp' data
    ERP.io.subscribe('erp');
    ERP.io.subscribe('erp_non_target');

    // Listen for 'erp' 
    ERP.io.on('erp', (data, meta) => {
        // Check if electrodes and selection are initialized : if not, initialize them
        if (ERP._electrodes.length === 0) {
            ERP.initElectrodes(data);
            ERP.initElectrodeSelector();
        }
        // Plot the data
        ERP.plotData(data, ERP.plot_target);
    });

    // Listen for 'erp_non_target'
    ERP.io.on('erp_non_target', (data, meta) => {
        // Check if electrodes and selection are initialized : if not, initialize them
        if (ERP._electrodes.length === 0) {
            ERP.initElectrodes(data);
            ERP.initElectrodeSelector();
        }
        // Plot the data
        if (ERP.showNonTarget == true) {
            ERP.plotData(data, ERP.plot_non_target);
        }
        else {
            Plotly.purge(ERP.plot_non_target)
        }
    });
});
