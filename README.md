# Predict Interpet
Plaything name: predict-interpret

This uses simulated data with a defined model (Model Driven Synthesiser notebook) to present a series of predictions explained via the Shap methodology and to solicit user input. The notebook is responsible for preparing training data, building a classifier, and emitting a set of example records with their computed Shap values (converted to influences on the probability/score).

## Plaything Specification
Refer to the README in the pg_shared repository/folder for common elements; this README refers only to the elements which are specific to the Precision/Recall/Accuracy Plaything.
The Specifications folder is Config/pra.

Available views:
- "interpret" - users provide responses in reaction to one of a set of explained predictions
- "review" - users can browse through the set of explained predictions, viewing responses made by others (and themself)
- "about"

Responses shown in "review" are filtered according to the tag which is in effect (tag=xxx in the URL), and are shown in recent-first order. Within a given web browser session, only the latest response will be shown.

### "detail"
- prediction_title [simple text]: the objective of the prediction, used as a title.
- instance_name [simple text]: the kind of entity which is the subject. This may ba used as a place-holder in the "about" markdown file (see below).
- input_prompt [simple text]: the prompt which appears over the user response box.
- personas [optional, list]: a list of personas which the respondant can select when making a response. If omitted (or null or an empty list) then personas will not be presented. Otherwise, a drop-down list will be shown. There is no restriction on the values which may be used here. Example: "personas": ["Teacher", "Student"]


Example specification (not using personas):
```
    "detail": {
		"prediction_title": "Chance of success",
		"instance_name": "student",
		"input_prompt": "What questions would you ask to validate this prediction?"
    },
    "menu_items": ["about", "interpret", "review"],
    "asset_map": {
        "examples": "syn_model_1_examples.json",
        "about": "about_en.md"
    }
```

### "asset_map"
Two keys are expected: "examples" is required, and "about" is optional (contingent on the menu_items).

The \*\_examples.json file produced by the notebook should be placed in the assets folder and be identified by the "examples" entry in "asset_map".

The "about" entry identifies a markdown file, as is common practice. In this Plaything, the markdown file for "about" may contain placeholders for any of the elements in __detail__. For example, you could write "Each record is one {instance_name}." This allows the "about" file to be shared between different specifications. It is permitted to add elements to "detail" other than as described above, for use as placeholders.

