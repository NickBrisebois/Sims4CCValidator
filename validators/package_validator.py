from enum import Enum
from logging import Logger

import validators.magic_numbers.packages as magic
from files import CCFile, CCType
from handlers.package_handler import DBPFEntry, DBPFHeader, Sims4PackageHandler
from validators.base_validator import BaseValidator


class ValidationError(Enum):
    # General file errors
    FILE_TOO_SMALL = "FILE_TOO_SMALL"

    # File header issues
    INVALID_FILE_IDENTIFIER = "MISSING_FILE_IDENTIFIER"
    INVALID_FORMAT_VERSION = "INVALID_FORMAT_VERSION"
    INVALID_UNKNOWN_CONSTANT = "INVALID_UNKNOWN_CONSTANT"
    INVALID_HOLE_OFFSET = "INVALID_HOLE_OFFSET"

    # Index issues
    INDEX_OUT_OF_BOUNDS = "INDEX_OUT_OF_BOUNDS"
    EMPTY_INDEX_INFO = "EMPTY_INDEX_INFO"
    INVALID_INDEX = "INVALID_INDEX"
    INDEX_PARSE_ERROR = "INDEX_PARSE_ERROR"

    # idk how these would even happen but ¯\_(ツ)_/¯
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_NOT_FILE = "FILE_NOT_FILE"

    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class PackageException(Exception):
    detail: str
    error: ValidationError

    def __init__(self, detail: str, error: ValidationError):
        self.detail = detail
        self.error = error


class Sims4PackageValidator(BaseValidator):
    _logger: Logger

    def __init__(self, logger: Logger):
        self._logger = logger

    def validate_file_meta(self, package_file: CCFile) -> None:
        """
        Just make sure we're working on a real file
        """
        error_code = None
        error_msg = None

        if package_file.file_type != CCType.PACKAGE:
            error_msg = (
                f"Incorrect file passed to SimsPackageValidator: {package_file.file_path}. "
                + "This is a programming error and not an issue with the file itself"
            )
            self._logger.error(error_msg)
            raise ValueError(error_msg)

        if not package_file.file_path.exists():
            error_msg = f"File does not exist: {package_file.file_path}"
            error_code = ValidationError.FILE_NOT_FOUND
            self._logger.error(error_msg)

        if not package_file.file_path.is_file():
            error_msg = f"Path is not a file: {package_file.file_path}"
            error_code = ValidationError.FILE_NOT_FILE
            self._logger.error(error_msg)

        if package_file.file_path.stat().st_size < magic.MIN_FILE_SIZE:
            error_msg = f"File is too small: {package_file.file_path}"
            error_code = ValidationError.FILE_TOO_SMALL
            self._logger.error(error_msg)

        if error_code and error_msg:
            raise PackageException(
                detail=error_msg,
                error=error_code,
            )

    def validate_header(self, header: DBPFHeader) -> ValidationError | None:
        error_msg = None
        error_code = None

        if header.file_signature != magic.FILE_IDENTIFIER:
            error_msg = "File is not a valid DBPF file"
            error_code = ValidationError.INVALID_FILE_IDENTIFIER

        if (
            header.major_format_version != magic.EXPECTED_MAJOR_FORMAT_VERSION
            or header.minor_format_version != magic.EXPECTED_MINOR_FORMAT_VERSION
        ):
            error_msg = "Invalid major/minor format version values"
            error_code = ValidationError.INVALID_FORMAT_VERSION

        if header.unknown_constant_one != magic.EXPECTED_UNKNOWN_CONSTANT_ONE:
            error_msg = "Invalid unknown constant value(s)"
            error_code = ValidationError.INVALID_UNKNOWN_CONSTANT

        if header.hole_offset != magic.EXPECTED_HOLE_OFFSET:
            error_msg = "Invalid hole offset value"
            error_code = ValidationError.INVALID_HOLE_OFFSET

        if error_code and error_msg:
            raise PackageException(
                detail=error_msg,
                error=error_code,
            )

    def validate_index_entry(
        self,
        index_entry: DBPFEntry,
        package_file: CCFile,
        header: DBPFHeader,
        file_size_bytes: int,
    ):
        error_msg = None
        error_code = None

        if header.index_size == 0:
            error_msg = f"Index info is empty: {package_file.file_path}"
            error_code = ValidationError.EMPTY_INDEX_INFO

        if (
            header.index_offset_short > file_size_bytes
            or header.index_offset_short + header.index_size > file_size_bytes
        ):
            error_msg = f"Index info is out of bounds: {package_file.file_path}"
            error_code = ValidationError.INDEX_OUT_OF_BOUNDS

        try:
            # raw_package_data.seek(header.index_offset_short)
            # index_data = raw_package_data.read(header.index_size)

            # if len(index_data) != header.index_size:
            #     error_msg = f"Couldn't read complete index (expected {header.index_size} bytes, got {len(index_data)} bytes)"
            #     error_code = ValidationError.INVALID_INDEX
            pass
        except Exception:
            error_msg = f"Failed to parse index info: {package_file.file_path}"
            error_code = ValidationError.INDEX_PARSE_ERROR

        if error_msg and error_code:
            raise PackageException(
                detail=error_msg,
                error=error_code,
            )

    def validate(self, package_file: CCFile):
        try:
            self._logger.info(
                "======================"
                + f"Validating package: {package_file.file_path}"
                + "======================"
            )

            self._logger.info(
                f"[{package_file.file_name}] Validating package file metadata..."
            )
            self.validate_file_meta(package_file)

            with Sims4PackageHandler(package_file) as handler:
                header = handler.get_header()

                self._logger.info(
                    f"[{package_file.file_name}] Validating package header..."
                )
                if error := self.validate_header(header):
                    return error

                self._logger.info(
                    f"[{package_file.file_name}] Validating package index info..."
                )
                for index_entry in handler.get_entries():
                    if error := self.validate_index_entry(
                        index_entry=index_entry,
                        package_file=package_file,
                        header=header,
                        file_size_bytes=package_file.file_size_bytes,
                    ):
                        return error

                    return error

            self._logger.info(f"Package file is good! 😎: {package_file.file_path}")

        except PackageException as e:
            self._logger.error(f"Error validating package: {e.detail}")
            return e.error
        except ValueError:
            raise
        except Exception as e:
            self._logger.error(f"Unknown error while validating package: {e}")
            return ValidationError.UNKNOWN_ERROR
