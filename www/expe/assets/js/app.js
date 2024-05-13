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
 * Set HTML content for the given element
 *
 * @param {string|object} element - element query or DOM object
 * @param {string} content - HTML content
 * @param {string} [cls] - classes
 */
function set_content(element, content, cls = '') {
    if (typeof element === 'string') {
        element = document.querySelector(element);
    }
    if (element === null ) return;
    element.innerHTML = content;
    element.setAttribute('class', cls);
}

/**
 * Set CSS class for the given element
 *
 * @param {string|object} element - element query or DOM object
 * @param {string} cls - classes
 */
function set_class(element, cls) {
    if (typeof element === 'string') {
        element = document.querySelector(element);
    }
    if (element === null ) return;
    element.classList.add(cls);
}

/**
 * Reset CSS class for all elements matching the query
 *
 * @param {string} elements - query or NodeList object
 */
function reset_class(elements) {
    if (typeof elements === 'string') {
        elements = document.querySelectorAll(elements);
    }
    for (let element of elements) {
        element.className = '';
    }
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
 * Compare two arrays
 *
 * @param {array} a - the first array
 * @param {array} b - the second array
 */
function array_equal(a, b) {
    return a.length === b.length && a.every((element, index) => element === b[index]);
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
     * @param {Object} options
     * @param {Object} options.codes
     * @param {array} options.codes.calibration - the list of burst codes for the calibration layout (one per target)
     * @param {array} options.codes.task - the list of burst codes for the task layout (one per target)
     * @param {Object} [options.layout]
     * @param {string} [options.layout.calibration] - the layout for the calibration stage ('single', 'simple', 'keyboard')
     * @param {string} [options.layout.task] - the layout for the task stages ('simple', 'grid', keyboard')
     * @param {Object} [options.calibration]
     * @param {number} [options.calibration.blocks] - the number of rounds during calibration
     * @param {number} [options.calibration.repetitions] - the number of cycles for each target
     * @param {boolean} [options.calibration.active_only] - display only the current target and mask the others
     * @param {number} [options.calibration.duration_rest] - the rest period before a new target is presented, in ms
     * @param {number} [options.calibration.duration_cue_on] - the duration of the cue
     * @param {number} [options.calibration.duration_cue_off] - the duration of the pause before the code starts flashing
     * @param {Object} [options.task]
     * @param {Object} [options.task.cue]
     * @param {boolean} [options.task.cue.enable] - true if the cued task must be enabled, false otherwise
     * @param {(number|array)} [options.task.cue.targets] - the number of random targets or the list of targets to be cued
     * @param {Object} [options.task.sequence]
     * @param {boolean} [options.task.sequence.enable] - true if the sequence task must be enabled, false otherwise
     * @param {(number|array)} [options.task.sequence.sequences] - the number of random sequences or the list of sequences to be typed
     * @param {boolean} [options.task.sequence.cue_target] - true if target cues must be enabled, false otherwise
     * @param {boolean} [options.task.sequence.cue_feedback] - true if feedback cues must be enabled, false otherwise
     * @param {Object} [options.run]
     * @param {number} [options.run.duration_rest] - the rest period before the free run begins, in ms
     * @param {number} [options.run.duration_lock_on] - the duration of the feedback when a prediction is received
     * @param {number} [options.run.duration_lock_off] - the rest period after the feedback
     * @param {Object} [options.stim]
     * @param {string} [options.stim.type] - the stimulus type ('gabord', 'ricker', 'face', 'plain')
     * @param {number} [options.stim.depth] - the stimulus opacity (0-1)
     * @param {Object} [options.colors]
     * @param {string} [options.colors.background] - the background color (hexadecimal)
     * @param {string} [options.colors.text] - the text color (hexadecimal)
     * @param {string} [options.colors.cross] - the fixation cross color (hexadecimal)
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
            codes: {
                calibration: [],
                task: []
            },
            layout: {
                calibration: 'single',
                task: 'keyboard'
            },
            calibration: {
                blocks: 5,
                repetitions: 3,
                active_only: false,
                duration_rest: 2000,
                duration_cue_on: 1500,
                duration_cue_off: 500
            },
            task: {
                cue: {
                    enable: true,
                    targets: 10
                },
                sequence: {
                    enable: true,
                    sequences: 10,
                    cue_target: false,
                    cue_feedback: true
                }
            },
            run: {
                duration_rest: 2000,
                duration_lock_on: 1500,
                duration_lock_off: 500
            },
            stim: {
                type: 'gabor',
                depth: .8
            },
            colors: {
                background: '#202020',
                text: '#FFFFFF',
                cross: '#FFFFFF',
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
        if (this.options.stim.type != 'plain') this.options.colors.target_on = this.options.colors.target_off;
        set_css_var('--background-color', this.options.colors.background);
        set_css_var('--text-color', this.options.colors.text);
        set_css_var('--marker-color', this.options.colors.cross);
        set_css_var('--target-off-color', this.options.colors.target_off);
        set_css_var('--target-on-color', this.options.colors.target_on);
        set_css_var('--target-border-color', this.options.colors.target_border);
        set_css_var('--target-cue-color', this.options.colors.target_cue);
        set_css_var('--target-success-color', this.options.colors.target_success);
        set_css_var('--target-failure-color', this.options.colors.target_failure);
        set_css_var('--target-lock-color', this.options.colors.target_lock);
        set_css_var('--target-url', 'url(../img/' + this.options.stim.type + '.png)');
        set_css_var('--target-depth', hex_to_rgba(this.options.colors.target_off, 1 - this.options.stim.depth));

        console.log(this.options.codes)

        // Initialize layouts
        this.layouts = {};
        for (let stage of ['calibration', 'task']) {
            this.layouts[stage] = { targets: [], sequence: null };
            // Targets
            const container = document.getElementById(`layout-${this.options.layout[stage]}`);
            const targets = container.getElementsByClassName('target');
            for (let target = 0; target < this.options.codes[stage].length; target++) {
                this.layouts[stage].targets[target] = {
                    index: target,
                    pattern: this.options.codes[stage][target],
                    element: targets[target],
                    label: targets[target].innerText
                }
            }
            // Sequence - assume that all sequences are of equal length
            this.layouts[stage].sequence = new Sequence(this.options.codes[stage][0].length)
        }

        // Initialize tasks
        // TODO: refactor
        this.score = 0;
        if (this.options.task.cue.enable) {
            if (Number.isInteger(this.options.task.cue.targets)) {
                let tasks = [];
                for (let i = 0; i < this.options.task.cue.targets; i++) {
                    tasks.push(get_random_int(this.layouts.task.targets.length));
                }
                this.options.task.cue.targets = tasks;
            }
        }
        if (this.options.task.sequence.enable) {
            if (Number.isInteger(this.options.task.sequence.sequences)) {
                let sequences = [];
                for (let i = 0; i < this.options.task.sequence.sequences; i++) {
                    let sequence = [];
                    for (let j = 0; j < 4; j++) {
                        sequence.push(get_random_int(this.layouts.task.targets.length - 1));
                    }
                    sequences.push(sequence);
                }
                this.options.task.sequence.sequences = sequences;
            }
        }

        // Initialize status
        this.running = false;
        this.stage = 'calibration';
        this.target = null;
        this.targets = this.layouts.calibration.targets;
        this.sequence = this.layouts.calibration.sequence;

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

        // Generate balanced target cues
        let targets = [];
        while (true) {
            if (targets.length < this.options.calibration.blocks) {
                targets = targets.concat(Object.values(this.targets.slice(0)));
                shuffle(targets);
            }
            if (targets.length > this.options.calibration.blocks) {
                targets = targets.slice(0, this.options.calibration.blocks);
            }
            if (targets.length == this.options.calibration.blocks) {
                break;
            }
        }

        // Pause for a bit
        await sleep(this.options.calibration.duration_rest);

        // Cue each target
        for (let target of targets) {
            this.target = target.index;
            let non_targets = this.targets.filter(i => i.index != target.index);
            if (this.options.calibration.active_only) {
                for (let non_target of non_targets) {
                    toggle(non_target.element);
                }
            }
            await sleep(this.options.calibration.duration_rest);
            this.io.event('cue', {target: target.index});
            toggle(target.element, 'cue');
            await sleep(this.options.calibration.duration_cue_on);
            toggle(target.element, 'cue');
            await sleep(this.options.calibration.duration_cue_off);
            this.running = true;
            await flag('done');
            if (this.options.calibration.active_only) {
                await sleep(this.options.calibration.duration_cue_off);
                for (let non_target of non_targets) {
                    toggle(non_target.element);
                }
            }
        }

        // Pause for a bit
        await sleep(this.options.calibration.duration_rest);

        // Send stop event
        this.io.event('calibration_ends');

        // Set the stage
        this.stage = 'task';
        this.targets = this.layouts.task.targets;
        this.sequence = this.layouts.task.sequence;

    }


    /**
     * Run the cue evaluation task
     */
    async task_cue() {

        // Send start event
        this.io.event('task_begins', {task: 'cue'});

        // Initialize scoring
        this.score = new Score().block();
        let color = '';

        // Cue selected targets and wait for a prediction
        for (let index of this.options.task.cue.targets) {
            let target = this.targets[index];
            await sleep(this.options.run.duration_rest);
            this.io.event('cue', {target: target.index});
            toggle(target.element, 'cue');
            await sleep(this.options.calibration.duration_cue_on);
            toggle(target.element, 'cue');
            await sleep(this.options.calibration.duration_cue_off);
            this.running = true;
            let event = await flag('predict');
            this.running = false;
            this._reset();
            let predicted = event.detail.target;
            let frames = event.detail.frames;
            if (index == predicted) {
                this.score.trial(1, frames);
                color = 'success';
            } else {
                this.score.trial(0, frames);
                color = 'failure';
            }
            toggle(this.targets[predicted].element, color);
            await sleep(this.options.run.duration_lock_on);
            toggle(this.targets[predicted].element, color);
            await sleep(this.options.run.duration_lock_off);
        }

        // Pause for a bit
        await sleep(this.options.run.duration_rest);

        // Send stop event
        this.io.event('task_ends', {score: this.score.stats()});

    }


    /**
     * Run the sequence evaluation task
     */
    async task_sequence() {

        // Send start event
        this.io.event('task_begins', {task: 'sequence'});

        // Initialize scoring
        this.score = new Score();

        // Show the feedback
        toggle('sequence', 'hidden');

        // Cue selected targets and wait for a prediction
        for (let sequence of this.options.task.sequence.sequences) {

            // Initial feedback
            set_content('#sequence :nth-child(1)', this.targets[sequence[0]].label, 'active');
            set_content('#sequence :nth-child(2)', this.targets[sequence[1]].label);
            set_content('#sequence :nth-child(3)', this.targets[sequence[2]].label);
            set_content('#sequence :nth-child(4)', this.targets[sequence[3]].label);

            // Initial state
            let preds = [];
            let target = 0;
            let expected = sequence[target];
            this.score.block();

            while (true) {

                // Cue
                await sleep(this.options.run.duration_rest);
                if (this.options.task.sequence.cue_target) {
                    toggle(this.targets[expected].element, 'cue');
                    await sleep(this.options.calibration.duration_cue_on);
                    toggle(this.targets[expected].element, 'cue');
                    await sleep(this.options.calibration.duration_cue_off);
                }

                // Wait for a prediction
                this.running = true;
                let event = await flag('predict');
                let predicted = event.detail.target;
                let frames = event.detail.frames;

                // Did we get it right?
                if (predicted == -1){
                    reset_class('#sequence span');
                    for (let i = 0; i < sequence.length; i++) {
                        toggle(this.targets[expected].element, 'cue');
                    }
                    await sleep(200);
                    for (let i = 0; i < sequence.length; i++) {
                        toggle(this.targets[expected].element, 'cue');
                    }
                    this.sequence.reset();
                }else{
                    this.running = false;
                    this._reset();

                    // Add to history
                    preds.push(predicted);

                    let hit = predicted == expected;

                    // Get next expected target
                    if (hit) {
                        target++;
                        expected = sequence[target];
                    }

                    // Update the feedback
                    reset_class('#sequence span');
                    for (let i = 0; i < sequence.length; i++) {
                        let element = `#sequence :nth-child(${i + 1})`;
                        if (i == target) {
                            set_class(element, 'active');
                        } else if (i < target) {
                            set_class(element, 'success');
                        }
                    }

                    // Cue
                    let color = 'lock';
                    if (this.options.task.sequence.cue_feedback) {
                        color = hit ? 'success' : 'failure';
                    }
                    toggle(this.targets[predicted].element, color);
                    await sleep(this.options.run.duration_lock_on);
                    toggle(this.targets[predicted].element, color);
                    await sleep(this.options.run.duration_lock_off);

                    // Update score
                    this.score.trial(hit, frames);

                    // Full match
                    if (expected === undefined) break;
                }

            }

        }

        // Hide feedback
        toggle('sequence', 'hidden');

        // Pause for a bit
        await sleep(this.options.run.duration_rest);

        // Send stop event
        this.io.event('task_ends', {score: this.score.stats()});

    }


    /**
     * Run the sequence evaluation task (with backspace)
     */
    async task_sequence_backspace() {

        // Send start event
        this.io.event('task_begins', {task: 'sequence'});

        // Initialize scoring
        this.score = new Score();

        // Show the feedback
        toggle('sequence', 'hidden');

        // Register the backspace target
        const backspace = 10;

        // Cue selected targets and wait for a prediction
        for (let sequence of this.options.task.sequence.sequences) {

            // Initial feedback
            set_content('#sequence :nth-child(1)', this.targets[sequence[0]].label, 'active');
            set_content('#sequence :nth-child(2)', this.targets[sequence[1]].label);
            set_content('#sequence :nth-child(3)', this.targets[sequence[2]].label);
            set_content('#sequence :nth-child(4)', this.targets[sequence[3]].label);

            // Initial state
            let preds = [];
            let expected = sequence[0];
            this.score.block();

            while (true) {

                // Cue
                await sleep(this.options.run.duration_rest);
                if (this.options.task.sequence.cue_target) {
                    toggle(this.targets[expected].element, 'cue');
                    await sleep(this.options.calibration.duration_cue_on);
                    toggle(this.targets[expected].element, 'cue');
                    await sleep(this.options.calibration.duration_cue_off);
                }

                // Wait for a prediction
                this.running = true;
                let event = await flag('predict');
                let predicted = event.detail.target;
                let frames = event.detail.frames;
                this.running = false;
                this._reset();

                // Add to history
                preds.push(predicted);

                // Handle backspace
                if (predicted == backspace) preds.splice(-2, 2);

                // Did we get it right?
                let hit = predicted == expected;

                // Get next expected target
                expected = sequence[0];
                for (let i = 0; i < preds.length; i++) {
                    if (sequence[i] == preds[i]) {
                        expected = sequence[i + 1];
                    } else {
                        expected = backspace;
                        break;
                    }
                }

                // Update the feedback
                reset_class('#sequence span');
                for (let i = 0; i < sequence.length; i++) {
                    let element = `#sequence :nth-child(${i + 1})`;
                    if (sequence[i] == preds[i]) {
                        set_class(element, 'success');
                    } else if (preds[i] != undefined ) {
                        set_class(element, 'failure');
                        set_class(element, 'active');
                        break;
                    } else if (i == preds.length) {
                        set_class(element, 'active');
                        break;
                    }
                }

                // Cue
                let color = 'lock';
                if (this.options.task.sequence.cue_feedback) {
                    color = hit ? 'success' : 'failure';
                }
                toggle(this.targets[predicted].element, color);
                await sleep(this.options.run.duration_lock_on);
                toggle(this.targets[predicted].element, color);
                await sleep(this.options.run.duration_lock_off);

                // Update score
                this.score.trial(hit, frames);

                // Full match
                if (array_equal(sequence, preds)) break;

            }

        }

        // Hide feedback
        toggle('sequence', 'hidden');

        // Pause for a bit
        await sleep(this.options.run.duration_rest);

        // Send stop event
        this.io.event('task_ends', {score: this.score.stats()});

    }


    /**
     * Start the main loop
     */
    async run() {

        // Send start event
        this.io.event('run_begins');

        // Handle keyboard
        let key;
        const handler = (e) => {
            if (e.keyCode === 37 || e.keyCode === 39) {
                key = e.keyCode === 37 ? 'left' : 'right';
                trigger('key');
            }
        };
        document.addEventListener('keydown', handler);

        // Pause for a bit
        await sleep(this.options.run.duration_rest);

        // Run until a prediction is received
        while (true) {
            this.running = true;
            let event = await flag(['predict', 'key']);
            this.running = false;
            this._reset();
            if (event.type === 'key') break;
            let target = event.detail.target;
            toggle(this.targets[target].element, 'lock');
            await sleep(this.options.run.duration_lock_on);
            toggle(this.targets[target].element, 'lock');
            await sleep(this.options.run.duration_lock_off);
        }

        // Stop listening to keyboard events
        document.removeEventListener('keydown', handler);

        // Send stop event
        this.io.event('run_ends');

        // Return
        return key;

    }


    /**
     * Called on each screen refresh
     */
    _tick(scheduled, called, ellapsed, fps) {

        // Run only when required
        if (!this.running) return;

        // Send epoch markers
        let meta = {'index': this.sequence.index};
        if (this.stage == 'calibration') {
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
        if (this.stage == 'calibration') {
            if (this.sequence.cycle == this.options.calibration.repetitions) {
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
        this.running = false;
        this.target = null;
        this.sequence.reset();
    }

    /**
     * Reinit
     */
    _reinit() {
        this.running = false;
        this.stage = 'calibration';
        this.target = null;
        this.targets = this.layouts.calibration.targets;
        this.sequence = this.layouts.calibration.sequence;
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


class Score {

    constructor() {
        this.score = [];
    }

    block() {
        this.score.push({trials: [], frames: []});
        return this;
    }

    trial(hit, frames) {
        let index = this.score.length - 1;
        this.score[index].trials.push(hit ? 1 : 0);
        this.score[index].frames.push(frames);
    }

    stats() {
        let stats = { hit_rate: {blocks: [], average: 0}, classification_time: {blocks: [], average: 0} };
        let all_trials = [];
        let all_frames = [];
        for (const block in this.score) {
            all_trials = all_trials.concat(this.score[block].trials);
            all_frames = all_frames.concat(this.score[block].frames);
            stats.hit_rate.blocks[block] = this._hit_rate(this.score[block].trials);
            stats.classification_time.blocks[block] = this._classification_time(this.score[block].frames);
        }
        stats.hit_rate.average = this._hit_rate(all_trials);
        stats.classification_time.average = this._classification_time(all_frames);
        return stats;
    }

    _hit_rate(arr) {
        return (arr.filter(x => x === 1).length) * 100 / arr.length;
    }

    _classification_time(arr) {
        const screen_rate = 60;
        return (arr.reduce((x, y) => x + y) / arr.length) * 1000 / screen_rate;
    }

}

load_settings().then(async settings => {

    // Initialize
    console.log(settings)
    let burst = new Burst(settings.app);
    // Handle events
    burst.io.subscribe('predictions');
    burst.io.on('predictions', (data, meta) => {
        for (let row of Object.values(data)) {
            switch (row.label) {
                case 'ready':
                    trigger('ready');
                case 'predict':
                    trigger('predict', JSON.parse(row.data));
            }
        }
    });

    // Initialize stages
    const stages = [];

    // Display the fixation cross
    stages[0] = async () => {
        notify(
            '',
            '<div class="marker center"></div>',
            'Press any key to continue'
        )
        await key();
        toggle('overlay');
    };

    // Display the initial message
    stages[1] = async () => {
        notify(
            'Welcome',
            'We will now start the calibration procedure.<br>Please stay still and try not to blink.<br>Look at the target that will be higlighted in blue.<br>For increased accuracy, we recommend that you silently count the short flashes that will appear inside the designated target.',
            'Press any key to continue'
        )
        await key();
        toggle('overlay');
    };

    // Start calibration
    stages[2] = async () => {
        toggle(`layout-${burst.options.layout.calibration}`);
        await burst.calibrate();
        toggle(`layout-${burst.options.layout.calibration}`);
    };

    // Wait for model training
    stages[3] = async () => {
        notify(
            'Training the model',
            '<img src="assets/img/spinner_white.apng" />',
            'Please wait'
        )
        await flag('ready');
        toggle('overlay');
        toggle(`layout-${burst.options.layout.task}`);
    }

    // Start free run
    stages[4] = async () => {
        notify(
            'All set!',
            'Now, let us flex these Jedi muscles.<br>Can you activate the targets?',
            'Press any key to continue'
        )
        await key();
        toggle('overlay');
        return await burst.run();
    };

    // Cued task
    stages[5] = async () => {
        if (burst.options.task.cue.enable) {
            notify(
                'Up for a little challenge?',
                'Try to activate the designated target.',
                'Press any key to continue'
            )
            await key();
            toggle('overlay');
            await burst.task_cue();
            let stats = burst.score.stats();
            notify(
                'Wow!',
                `You achieved a score of ${Math.round(stats.hit_rate.average)}%.<br>Your average activation time was ${Math.round(stats.classification_time.average)}ms per target.`,
                'Press any key to continue'
            )
            await key();
            toggle('overlay');
        }
    };

    // Sequence task
    stages[6] = async () => {
        if (burst.options.task.sequence.enable && (burst.options.layout.task == 'keyboard' || burst.options.layout.task == 'simple')) {
            notify(
                'Ready?',
                //'Now, try to spell the sequence.<br>Use the backspace key if you make an error!',
                'Now, try to copy the sequence!',
                'Press any key to continue'
            )
            await key();
            toggle('overlay');
            await burst.task_sequence();
            let stats = burst.score.stats();
            notify(
                'Congratulations!',
                `You achieved a score of ${Math.round(stats.hit_rate.average)}%.<br>Your average activation time was ${Math.round(stats.classification_time.average)}ms per target.`,
                'Press any key to continue'
            )
            await key();
            toggle('overlay');
        }
    };

    stages[7] = async () => {
        notify(
            'Thank you!',
            'We really appreciate your participation.'
        );
    };

    // Run each stage consecutively
    for (let i = 0; i < stages.length; i++) {
        let r = await stages[i]();
        // TODO: handle return values dynamically - hardcoded for now
        if (i === 4 && r === 'left') {
            toggle(`layout-${burst.options.layout.task}`);
            burst._reinit(); // TODO: refactor
            burst.io.event('reset'); // Send reset event
            i = 0; // Return to calibration stage
        }
    }


});
