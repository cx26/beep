import re
import os
import json

from monty.serialization import loadfn, dumpfn

from beep import logger
from beep.conversion_schemas import FastCharge_CONFIG, xTesladiag_CONFIG, ARBIN_CONFIG, MACCOR_CONFIG, INDIGO_CONFIG, BIOLOGIC_CONFIG, NEWARE_CONFIG
from beep.structure.arbin import ArbinDatapath
from beep.structure.maccor import MaccorDatapath
from beep.structure.neware import NewareDatapath
from beep.structure.indigo import IndigoDatapath
from beep.structure.biologic import BiologicDatapath
from beep.utils import WorkflowOutputs
from beep.collate import add_suffix_to_filename


def process_file_list_from_json(file_list_json, processed_dir="data-share/structure/"):
    """
    Function to take a json filename corresponding to a data structure
    with a 'file_list' and a 'validity' attribute, process each file
    with a corresponding True validity, dump the processed file into
    a predetermined directory, and return a jsonable dict of processed
    cycler run file locations

    Args:
        file_list_json (str): json string or json filename corresponding
            to a dictionary with a file_list and validity attribute,
            if this string ends with ".json", a json file is assumed
            and loaded, otherwise interpreted as a json string.
        processed_dir (str): location for processed cycler run output
            files to be placed.

    Returns:
        str: json string of processed files (with key "processed_file_list").
            Note that this list contains None values for every file that
            had a corresponding False in the validity list.

    """
    # Get file list and validity from json, if ends with .json,
    # assume it's a file, if not assume it's a json string
    if file_list_json.endswith(".json"):
        file_list_data = loadfn(file_list_json)
    else:
        file_list_data = json.loads(file_list_json)

    # Setup workflow
    outputs = WorkflowOutputs()

    # Prepend optional root to output directory
    processed_dir = os.path.join(
        os.environ.get("BEEP_PROCESSING_DIR", "/"), processed_dir
    )

    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)

    file_list = file_list_data["file_list"]
    validities = file_list_data["validity"]
    run_ids = file_list_data["run_list"]
    processed_file_list = []
    processed_run_list = []
    processed_result_list = []
    processed_message_list = []
    invalid_file_list = []
    for filename, validity, run_id in zip(file_list, validities, run_ids):
        logger.info("run_id=%s structuring=%s", str(run_id), filename, extra=s)
        if validity == "valid":
            # Process datapath and dump to file

            dp = auto_load(filename)
            dp.structure()

            # raw_cycler_run = RawCyclerRun.from_file(filename)
            # processed_cycler_run = raw_cycler_run.to_processed_cycler_run()
            new_filename, ext = os.path.splitext(os.path.basename(filename))
            new_filename = new_filename + ".json"
            new_filename = add_suffix_to_filename(new_filename, "_structure")
            structured_run_loc = os.path.join(processed_dir, new_filename)
            structured_run_loc = os.path.abspath(structured_run_loc)
            dumpfn(dp, structured_run_loc)

            # Append file loc to list to be returned
            processed_file_list.append(structured_run_loc)
            processed_run_list.append(run_id)
            processed_result_list.append("success")
            processed_message_list.append({"comment": "", "error": ""})

        else:
            invalid_file_list.append(filename)

    output_json = {
        "file_list": processed_file_list,
        "run_list": processed_run_list,
        "result_list": processed_result_list,
        "message_list": processed_message_list,
        "invalid_file_list": invalid_file_list,
    }

    # Workflow outputs
    file_list_size = len(output_json["file_list"])
    if file_list_size > 1 or file_list_size == 0:
        logger.warning("{file_list_size} files being validated, should be 1")

    output_data = {
        "filename": output_json["file_list"][0],
        "run_id": output_json["run_list"][0],
        "result": output_json["result_list"][0],
    }

    outputs.put_workflow_outputs(output_data, "structuring")

    # Return jsonable file list
    return json.dumps(output_json)


def auto_load(filename):
    """
    Factory method to invoke RawCyclerRun from filename with recognition of
    type from filename, using corresponding class method as constructor.

    Args:
        filename (str): string corresponding to file filename.
        validate (bool): whether or not to validate file.

    Returns:
        beep.structure.RawCyclerRun: RawCyclerRun corresponding to parsed file(s).

    """
    if re.match(ARBIN_CONFIG["file_pattern"], filename) or re.match(FastCharge_CONFIG["file_pattern"], filename):
        return ArbinDatapath.from_file(filename)
    elif re.match(MACCOR_CONFIG["file_pattern"], filename) or re.match(xTesladiag_CONFIG["file_pattern"], filename):
        return MaccorDatapath.from_file(filename)
    elif re.match(INDIGO_CONFIG["file_pattern"], filename):
        return IndigoDatapath.from_file(filename)
    elif re.match(BIOLOGIC_CONFIG["file_pattern"], filename):
        return BiologicDatapath.from_file(filename)
    elif re.match(NEWARE_CONFIG["file_pattern"], filename):
        return NewareDatapath.from_file(filename)
    else:
        raise ValueError("{} does not match any known file pattern".format(filename))
