from . import io
from .csm import CostAndScalingModel

from pathlib import Path
from collections.abc import Generator


def run(
    config: str | dict = io.read_config(),
) -> Generator[tuple] | Generator[Path]:
    """Run the cost and scaling model(s) for the input configuration
    Configuration can be entered as a string (path to a config file to read) or a dict
    If not provided, will read the config at the default config file location

    Args:
        config (str | dict, optional): input configuration. Defaults to io.read_config().

    Yields:
        Generator[tuple] | Generator[Path]: model results or paths to saved output files
    """
    
    # If the input is provided in the form of a path to a configuration file, read it
    # Otherwise, the config input is assumed to be a dict of config options
    if isinstance(config, str):
        config = io.read_config(config)

    model_input = io.read_model_input(config)
    model_result = generate_model_result(model_input)
    model_output = create_model_output(model_result, config)

    yield from model_output


def generate_model_result(
    model_input: Generator[tuple],
) -> Generator[tuple]:
    
    for module, data in model_input:
        model = CostAndScalingModel(module)
        result = model.calculate_output_parameters(data)
        yield model.name, result


def create_model_output(
    model_result: Generator[tuple],
    config: dict,
    ) -> Generator[tuple] | Generator[Path]:
    """Create the model output in the specified output format, or return the model results directly if not output specified

    Args:
        model_result (Generator[tuple]): resutls from model
        config (dict): configuration dict

    Yields:
        Generator[tuple] | Generator[Path]: either the model results returned directly or the paths to the output files
    """    

    # Lookup to get which function should be used to create the output file
    func_create_output_lookup = {
        "landbosse": io.generate_output_landbosse,
        "sqlite": io.generate_output_sqlite,
    }

    if (output_file_type := config.get("output_type", None)) is None:
        # if there is no output file type, simply return the results from the model(s)
        for r in model_result:
            yield r

    else:

        config["output_directory"] = Path(config.get("output_directory", "./output"))
        
        if output_file_type not in func_create_output_lookup.keys():
            raise KeyError(
                f"Invalid output file type: '{output_file_type:s}'. Allowable values are {", ".join(func_create_output_lookup.keys())} or None",
            )
        func_create_output = func_create_output_lookup[output_file_type]
        
        # Call the appropriate function on the model results
        for r in model_result:
            yield from func_create_output(*r, config)


if __name__ == "__main__":
    pass
