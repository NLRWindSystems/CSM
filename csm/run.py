from . import util
from . import io
from .csm import CostAndScalingModel

from pathlib import Path
from collections.abc import Generator


def run() -> Generator[tuple] | Generator[Path]:
    model_input = io.read_model_input()
    model_result = generate_model_result(model_input)
    model_output = create_model_output(model_result)
    yield from model_output


def generate_model_result(
    model_input: Generator,
    ) -> Generator[tuple]:
    for name, data in model_input:
        model = CostAndScalingModel(name)
        result = model.calculate_output_parameters(data)
        yield name, result


def create_model_output(
    model_result: Generator[tuple],
    ) -> Generator[tuple] | Generator[Path]:

    # The type of output file to write
    output_file_type = util.conf.get("output_type")

    # Lookup to get which function should be used to create the output file
    func_create_output_lookup = {
        "landbosse": io.generate_output_landbosse,
        "sqlite": io.generate_output_sqlite,
    }

    if output_file_type is None:
        # if there is no output file type, simply return the results from the model(s)
        for r in model_result:
            yield r

    else:

        output_directory = util.conf.get("output_directory")

        # if there is an output file type, check to make sure it has a corresponding function and there is an output directory specified
        if output_directory is None:
            raise Exception(
                f"Output filetype {output_file_type:s} specified but not output file location provided."
            )
        
        output_directory = Path(output_directory)
        
        if output_file_type not in func_create_output_lookup.keys():
            raise Exception(
                f"Invalid output file type: '{output_file_type:s}'. Allowable values are {", ".join(func_create_output_lookup.keys())} or None",
                )
        func_create_output = func_create_output_lookup[output_file_type]
        
        # Call the appropriate function on the model results
        for r in model_result:
            yield from func_create_output(output_directory, *r)


if __name__ == "__main__":
    pass
