// For help, see: https://formio.github.io/formio.js/app/builder.html

const schema = {
    "components": [
        {
            "legend": "Stim",
            "key": "stim",
            "type": "fieldset",
            "components": [
                {
                    "label": "Type",
                    "labelPosition": "left-left",
                    "widget": "html5",
                    "placeholder": " ",
                    "defaultValue": "ricker",
                    "data": {
                        "values": [
                            {
                                "label": "Gabor",
                                "value": "gabor"
                            },
                            {
                                "label": "Ricker",
                                "value": "ricker"
                            },
                            {
                                "label": "Plain",
                                "value": "plain"
                            }
                        ]
                    },
                    "validate": {
                        "required": true
                    },
                    "key": "stim.type",
                    "type": "select",
                    "input": true
                },
                {
                    "label": "Depth",
                    "labelPosition": "left-left",
                    "defaultValue": 0.8,
                    "validate": {
                        "required": true,
                        "min": 0.01,
                        "max": 1
                    },
                    "clearOnHide": false,
                    "key": "stim.depth",
                    "type": "number"
                }
            ]
        },
        {
            "legend": "Decision",
            "key": "decision",
            "type": "fieldset",
            "components": [
                {
                    "label": "Minimum buffer size",
                    "labelPosition": "left-left",
                    "defaultValue": 20,
                    "validate": {
                        "required": true,
                        "min": 1,
                        "max": 1e9
                    },
                    "clearOnHide": false,
                    "key": "decision.common.min_buffer_size",
                    "type": "number"
                },
                {
                    "label": "Maximum buffer size",
                    "labelPosition": "left-left",
                    "defaultValue": 80,
                    "validate": {
                        "required": true,
                        "min": 1,
                        "max": 1e9
                    },
                    "clearOnHide": false,
                    "key": "decision.common.max_buffer_size",
                    "type": "number"
                },
                {
                    "label": "Scoring method",
                    "labelPosition": "left-left",
                    "widget": "html5",
                    "placeholder": " ",
                    "defaultValue": "nodes.predict.Steady",
                    "data": {
                        "values": [
                            {
                                "label": "Pearson",
                                "value": "nodes.predict.Pearson"
                            },
                            {
                                "label": "Steady",
                                "value": "nodes.predict.Steady"
                            },
                            {
                                "label": "Random",
                                "value": "Random"
                            }
                        ]
                    },
                    "validate": {
                        "required": true
                    },
                    "key": "decision.method",
                    "type": "select",
                    "input": true
                },
                {
                    "label": "Pearson",
                    "conditional": {
                        "show": true,
                        "when": "decision.method",
                        "eq": "nodes.predict.Pearson"
                    },
                    "type": "well",
                    "input": false,
                    "components": [
                        {
                            "label": "Threshold",
                            "labelPosition": "left-left",
                            "defaultValue": 0.2,
                            "validate": {
                                "required": true,
                                "min": 0.0001,
                                "max": 1
                            },
                            "clearOnHide": false,
                            "key": "decision.pearson.threshold",
                            "type": "number"
                        },
                        {
                            "label": "Delta",
                            "labelPosition": "left-left",
                            "defaultValue": 0.5,
                            "validate": {
                                "required": true,
                                "min": 0,
                                "max": 10
                            },
                            "clearOnHide": false,
                            "key": "decision.pearson.delta",
                            "type": "number",
                        },
                    ]
                },
                {
                    "label": "Steady",
                    "conditional": {
                        "show": true,
                        "when": "decision.method",
                        "eq": "nodes.predict.Steady"
                    },
                    "type": "well",
                    "input": false,
                    "components": [
                        {
                            "label": "Minimum prediction score",
                            "labelPosition": "left-left",
                            "defaultValue": 50,
                            "validate": {
                                "required": true,
                                "min": 1,
                                "max": 1e9
                            },
                            "clearOnHide": false,
                            "key": "decision.steady.min_frames_pred",
                            "type": "number"
                        },
                        {
                            "label": "Maximum predictions",
                            "labelPosition": "left-left",
                            "defaultValue": 200,
                            "validate": {
                                "required": true,
                                "min": 1,
                                "max": 1e9
                            },
                            "clearOnHide": false,
                            "key": "decision.steady.max_frames_pred",
                            "type": "number",
                        },
                    ]
                },
                {
                    "label": "Random",
                    "conditional": {
                        "show": true,
                        "when": "decision.method",
                        "eq": "Random"
                    },
                    "type": "well",
                    "components": [
                        {
                            "label": "Number of targets",
                            "labelPosition": "left-left",
                            "defaultValue": 5,
                            "validate": {
                                "required": true,
                                "min": 1,
                                "max": 5
                            },
                            "clearOnHide": false,
                            "key": "decision.random.n_targets",
                            "type": "number",
                        }
                    ]
                },
            ]
        },
        {
            "type": "button",
            "label": "Update",
            "key": "update",
            "disableOnInvalid": true,
            "input": true,
            "action": "event",
            "event": "update"
        }
    ]
}