// For help, see: https://formio.github.io/formio.js/app/builder.html

const schema = {
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
            "key": "common.min_buffer_size",
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
            "key": "common.max_buffer_size",
            "type": "number"
        },
        {
            "label": "Scoring method",
            "labelPosition": "left-left",
            "widget": "html5",
            "placeholder": " ",
            "defaultValue": "AccumulateSteady",
            "data": {
                "values": [
                    {
                        "label": "Pearson",
                        "value": "AccumulatePearson"
                    },
                    {
                        "label": "Steady",
                        "value": "AccumulateSteady"
                    },
                    {
                        "label": "Random",
                        "value": "AccumulateRandom"
                    }
                ]
            },
            "validate": {
                "required": true
            },
            "key": "method",
            "type": "select",
            "input": true
        },
        {
            "label": "Pearson",
            "conditional": {
                "show": true,
                "when": "method",
                "eq": "AccumulatePearson"
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
                    "key": "pearson.threshold",
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
                    "key": "pearson.delta",
                    "type": "number",
                },
            ]
        },
        {
            "label": "Steady",
            "conditional": {
                "show": true,
                "when": "method",
                "eq": "AccumulateSteady"
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
                    "key": "steady.min_frames_pred",
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
                    "key": "steady.max_frames_pred",
                    "type": "number",
                },
            ]
        },
        {
            "label": "Random",
            "conditional": {
                "show": true,
                "when": "method",
                "eq": "AccumulateRandom"
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
                    "key": "random.n_targets",
                    "type": "number",
                }
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