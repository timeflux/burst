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
 * @param {string} name - variable name
 */
function get_css_var(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name);
}

/**
 * Convert an hexadecimal color to RGBA
 *
 * @param {string} hex - the hexadecimal color
 * @param {number} opacity - the alpha value
 */
function hex_to_rgba(hex, opacity) {
    return 'rgba(' + (hex = hex.replace('#', ''))
        .match(new RegExp('(.{' + hex.length/3 + '})', 'g'))
        .map(function(l) { return parseInt(hex.length%2 ? l+l : l, 16) })
        .concat(isFinite(opacity) ? opacity : 1)
        .join(',') + ')';
}

/**
 * Shuffle an array
 *
 * This is done in-place. Make a copy first with .slice(0) if you don't want to
 * modify the original array.
 *
 * @param {array} array - the array to shuffle
 *
 * @see:https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle#The_modern_algorithm
 */
function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

/**
 * Generate a random integer
 *
 * @param {number} max - the maximum value
 */
function get_random_int(max) {
    return Math.floor(Math.random() * max);
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
     * @param {number} [options.training.blocks] - the number of rounds for each target during calibration
     * @param {number} [options.training.repetitions] - the number of repetitions for each target during each block
     * @param {number} [options.training.duration_rest] - the rest period before a new target is presented, in ms
     * @param {number} [options.training.duration_cue_on] - the duration of the cue
     * @param {number} [options.training.duration_cue_off] - the duration of the pause before the code starts flashing
     * @param {Object} [options.task]
     * @param {boolean} [options.task.enable] - true if the cued task must be enabled, false otherwise
     * @param {(number|array)} [options.task.targets] - the number of random targets or the list of targets to be cued
     * @param {Object} [options.validation]
     * @param {number} [options.validation.duration_rest] - the rest period before the free run begins, in ms
     * @param {number} [options.validation.duration_lock_on] - the duration of the feedback when a prediction is received
     * @param {number} [options.validation.duration_lock_off] - the rest period after the feedback
     * @param {Object} [options.stim]
     * @param {string} [options.stim.type] - the stimulus type ('gabord', 'ricker', 'face', 'plain')
     * @param {number} [options.stim.depth] - the stimulus opacity (0-1)
     * @param {Object} [options.colors]
     * @param {string} [options.colors.background] - the background color (hexadecimal)
     * @param {string} [options.colors.target_off] - the target color during the off-state (hexadecimal)
     * @param {string} [options.colors.target_on] - the target color during the on-state, if stim.type is 'plain' (hexadecimal)
     * @param {string} [options.colors.target_border] - the border color (hexadecimal)
     * @param {string} [options.colors.target_cue] - the cue border color (hexadecimal)
     * @param {string} [options.colors.target_success] - the target color when the task is successful (hexadecimal)
     * @param {string} [options.colors.target_failure] - the target color when the task failed (hexadecimal)
     * @param {string} [options.colors.target_lock] - the prediction color (hexadecimal)
     */
    constructor(options = {}) {

        // Merge options
        let default_options = {
            targets: [],
            training: {
                blocks: 5,
                repetitions: 2,
                duration_rest: 2000,
                duration_cue_on: 1500,
                duration_cue_off: 500
            },
            task: {
                enabled: true,
                targets: 5
            },
            validation: {
                duration_rest: 2000,
                duration_lock_on: 1500,
                duration_lock_off: 500
            },
            stim: {
                type: 'gabor',
                depth: .8
            },
            colors: {
                background: '#797979',
                target_off: '#797979',
                target_on: '#FFFFFF',
                target_border: '#000000',
                target_cue: 'blue',
                target_success: 'green',
                target_failure: 'red',
                target_lock: 'blue'
            }
        };
        this.options = merge(default_options, options);

        // Initialize UI
        set_css_var('--background-color', this.options.colors.background);
        set_css_var('--target-off-color', this.options.colors.target_off);
        set_css_var('--target-on-color', this.options.colors.target_on);
        set_css_var('--target-border-color', this.options.colors.target_border);
        set_css_var('--target-cue-color', this.options.colors.target_cue);
        set_css_var('--target-success-color', this.options.colors.target_success);
        set_css_var('--target-failure-color', this.options.colors.target_failure);
        set_css_var('--target-lock-color', this.options.colors.target_lock);
        set_css_var('--target-url', 'url(../img/' + this.options.stim.type + '.png)');
        set_css_var('--target-depth', hex_to_rgba(this.options.colors.target_off, 1 - this.options.stim.depth));

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

        // Initialize sequences
        // Assume that all sequences are of equal length
        this.sequence = new Sequence(this.options.targets[0].length)

        // Initialize cued task
        this.score = 0;
        if (this.options.task.enabled) {
            if (Number.isInteger(this.options.task.targets)) {
                let tasks = [];
                for (let i = 0; i < this.options.task.targets; i++) {
                    tasks.push(get_random_int(this.targets.length));
                }
                this.options.task.targets = tasks;
            }
        }

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

        // Cue each target
        let targets = this.targets.slice(0);
        for (let block = 0; block < this.options.training.blocks; block++) {
            shuffle(targets);
            for (let target of targets) {
                this.target = target.index;
                await sleep(this.options.training.duration_rest);
                this.io.event('cue', {target: target.index});
                toggle(target.element, 'cue');
                await sleep(this.options.training.duration_cue_on);
                toggle(target.element, 'cue');
                await sleep(this.options.training.duration_cue_off);
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
     * Start the evaluation task
     */
    async task() {

        // Send start event
        this.io.event('task_begins');

        // Initialize scoring
        let matches = 0;
        let color = '';

        // Cue selected targets and wait for a prediction
        for (let index of this.options.task.targets) {
            let target = this.targets[index];
            await sleep(this.options.training.duration_rest);
            this.io.event('cue', {target: target.index});
            toggle(target.element, 'cue');
            await sleep(this.options.training.duration_cue_on);
            toggle(target.element, 'cue');
            await sleep(this.options.training.duration_cue_off);
            this.status = 'task';
            let predicted = await flag('predict');
            this.status = 'idle';
            this._reset();
            if (index == predicted) {
                matches++;
                color = 'success';
            } else {
                color = 'failure'
            }
            toggle(this.targets[predicted].element, color);
            await sleep(this.options.validation.duration_lock_on);
            toggle(this.targets[predicted].element, color);
            await sleep(this.options.validation.duration_lock_off);
        }

        // Compute final score
        this.score = Math.round(matches * 100 / this.options.task.targets.length);

        // Pause for a bit
        await sleep(this.options.validation.duration_rest);

        // Send stop event
        this.io.event('task_ends');

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
            this.status = 'idle';
            this._reset();
            toggle(this.targets[target].element, 'lock');
            await sleep(this.options.validation.duration_lock_on);
            toggle(this.targets[target].element, 'lock');
            await sleep(this.options.validation.duration_lock_off);
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
        let meta = {'index': this.sequence.index};
        if (this.status == 'calibration') {
            meta['cue'] = this.target;
            meta['bit'] = parseInt(this.targets[this.target].pattern[this.sequence.index]);
        } else {
            meta['bits'] = this.targets.map((target) => parseInt(target.pattern[this.sequence.index]));
        }
        this.io.event('epoch', meta);

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

        // Stop calibration for the current target
        if (this.status == 'calibration') {
            if (this.sequence.cycle == this.options.training.repetitions) {
                trigger('done');
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
                    trigger('predict', JSON.parse(row.data).target);
            }
        }
    });

    // Display the fixation cross
    notify(
        '',
        '<div class="marker center"></div>',
        'Press any key to continue'
    )
    await key();
    toggle('overlay');

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

    // Cued task
    if (burst.options.task.enabled) {
        notify(
            'All set!',
            'Now, let us flex these Jedi muscles.<br>Try to activate the designated target.',
            'Press any key to continue'
        )
        await key();
        toggle('overlay');
        await burst.task();
        notify(
            'Congratulations!',
            `You have achieved a score of ${burst.score}%.<br>If you want, you can now freely play with the interface.`,
            'Press any key to continue'
        )
        await key();
        toggle('overlay');
    }

    // Start main loop
    burst.run();

});
