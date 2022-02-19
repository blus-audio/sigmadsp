import argparse
import logging
import rpyc


def main():
    logging.basicConfig(level=logging.INFO)

    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "-av",
        "--adjust_volume",
        required=False,
        type=float,
        help="Adjust the volume by a certain value in dB (positive or negative).",
    )
    argument_parser.add_argument(
        "-r", "--reset", required=False, help="Soft-reset the DSP.", action="store_true"
    )
    argument_parser.add_argument(
        "-lp", "--load_parameters", required=False, help="Load new parameter file"
    )
    arguments = argument_parser.parse_args()

    try:
        sigmadsp_backend_service = rpyc.connect("localhost", 18861)

    except ConnectionRefusedError:
        logging.info("Sigmadsp backend is not running! Aborting.")

    else:
        if arguments.adjust_volume is not None:
            sigmadsp_backend_service.root.adjust_volume(
                arguments.adjust_volume, "adjustable_volume_main"
            )

        if arguments.load_parameters is not None:
            with open(arguments.load_parameters, "r") as parameter_file:
                parameters = parameter_file.readlines()

            sigmadsp_backend_service.root.load_parameter_file(parameters)

        if arguments.reset is True:
            sigmadsp_backend_service.root.reset_dsp()


if __name__ == "__main__":
    main()
