# Handle reading DBPF files
# References:
# https://thuverx.github.io/mysims-research/Files/DBPF.html
# https://modthesims.info/wiki.php?title=DBPF
# https://github.com/ytaa/dbpf_reader

import struct
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO

import validators.magic_numbers.packages as magic
from files import CCFile


@dataclass
class DBPFHeader:
    file_signature: bytes
    major_format_version: int
    minor_format_version: int
    major_file_version: int  # unused
    minor_file_version: int  # unused
    unknown_constant_one: int  # unused but should be int 0
    creation_time: int  # unused
    update_time: int  # unused
    index_major_version: int  # unused
    index_count: int
    index_offset_short: int
    index_size: int
    hole_entry_count: int  # unused
    hole_offset: int  # unused but should be int 3
    index_offset_long: int
    padding: bytes


@dataclass
class DBPFIndexHeader:
    raw_flags: int
    constant_type: int
    constant_group: int
    constant_instance: int


class DBPFCompressionType(Enum):
    NONE = 0x0000
    ZLIB = 0x5A42
    DELETED = 0xFFE0
    STREAMABLE = 0xFFFE
    INTERNAL = 0xFFFF


@dataclass
class DBPFEntry:
    resource_key_type: int | None
    resource_key_group: int | None
    resource_key_instance_upper_32_bits: int | None
    resource_key_instance_lower_32_bits: int
    resource_offset: int
    compressed_size: int  # compressed size (obv)
    uncompressed_size: int  # uncompressed size
    extended_entry: bool  # this is technically part of the uncompressed_size field, pulled via the last bit
    compression_type: DBPFCompressionType | None
    comitted: bool | None


@dataclass
class PackageHandlerException(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class Sims4PackageHandler:
    _package_file: CCFile
    _file: BinaryIO
    _header: bytes

    def __init__(self, package_file: CCFile) -> None:
        self._package_file = package_file

    def __enter__(self) -> "Sims4PackageHandler":
        self._file = self._package_file.file_path.open("rb")
        self._header = self._file.read(magic.HEADER_SIZE)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._file.close()

    def get_header(self) -> DBPFHeader:
        """
        Get the binary header data of the package file and parse it into a DBPFHeader object
        """
        # Unpack header data
        unpacked = struct.unpack(magic.HEADER_STRUCT_FORMAT, self._header)
        (
            file_signature,
            major_format_version,
            minor_format_version,
            major_file_version,
            minor_file_version,
            unknown_one,
            creation_time,
            update_time,
            index_major_version,
            index_count,
            index_offset_short,
            index_size,
            unknown_three,
            hole_offset,
            index_offset_long,
            padding,
        ) = unpacked
        return DBPFHeader(
            file_signature=file_signature,
            major_format_version=major_format_version,
            minor_format_version=minor_format_version,
            major_file_version=major_file_version,
            minor_file_version=minor_file_version,
            unknown_constant_one=unknown_one,
            creation_time=creation_time,
            update_time=update_time,
            index_major_version=index_major_version,
            index_count=index_count,
            index_offset_short=index_offset_short,
            index_size=index_size,
            hole_entry_count=unknown_three,
            hole_offset=hole_offset,
            index_offset_long=index_offset_long,
            padding=padding,
        )

    def parse_index_flags(self, header: DBPFHeader) -> DBPFIndexHeader:
        self._file.seek(header.index_offset_long)

        raw_flags = struct.unpack("<I", self._file.read(magic.INDEX_HEADER_SIZE))[0]
        return DBPFIndexHeader(
            raw_flags=raw_flags,
            constant_type=raw_flags & 0x1,
            constant_group=raw_flags & 0x2,
            constant_instance=raw_flags & 0x4,
        )

    def get_entries(self) -> list[DBPFEntry]:
        parsed_header = self.get_header()

        # each flag being enabled adds another possibly property to the package entry
        parsed_flags = self.parse_index_flags(parsed_header)

        try:
            entries = []
            self._file.seek(parsed_header.index_offset_long)

            index_pos = magic.HEADER_SIZE
            for entry in range(parsed_header.index_count):
                self._file.seek(index_pos)

                resource_key_type = None
                resource_key_group = None
                resource_key_instance_upper_32_bits = None
                if parsed_flags.constant_type:
                    resource_key_type = struct.unpack("<I", self._file.read(4))[0]
                if parsed_flags.constant_group:
                    resource_key_group = struct.unpack("<I", self._file.read(4))[0]
                if parsed_flags.constant_instance:
                    resource_key_instance_upper_32_bits = struct.unpack(
                        "<I", self._file.read(4)
                    )[0]

                entry = self._file.read(magic.STATIC_ENTRY_SIZE)
                (
                    resource_key_instance_lower_32_bits,
                    resource_offset,
                    compressed_size_and_extended_entry,
                    uncompressed_size,
                ) = struct.unpack(
                    magic.STATIC_ENTRY_STRUCT_FORMAT,
                    entry,
                )
                entry = DBPFEntry(
                    resource_key_type=resource_key_type,
                    resource_key_group=resource_key_group,
                    resource_key_instance_upper_32_bits=resource_key_instance_upper_32_bits,
                    resource_key_instance_lower_32_bits=resource_key_instance_lower_32_bits,
                    resource_offset=resource_offset,
                    compressed_size=compressed_size_and_extended_entry & 0x7FFFFFFF,
                    extended_entry=bool((compressed_size_and_extended_entry >> 31) & 1),
                    uncompressed_size=uncompressed_size,
                    compression_type=None,
                    comitted=None,
                )

                if entry.extended_entry:
                    compression_type, comitted = struct.unpack(
                        "<HH", self._file.read(4)
                    )
                    entry.compression_type = DBPFCompressionType(compression_type)
                    entry.comitted = comitted

                entries.append(entry)
        except Exception as e:
            raise PackageHandlerException(f"Failed to seek to index offset: {e}")

        return entries
