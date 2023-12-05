# Predict Interpet
Plaything name: predict-interpret

Uses simulated data with a defined model (Model Driven Synthesiser notebook) to present a series of predictions explained via the Shap methodology and to solicit user input. The notebook is responsible for preparing training data, building a classifier, and emitting a set of example records with their computed Shap values (converted to influences on the probability/score).

The \*\_examples.json file produced by the notebook should be used in the assets folder.

The markdown file for "about" may contain placeholders for any of the elements in __detail__. For example, you could write "Each record is one {instance_name}."

Example specification:
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