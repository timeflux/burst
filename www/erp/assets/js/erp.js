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

        // Initialize class constants
        this.frequency = 500;
        this.plot_container = 'plot-container';
        this.electrodes_selector = 'electrode-selector';

        // Initialize plots
        this.initPlots();

    }

    initPlots() {
        // Initialize erp-plot with empty data
        this.traces = [];
        this._electrodes = [];

        Plotly.newPlot(this.plot_container, this.traces);
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

    plotData(data) {
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
            traces.push({
                x: x_time.map((value, index) => (value - x_time[0]) / this.frequency),
                y: meanTimeSeries,
                mode: 'lines',
                name: electrode
            });
        }

        const layout = {
            xaxis: {
                title: 'Time (ms)'
            },
            yaxis: {
                title: 'Amplitude'
            }
        };

        Plotly.newPlot(this.plot_container, traces, layout);
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

    // Listen for 'erp' 
    ERP.io.on('erp', (data, meta) => {
        // Check if electrodes and selection are initialized : if not, initialize them
        if (ERP._electrodes.length === 0) {
            ERP.initElectrodes(data);
            ERP.initElectrodeSelector();
        }
        // Plot the data
        ERP.plotData(data);
    });
});
