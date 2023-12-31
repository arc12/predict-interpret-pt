# import logging

from pg_shared.dash_utils import create_dash_app_util
from pg_shared.visualisation_builders import shap_force_plot
from predict_interpret import core, menu, Langstrings
from flask import session

from dash import html, dcc, callback_context, no_update
from dash.exceptions import PreventUpdate

from dash.dependencies import Output, Input, State

view_name = "interpret"

def create_dash(server, url_rule, url_base_pathname):
    """Create a Dash view"""
    app = create_dash_app_util(server, url_rule, url_base_pathname)

    # dash app definitions goes here
    app.config.suppress_callback_exceptions = True
    app.title = "Interpret Prediction"

    app.layout = html.Div([
        dcc.Location(id="location"),
        dcc.Store(id="rec_uuids", storage_type="memory"),
        dcc.Store(id="rec_ix", data=0, storage_type="local"),

        html.Div(id="menu"),

        html.Div(
            [
                html.H1(id="heading", className="header-title"),
                html.P(id="notes")
            ]
            # className="header"
            ),


        html.Div(
            dcc.Loading(
                dcc.Graph(id="force_plot", config={'displayModeBar': False}),
                type="circle"
            )
            # style={"display": "flex"}
        ),

        html.Div(
            [
                html.H2(id="input_prompt"),
                dcc.Textarea(id="interpretation", style={'width': '100%', 'height': 200})
            ]
        ),

        html.Div(
            [
                html.Div([dcc.Input(id="persona", type="hidden", value=None)], id="persona_div", className="mt-2 mx-2 d-flex justify-content-end"),
                html.Div(
                    [
                        html.Label(id="ut_label", className="mx-1"),
                        dcc.Input(id="ut_value", type="text", size=8)
                    ], className="mt-2"
                )
            ],
            className="d-flex justify-content-end"
        ),
        html.Div(
                    [
                        html.Button(id="skip_button", className="btn btn-secondary mx-2 mt-1"),
                        html.Button(id="submit_button", className="btn btn-secondary mt-1")
                    ],
                    className="d-flex justify-content-end"
                )
    ],
    className="wrapper"
    )

    @app.callback(
            [
                Output("rec_ix", "data"),
                Output("interpretation", "value")
            ],
            [
                Input("submit_button", "n_clicks"),
                Input("skip_button", "n_clicks")
            ],
            [
                State("location", "pathname"),
                State("location", "search"),
                State("rec_ix", "data"),
                State("rec_uuids", "data"),
                State("ut_value", "value"),
                State("interpretation", "value"),
                State("persona", "value")
            ]
    )
    def submit_btn(n_clicks_submit, n_clicks_skip, pathname, querystring, rec_ix, rec_uuids, ut_value, interpretation, persona):
        if n_clicks_submit is None and n_clicks_skip is None:
            raise PreventUpdate

        action = "skip" if callback_context.triggered_id == "skip_button" else "submit"
        
        specification_id = pathname.split('/')[-1]
        tag = None
        if len(querystring) > 0:
            for param, value in [pv.split('=') for pv in querystring[1:].split("&")]:
                if param == "tag":
                    tag = value
                    break
        
        specification_id = pathname.split('/')[-1]
        # spec = core.get_specification(specification_id)
        # langstrings = Langstrings(spec.lang)

        activity = {"action": action, "rec_uuid": rec_uuids[rec_ix % len(rec_uuids)]}
        if action == "submit":
            activity.update({"user_tag": ut_value, "interpretation": interpretation})
            if persona is not None:
                activity["persona"] = persona

        # TODO find a method for capturing the initial referrer. (the referrer in a callback IS the page itself)
        core.record_activity(view_name, specification_id, session,
                             activity=activity,
                             referrer="(callback)",
                             tag=tag)
        
        rec_ix = (rec_ix + 1) % len(rec_uuids)

        return [rec_ix, ""]

    @app.callback(
        [
            Output("menu", "children"),
            Output("heading", "children"),
            Output("notes", "children"),
            Output("input_prompt", "children"),
            Output("persona_div", "children"),
            Output("skip_button", "children"),
            Output("ut_label", "children"),
            Output("submit_button", "children"),
            # Output("rec_uuids", "data")
        ],
        [
            Input("location", "pathname"),
            Input("location", "search")
        ]
        # [
        #     State("rec_ix", "data")
        # ]
    )
    def update_intialise(pathname, querystring):
        specification_id = pathname.split('/')[-1]
        spec = core.get_specification(specification_id)
        langstrings = Langstrings(spec.lang)
        personas = spec.detail.get("personas", [])
        personas = [] if personas is None else personas
    
        if callback_context.triggered_id == "location":
            # initial load
            menu_children = spec.make_menu(menu, langstrings, core.plaything_root, view_name, query_string=querystring, for_dash=True)
            if len(personas) == 0:
                persona_div = no_update  # leave default hidden field with value None for the callback handler
            else:
                persona_div = [
                    html.Label(langstrings.get("PERSONA"), className="mx-1 mt-1"),
                    dcc.Dropdown(personas, id="persona", value=personas[0], clearable=False, searchable=False, style={"width": "150px"})
                ]
            output = [
                menu_children,
                spec.detail.get("prediction_title", ""),
                spec.detail.get("notes", None),
                spec.detail.get("input_prompt", ""),
                persona_div,
                langstrings.get("SKIP"),
                langstrings.get("USER_TAG"),
                langstrings.get("SUBMIT")
                ]
        else:
            output = [no_update] * 8

        # examples = spec.load_asset_json("examples")
        # examples_uuids = list(examples["data"])
        # output.append(examples_uuids)

        return output

    @app.callback(
        [
            Output("rec_uuids", "data"),
            Output("force_plot", "figure") 
        ],
        [
            Input("rec_ix", "data"),
            # heading is to get chart to plot on 1st load by forcing chained callbacks. This is not what I wanted!
            # For some reason, including rec_ix in update_initialise Input list meant that the Location context never occurred.
            Input("heading", "children")
        ],
        
        [
            State("location", "pathname")
        ],
    )
    def update_chart(rec_ix, heading, pathname):
        specification_id = pathname.split('/')[-1]
        spec = core.get_specification(specification_id)
        langstrings = Langstrings(spec.lang)    

        # although putting all examples in one file makes for redundant reading, its only a small file and its more tidy in the config.
        examples = spec.load_asset_json("examples")
        attr_index = examples["attr_index"]
        attr_names = examples["attr_names"]
        examples_uuids = list(examples["data"])

        fig = shap_force_plot(attr_index, attr_names, examples["data"][examples_uuids[rec_ix % len(examples_uuids)]],
                              title=spec.detail.get("prediction_title", "") + f" - {langstrings.get('RECORD')} #{rec_ix + 1}",
                              x_axis_text=langstrings.get("PROB_PC"),
                              y_axis_text=None,  # langstrings.get("ATTRIBUTE")
                              height=50 * (1 + len(attr_index))
                              )

        return [examples_uuids, fig]
        # return [fig]


    return app.server
