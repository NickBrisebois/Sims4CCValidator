#!/usr/bin/env python3

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

from files import CCFile, CCType, find_cc_files, write_file_to_output
from log_handler import get_logger
from validators.package_validator import Sims4PackageValidator
from validators.ts4script_validator import TS4ScriptValidator


@dataclass
class CCCheckerArgs:
    directory: Path
    outdir: Path
    skip: list[CCType]
    write_report: Path
    dont_write_skipped: bool
    dry_run: bool


def parse_args() -> CCCheckerArgs:
    parser = ArgumentParser(description="Package Checker")
    parser.add_argument("-d", "--directory", type=Path, help="Directory to check")
    parser.add_argument("-o", "--outdir", type=Path, help="Output directory")
    parser.add_argument(
        "-s",
        "--skip",
        type=str,
        action="append",
        choices=[t.value for t in CCType],
        required=False,
        help="Skip validation for specific file types",
    )
    parser.add_argument(
        "-S",
        "--dont-write-skipped",
        action="store_true",
        dest="dont_write_skipped",
        help="Don't write skipped files to output directory",
    )
    parser.add_argument(
        "-w",
        "--write-report",
        type=Path,
        dest="write_report",
        help="Write a report summary to the provided filepath",
    )
    parser.add_argument(
        "-t",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Don't write any files to output directory",
    )
    args = parser.parse_args()
    return CCCheckerArgs(
        directory=args.directory,
        outdir=args.outdir,
        skip=[CCType[t] for t in args.skip] if args.skip else [],
        write_report=args.write_report,
        dont_write_skipped=args.dont_write_skipped,
        dry_run=args.dry_run,
    )


def write_report(validity_stats: dict[str, list[CCFile]], output_path: Path):
    with open(output_path, "w") as f:
        for category, files in validity_stats.items():
            f.write(f"{category}: {len(files)}\n")
        f.write("\n")
        for category, files in validity_stats.items():
            f.write(
                "\n\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            )
            f.write(f"{category.upper()} FILES:\n")
            f.write(
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            )
            for file in files:
                f.write(f"{file.relative_path}\n")
    f.close()


def main():
    logger = get_logger("Sims4CCValidator")

    args = parse_args()
    if args.skip:
        logger.info(f"Skipping validation for {args.skip}")

    package_validator = Sims4PackageValidator(logger)
    ts4cript_validator = TS4ScriptValidator(logger)

    validity_stats = {
        "corrupted": list[CCFile](),
        "valid": list[CCFile](),
    }
    file_stats: dict[CCType, int] = {t: 0 for t in CCType}

    validator_map = {
        CCType.PACKAGE: package_validator,
        CCType.SCRIPT: ts4cript_validator,
    }

    for cc_file in find_cc_files(args.directory):
        file_stats[cc_file.file_type] += 1
        validator = validator_map.get(cc_file.file_type)
        should_skip = cc_file.file_type in args.skip
        if validator and not should_skip and (error := validator.validate(cc_file)):
            logger.error(f"Validation error for {cc_file.file_name}: {error}")
            validity_stats["corrupted"].append(cc_file)
            continue
        else:
            validity_stats["valid"].append(cc_file)
            logger.info(f"Validated {cc_file.file_name}")
            if args.dry_run or (should_skip and args.dont_write_skipped):
                continue
            write_file_to_output(cc_file, args.outdir)

    if args.write_report:
        write_report(validity_stats, args.write_report)

    logger.info(f"Validated {len(validity_stats['valid'])} cc files")
    logger.info(f"Found {len(validity_stats['corrupted'])} corrupted cc files")
    logger.info(f"Found {file_stats[CCType.SCRIPT]} TS4Script files")
    logger.info(f"Found {file_stats[CCType.PACKAGE]} SimsPackage files")
    logger.info(f"Found {file_stats[CCType.IMAGE]} image files")
    logger.info(f"Found {file_stats[CCType.OTHER]} other files")


if __name__ == "__main__":
    main()
