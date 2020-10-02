"""
High-level run function
"""
import logging

import scmdata
from tqdm.autonotebook import tqdm

from .adapters import FAIR, MAGICC7

LOGGER = logging.getLogger(__name__)


def run(
    climate_models_cfgs,
    scenarios,
    output_variables=("Surface Temperature",),
    out_config=None,
):  # pylint: disable=W9006
    """
    Run a number of climate models over a number of scenarios

    Parameters
    ----------
    climate_models_cfgs : dict[str: list]
        Dictionary where each key is a model and each value is the configs
        with which to run the model. The configs are passed to the model
        adapter.

    scenarios : :obj:`pyam.IamDataFrame`
        Scenarios to run

    output_variables : list[str]
        Variables to include in the output

    out_config : dict[str: tuple of str]
        Dictionary where each key is a model and each value is a list of
        configuration values to include in the output's metadata.

    Returns
    -------
    :obj:`scmdata.ScmDataFrame`
        Model output

    Raises
    ------
    KeyError
        ``out_config`` has keys which are not in ``climate_models_cfgs``

    TypeError
        A value in ``out_config`` is not a :obj:`tuple`
    """
    if out_config is not None:
        unknown_models = set(out_config.keys()) - set(climate_models_cfgs.keys())
        if unknown_models:
            raise KeyError(
                "Found model(s) in `out_config` which are not in "
                "`climate_models_cfgs`: {}".format(unknown_models)
            )

        for k, v in out_config.items():
            if not isinstance(v, tuple):
                raise TypeError(
                    "`out_config` values must be tuples, this isn't the case for "
                    "climate_model: '{}'".format(k)
                )

    res = []
    for climate_model, cfgs in tqdm(climate_models_cfgs.items(), desc="Climate models"):
        if climate_model == "MAGICC7":
            runner = MAGICC7()
        elif climate_model.upper() == "FAIR":  # allow various capitalisations
            runner = FAIR()
        else:
            raise NotImplementedError(
                "No adapter available for {}".format(climate_model)
            )

        if out_config is not None and climate_model in out_config:
            output_config_cm = out_config[climate_model]
        else:
            output_config_cm = None

        model_res = runner.run(scenarios, cfgs, output_variables=output_variables, output_config=output_config_cm)
        res.append(model_res)

    for i, model_res in enumerate(res):
        if i < 1:
            key_meta = set(model_res.meta.columns.tolist())

        model_meta = set(model_res.meta.columns.tolist())
        climate_model = model_res.get_unique_meta("climate_model")
        if model_meta != key_meta:  # noqa
            raise AssertionError(
                "{} meta: {}, expected meta: {}".format(
                    climate_model, model_meta, key_meta
                )
            )

    if len(res) == 1:
        LOGGER.info("Only one model run, returning its results")
        scmdf = res[0]
    else:
        LOGGER.info("Appending model results")
        scmdf = scmdata.run_append(res)

    return scmdf
