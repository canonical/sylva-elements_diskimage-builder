import argparse
import logging
import os

from sylvaprojects.diskimagebuilder import ImageBuilder


def image_builder():
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("DIB_DEBUG_TRACE") else logging.INFO
    )

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--bool", "-b", default=[], action="append", help="Define a boolean flag"
    )
    parser.add_argument("--format", "-t", default="qcow2", help="Format of the image")
    parser.add_argument(
        "--help", "-h", help="Print this help message", action="store_true"
    )
    parser.add_argument("--output", "-o", required=True, help="name of the image")
    parser.add_argument(
        "--set",
        "-s",
        default=[],
        action="append",
        dest="decl",
        help="Define a variable with syntax key=value",
    )
    parser.add_argument(
        "--config", "-c", required=True, help="The configuration to use"
    )

    args = parser.parse_args()
    image_builder = ImageBuilder()
    flags = args.bool
    vars = {}
    for decl in args.decl:
        if "=" in decl:
            [key, val] = decl.split("=", 1)
            vars[key.strip()] = val.strip()
        else:
            raise Exception(f"Incorrect binding syntax {decl}")

    config = args.config

    if config:
        image_builder.parse_config(config)

    image_builder.compile(flags, vars)
    if args.help:
        parser.print_help()
        image_builder.print_help()
        return
    output = args.output or "img"
    if "." not in output:
        output = f"{output}.{args.format}"

    image_builder.run(output, args.format, use_exec=True)
