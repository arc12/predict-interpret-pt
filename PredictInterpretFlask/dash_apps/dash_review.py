# import logging

from pg_shared.dash_utils import create_dash_app_util
from pg_shared.visualisation_builders import shap_force_plot
from pg_shared.text_utilities import ago_text

from predict_interpret import core, menu, Langstrings
from flask import session

from dash import html, dcc, callback_context, no_update
from dash.exceptions import PreventUpdate

from dash.dependencies import Output, Input, State

view_name = "review"

def create_dash(server, url_rule, url_base_pathname):
    """Create a Dash view"""
    app = create_dash_app_util(server, url_rule, url_base_pathname)

    # dash app definitions goes here
    app.config.suppress_callback_exceptions = True
    app.title = "Review Interpretations"

    app.layout = html.Div([
        dcc.Location(id="location"),
        dcc.Store(id="rec_uuids", storage_type="memory"),
        dcc.Store(id="rec_ix", data=0, storage_type="local"),

        html.Div(id="menu"),

        html.Div(
            [
                html.H1(id="heading", className="header-title")
            ]
            # className="header"
            ),


        html.Div(
            dcc.Loading(
                dcc.Graph(id="force_plot", config={'displayModeBar': False}),
                type="circle"
            )
        ),

        
        html.Div(
            [
                html.Button(id="prev_button", className="btn btn-secondary", style={"width": "10%"}),
                html.Div(dcc.Slider(id="slider", min=1, max=10, step=1, value=5, className="mx-2 py-3"), style={"width": "80%"}),
                html.Button(id="next_button", className="btn btn-secondary", style={"width": "10%"})
                # html.Div(html.Button(id="prev_button", className="btn btn-secondary mx-2 mt-0")),
                # html.Div(html.Button(id="next_button", className="btn btn-secondary mt-0"))
                # TODO consider adding a 
            ],
            className="d-flex justify-content-end"
        ),

        html.Div(
            [
                html.H2(id="input_prompt", style={"margin-top": "5px"}),
                html.Div(id="interpretations", style={"height": "280px", "maxHeight": "800px", "overflow": "scroll", "resize": "vertical", "background-color": "#EBEBEB"})
            ]
        ),

    ],
    className="wrapper"
    )

    @app.callback(
            [
                Output("rec_ix", "data")
            ],
            [
                Input("prev_button", "n_clicks"),
                Input("next_button", "n_clicks"),
                Input("slider", "value")
            ],
            [
                # State("location", "pathname"),
                # State("location", "search"),
                State("rec_ix", "data"),
                State("rec_uuids", "data")
            ]
    )
    def change_rec(n_clicks_previous, n_clicks_next, slider, rec_ix, rec_uuids):  #pathname, querystring, 
        triggered_by = callback_context.triggered_id
        if triggered_by is None:
            raise PreventUpdate
        
        if triggered_by == "slider":
            rec_ix = slider - 1  # UI uses 1-based index
        else:
            delta = -1 if callback_context.triggered_id == "prev_button" else 1
            rec_ix = (rec_ix + delta) % len(rec_uuids)

        return [rec_ix]

    @app.callback(
        [
            Output("menu", "children"),
            Output("heading", "children"),
            Output("input_prompt", "children"),
            Output("prev_button", "children"),
            Output("next_button", "children")
        ],
        [
            Input("location", "pathname"),
            Input("location", "search")
        ]
    )
    def update_intialise(pathname, querystring):
        specification_id = pathname.split('/')[-1]
        spec = core.get_specification(specification_id)
        langstrings = Langstrings(spec.lang)
    
        if callback_context.triggered_id == "location":
            # initial load
            menu_children = spec.make_menu(menu, langstrings, core.plaything_root, view_name, query_string=querystring, for_dash=True)
            output = [
                menu_children,
                spec.detail.get("prediction_title", ""),
                spec.detail.get("input_prompt", ""),
                " <- ",
                " -> "
                ]
        else:
            output = [no_update] * 5

        return output

    @app.callback(
        [
            Output("rec_uuids", "data"),
            Output("force_plot", "figure"),
            Output("interpretations", "children"),
            Output("slider", "value"),
            Output("slider", "max")
        ],
        [
            Input("rec_ix", "data"),
            # heading is to get chart to plot on 1st load by forcing chained callbacks. This is not what I wanted!
            # For some reason, including rec_ix in update_initialise Input list meant that the Location context never occurred.
            Input("heading", "children")
        ],
        
        [
            State("location", "pathname"),
            State("location", "search")
        ],
    )
    def update_chart(rec_ix, heading, pathname, querystring):
        specification_id = pathname.split('/')[-1]
        tag = None
        if len(querystring) > 0:
            for param, value in [pv.split('=') for pv in querystring[1:].split("&")]:
                if param == "tag":
                    tag = value
                    break

        spec = core.get_specification(specification_id)
        langstrings = Langstrings(spec.lang)    

        # although putting all examples in one file makes for redundant reading, its only a small file and its more tidy in the config.
        examples = spec.load_asset_json("examples")
        attr_index = examples["attr_index"]
        attr_names = examples["attr_names"]
        examples_uuids = list(examples["data"])
        uuid = examples_uuids[rec_ix % len(examples_uuids)]

        fig = shap_force_plot(attr_index, attr_names, examples["data"][uuid],
                              title=spec.detail.get("prediction_title", "") + f" - {langstrings.get('RECORD')} #{rec_ix + 1}",
                              x_axis_text=langstrings.get("PROB_PC"),
                              y_axis_text=None  # langstrings.get("ATTRIBUTE")
                              )
        
        intrepretations = list()
        if core.record_activity_container is not None:
            tag_clause = "IS_NULL(c.tag)" if tag is None else f"c.tag = '{tag}'"
            # display in returned order, but only the first for each session id
            qry = "SELECT c.user_tag, c.interpretation, c.session_id, c._ts FROM c " \
                  "WHERE c.plaything_name = 'predict-interpret' AND c.action = 'submit' AND "\
                  f"c.specification_id = '{specification_id}' AND c.rec_uuid = '{uuid}' AND {tag_clause} "\
                  "AND NOT IS_NULL(c.interpretation) ORDER BY c._ts DESC"
            session_hits = set()
            iii = core.record_activity_container.query_items(qry, max_item_count=100, enable_cross_partition_query=True)
            for interp in iii:
                sid = interp["session_id"]
                if sid not in session_hits:
                    interp_text = interp["interpretation"].strip()
                    if len(interp_text) > 0:
                        session_hits.add(sid)  # TODO reinstate - removed for ease of testing
                        # ta = dcc.Textarea(id=f"ta_{sid}", value=interp_text, readOnly=True, style={"font-size": "10pt", "margin-top": "12px", "width": "100%", "height": 100})
                        intrepretations.append(
                            html.Div(
                                [
                                    html.Div(
                                        [html.P(t) for t in interp_text.split("\n")], className="card", style={"font-size": "10pt"}
                                    ),
                                    html.Div(
                                        [
                                            html.B(interp["user_tag"], style={"margin-right": "4px"}),
                                            html.Label(ago_text(interp["_ts"], spec.lang))
                                        ], className="d-flex justify-content-end"
                                    )
                                ], className="mt-3", style={"width": "97%", "margin": "auto"}
                            )
                        )
        else:
            pass  # add logging?

        # TODO find a method for capturing the initial referrer. (the referrer in a callback IS the page itself)
        core.record_activity(view_name, specification_id, session,
                             activity={"rec_uuid": uuid, "rec_ix": rec_ix, "n_interpretations": len(intrepretations)},
                             referrer="(callback)",
                             tag=tag)

        return [examples_uuids, fig, langstrings.get("NO_DATA")
                if len(intrepretations) == 0 else intrepretations, rec_ix + 1, len(examples_uuids)]


    return app.server
