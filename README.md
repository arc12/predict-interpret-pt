# Predict Interpet
Plaything name: predict-interpret

Uses simulated data with a defined model (Model Driven Synthesiser notebook) to present a series of predictions explained via the Shap methodology and to solicit user input. The notebook is responsible for preparing training data, building a classifier, and emitting a set of example records with their computed Shap values (converted to influences on the probability/score).

The \*\_examples.json file produced by the notebook should be used in the assets folder.