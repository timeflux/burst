'use strict';

/**
 * Display an overlay notification
 *
 * @param {string} [title] - notification title
 * @param {string} [message] - notification message
 * @param {string} [footer] - notification footer
 */
function notify(title = '', message = '', footer = '') {
    document.getElementById('title').innerHTML = title;
    document.getElementById('message').innerHTML = message;
    document.getElementById('footer').innerHTML = footer;
    document.getElementById('overlay').classList.remove('hidden');
}

/**
 * Toggle a HTML element class
 *
 * @param {string|object} element - element id or DOM object
 * @param {string} [cls] - class name
 */
function toggle(element, cls = 'hidden') {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    element.classList.toggle(cls);
}

/**
 * Set a CSS variable
 *
 * @param {string} name - variable name
 * @param {string|number} value - variable value
 */
function set_css_var(name, value) {
    document.documentElement.style.setProperty(name, value);
}

/**
 * Get a CSS variable
 *
 * @param {string} name -variable name
 */
function get_css_var(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name);
}


/**
 * A Burst VEP controller
 *
 */
class Burst {

    /**
     * @param {Object} [options]
     * @param {array} options.targets - a list of burst code (one per target)
     * @param {Object} [options.training]
     * @param {number} [options.training.cycles] - the number of rounds for each target during calibration
     * @param {number} [options.training.repetitions] - the number of repetitions during each cycle
     * @param {number} [options.training.duration_rest] - the rest period before a new target is presented, in ms
     * @param {number} [options.training.duration_focus_on] - the duration of the highlight
     * @param {number} [options.training.duration_focus_off] - the duration of the pause before the code starts flashing
     * @param {Object} [options.validation]
     * @param {number} [options.validation.duration_rest] - the rest period before the free run begins, in ms
     * @param {number} [options.validation.duration_focus_on] - the duration of the feedback when a prediction is received
     * @param {number} [options.validation.duration_focus_off] - the rest period after the feedback
     * @param {Object} [options.colors]
     * @param {string} [options.colors.background] - the background color
     * @param {string} [options.colors.target] - the target color during the off-state
     * @param {string} [options.colors.border] - the border color
     */
    constructor(options = {}) {

        // Merge options
        let default_options = {
            targets: [],
            training: {
                cycles: 3,
                repetitions: 2,
                duration_rest: 2000,
                duration_focus_on: 1500,
                duration_focus_off: 500
            },
            validation: {
                duration_rest: 2000,
                duration_focus_on: 1500,
                duration_focus_off: 500
            },
            colors: {
                background: '#797979',
                target: '#797979',
                border: '#000000'
            }
        };
        this.options = merge(default_options, options);
        //console.log(this.options);

        // Initialize UI
        set_css_var('--background-color', this.options.colors.background);
        set_css_var('--target-color', this.options.colors.target);
        set_css_var('--border-color', this.options.colors.border);

        // Initialize status
        this.status = 'idle';

        // Initialize targets
        this.target = null;
        this.targets = [];
        const targets = document.getElementsByClassName('target');
        for (let target = 0; target < this.options.targets.length; target++) {
            this.targets[target] = {
                index: target,
                pattern: this.options.targets[target],
                element: targets[target],
            }
        }
        //console.log(this.targets);

        // Initialize sequence
        // Assume that all targets are of equal length
        this.sequence = new Sequence(this.options.targets[0].length)

        // Initialize events
        this.io = new IO();
        this.io.on('connect', () => this.io.event('session_begins', this.options));
        window.onbeforeunload = () => {
            this.io.event('session_ends');
        }

        // Initialize scheduler
        this.scheduler = new Scheduler();
        this.scheduler.start();
        this.scheduler.on('tick', this._tick.bind(this));

    }

    /**
     * Start calibration
     */
    async calibrate() {

        // Send start event
        this.io.event('calibration_begins');

        // Highlight each target
        for (let cycle = 0; cycle < this.options.training.cycles; cycle++) {
            for (let target of this.targets) {
                this.target = target.index;
                await sleep(this.options.training.duration_rest);
                toggle(target.element, 'highlight');
                await sleep(this.options.training.duration_focus_on);
                toggle(target.element, 'highlight');
                await sleep(this.options.training.duration_focus_off);
                this.status = 'calibration';
                await flag('done');
            }
        }

        // Pause for a bit
        await sleep(this.options.training.duration_rest);

        // Send stop event
        this.io.event('calibration_ends');

    }

    /**
     * Start the main loop
     */
    async run() {

        // Send start event
        this.io.event('validation_begins');

        // Pause for a bit
        await sleep(this.options.validation.duration_rest);

        // Run until a prediction is received
        while (true) {
            this.status = 'validation';
            let target = await flag('predict');
            toggle(this.targets[target].element, 'lock');
            await sleep(this.options.validation.duration_focus_on);
            toggle(this.targets[target].element, 'lock');
            await sleep(this.options.validation.duration_focus_off);
        }

        // Send stop event
        this.io.event('validation_ends');

    }

    /**
     * Called on each screen refresh
     */
    _tick(scheduled, called, ellapsed, fps) {

        // Run only during calibration and main loop
        if (this.status == 'idle') return;

        // Send epoch markers
        if (this.sequence.index == 0) {
            this.io.event('epoch', { target: this.target });
        }

        // Update DOM and advance sequence
        for (const target of this.targets) {
            if (target.pattern[this.sequence.index] == '1') {
                target.element.classList.remove('off');
                target.element.classList.add('on');
            } else {
                target.element.classList.remove('on');
                target.element.classList.add('off');
            }
        }
        this.sequence.next();

        // Stop calibration
        if (this.status == 'calibration') {
            if (this.sequence.cycle == this.options.training.repetitions) {
                trigger('done');
                this._reset();
            }
        }

        // Stop validation (single trial)
        // TODO: handle continuous classification
        if (this.status == 'validation') {
            //console.log(this.sequence.cycle, this.sequence.index);
            if (this.sequence.cycle == 1) {
                this._reset();
            }
        }

    }

    /**
     * Reset targets
     */
    _reset() {
        for (const target of this.targets) {
            target.element.classList.remove('on');
            target.element.classList.add('off');
        }
        this.status = 'idle';
        this.target = null;
        this.sequence.reset();
    }

}


class Sequence {

    constructor(length, start=0) {
        this.length = length;
        this.start = start;
        this.index = start;
        this.cycle = 0;
    }

    next() {
        this.index++;
        if (this.index == this.length) {
            this.index = 0;
        }
        if (this.index == this.start) {
            this.cycle ++;
        }
        return this.index;
    }

    prev() {
        this.index--;
        if (this.index == -1) {
            this.index = this.length - 1;
        }
        if (this.index == this.start) {
            this.cycle ++;
        }
        return this.index;
    }

    reset() {
        this.index = this.start;
        this.cycle = 0;
    }

}


load_settings().then(async settings => {

    // Initialize
    let burst = new Burst(settings.bvep);

    // Handle events
    burst.io.subscribe('predictions');
    burst.io.on('predictions', (data, meta) => {
        for (let row of Object.values(data)) {
            switch (row.label) {
                case 'ready':
                    trigger('ready');
                case 'predict':
                    //console.log('predict');
                    trigger('predict', JSON.parse(row.data).result);
            }
        }
    });

    // Display the initial message
    notify(
        'Welcome',
        'We will now start the calibration procedure.<br>Please stay still and try not to blink.<br>Look at the target that will be higlighted in blue.<br>For increased accuracy, we recommend that you silently count the short flashes that will appear inside the designated target.',
        'Press any key to continue'
    )
    await key();
    toggle('overlay');
    toggle('targets');

    // Start calibration
    await burst.calibrate();

    // Wait for model training
    notify(
        'Training the model',
        '<img src="assets/img/spinner.png" />',
        'Please wait'
    )
    await flag('ready');
    toggle('overlay');

    // Start main loop
    burst.run();

});
