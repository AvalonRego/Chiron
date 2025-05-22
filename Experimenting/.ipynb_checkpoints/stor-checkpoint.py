"""Module containing all the storage interfaces for collections."""
from __future__ import annotations

import logging
import os
import shutil
import uuid

from abc import ABC, abstractmethod
from enum import Enum
from subprocess import call
from typing import Dict, Generic, List, Optional, Type, TypeVar, Union

import numpy as np
import pandas as pd
import pandera as pa

from ananke.configurations.collection import (
    HDF5StorageConfiguration,
    StorageConfiguration, MemoryStorageConfiguration,
)
from ananke.configurations.events import Interval
from ananke.models.detector import Detector
from ananke.models.event import Hits, RecordIds, Records, Sources
from ananke.models.interfaces import DataFrameFacade
from ananke.schemas.event import FullRecordSchema, RecordIdsTypes_, TypesTypes_


CollectionStorageConfiguration_ = TypeVar(
    "CollectionStorageConfiguration_", bound=StorageConfiguration
)
DataFrameFacade_ = TypeVar("DataFrameFacade_", bound=DataFrameFacade)


# TODO: Implement Configuration Saving
# TODO: Implement Deletion


class AbstractCollectionStorage(ABC, Generic[CollectionStorageConfiguration_]):
    """Interface for all Collection Storage interfaces."""

    def __init__(self, configuration: CollectionStorageConfiguration_):
        """Constructor of the Collection Storage.

        Args:
            configuration: Configuration of the Collection Storage Interface
        """
        self.configuration = configuration
        self._read_only = self.configuration.read_only
        self.logger = logging.getLogger(type(self).__name__)

    def __enter__(self) -> AbstractCollectionStorage:
        """Open storage connection on enter."""
        return self.open()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Close storage connection on exit."""
        self.close()

    @abstractmethod
    def open(self) -> AbstractCollectionStorage:
        """Opens storage connection."""
        raise NotImplementedError("Opening Connection not possible.")

    @abstractmethod
    def close(self) -> None:
        """Opens storage connection."""
        raise NotImplementedError("Closing Connection not possible.")

    @abstractmethod
    def get_detector(self) -> Optional[Detector]:
        """Gets the detector of the current collection.

        Returns:
            Detector of collection or None if empty.
        """
        raise NotImplementedError("Get detector is not implemented")

    @abstractmethod
    def set_detector(self, detector: Detector, append: bool = False) -> None:
        """Sets the detector for current storage.

        Args:
            detector: Detector to set
            append: Append to existing detector
        """
        raise NotImplementedError("Set detector is not implemented")

    @abstractmethod
    def del_detector(self) -> None:
        """Deletes detector of collection storage."""
        raise NotImplementedError("Delete detector is not implemented")

    @abstractmethod
    def get_records(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> Optional[Records]:
        """Gets the records of the current collection.

        Args:
            types: Type of records to get
            record_ids: record_ids to pick
            interval: only records in interval

        Returns:
            Records of collection or None if empty.
        """
        raise NotImplementedError("Get records is not implemented")

    @abstractmethod
    def set_records(
        self,
        records: Records,
        append: bool = True,
    ) -> None:
        """Sets the records for current storage.

        Args:
            records: Records to set
            append: Append to existing detector
        """
        raise NotImplementedError("Set records is not implemented")

    @abstractmethod
    def del_records(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> None:
        """Deletes records of collection storage.

        Args:
            types: Type of records to get
            record_ids: record_ids to pick
            interval: only records in interval
        """
        raise NotImplementedError("Delete records is not implemented")

    @abstractmethod
    def get_hits(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> Optional[Hits]:
        """Gets the hits of the current collection.

        Args:
            types: Type of hits to get
            record_ids: record_ids to pick
            interval: only hits in interval

        Returns:
            Hits of collection or None if empty.
        """
        raise NotImplementedError("Get hits is not implemented")

    @abstractmethod
    def set_hits(
        self,
        hits: Hits,
        append: bool = True,
    ) -> None:
        """Sets the hits for current storage.

        Args:
            hits: Hits to set
            append: Append to existing detector
        """
        raise NotImplementedError("Set hits is not implemented")

    @abstractmethod
    def del_hits(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> None:
        """Deletes hits of collection storage.

        Args:
            types: Type of hits to get
            record_ids: record_ids to pick
            interval: only hits in interval
        """
        raise NotImplementedError("Delete hits is not implemented")

    @abstractmethod
    def get_sources(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> Optional[Sources]:
        """Gets the sources of the current collection.

        Args:
            types: Type of sources to get
            record_ids: record_ids to pick
            interval: only sources in interval

        Returns:
            Sources of collection or None if empty.
        """
        raise NotImplementedError("Get sources is not implemented")

    @abstractmethod
    def set_sources(
        self,
        sources: Sources,
        append: bool = True,
    ) -> None:
        """Sets the sources for current storage.

        Args:
            sources: Sources to set
            append: Append to existing detector
        """
        raise NotImplementedError("Set sources is not implemented")

    @abstractmethod
    def del_sources(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> None:
        """Deletes sources of collection storage.

        Args:
            types: Type of sources to get
            record_ids: record_ids to pick
            interval: only sources in interval
        """
        raise NotImplementedError("Delete sources is not implemented")

    @abstractmethod
    def get_next_record_ids(self, n: int = 1) -> List[int]:
        """Gets n next record ids for generation.

        Args:
            n: Number of record ids to generate

        Returns:
            List of integers
        """
        raise NotImplementedError("Get next record ids not implemented")

    @abstractmethod
    def delete(self) -> None:
        """Deletes current collection."""
        raise NotImplementedError("Delete collection is not implemented")

    def get_record_ids_with_hits(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> pd.Series:
        """Gets all record ids with hits.

        Args:
            types: Type of sources to get
            record_ids: record_ids to pick
            interval: only sources in interval

        Returns:
            Pandas Series containing all record ids
        """
        raise NotImplementedError("Get record ids with hits is not implemented")

    def get_record_ids_with_sources(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> pd.Series:
        """Gets all record ids with hits.

        Args:
            types: Type of sources to get
            record_ids: record_ids to pick
            interval: only sources in interval

        Returns:
            Pandas Series containing all record ids
        """
        raise NotImplementedError("Get record ids with sources is not implemented")

    def optimize(self):
        """Optimizes storage, if optimizable."""
        pass


class StorageKeys(Enum):
    """Enum containing keys for the collection file."""

    RECORDS = "records"
    HITS = "hits"
    SOURCES = "sources"
    DETECTOR = "detector"

    def __str__(self) -> str:
        """To string coercion.

        Returns:
            String representation of the value
        """
        return str(self.value)

class MemoryCollectionStorage(AbstractCollectionStorage[MemoryStorageConfiguration]):

    def __init__(self, configuration: HDF5StorageConfiguration):
        """Constructor of HDF5 collection storage."""
        super(MemoryCollectionStorage, self).__init__(configuration=configuration)
        self.__store = None
        self.__is_open = False

    def open(self) -> MemoryCollectionStorage:
        if self.__store is None:
            self.__store = {}
        elif not self.__is_open:
            self.__is_open = True

        return self

    def close(self) -> None:
        self.__is_open = False

    def __get_data(self, key: StorageKeys):
        logging.debug(
            "Get key {}".format(key)
        )

    def get_detector(self) -> Optional[Detector]:
        pass

    def set_detector(self, detector: Detector, append: bool = False) -> None:
        pass

    def del_detector(self) -> None:
        pass

    def get_records(
            self,
            types: TypesTypes_ = None,
            record_ids: RecordIdsTypes_ = None,
            interval: Optional[Interval] = None
            ) -> Optional[Records]:
        pass

    def set_records(self, records: Records, append: bool = True) -> None:
        pass

    def del_records(
            self,
            types: TypesTypes_ = None,
            record_ids: RecordIdsTypes_ = None,
            interval: Optional[Interval] = None
            ) -> None:
        pass

    def get_hits(
            self,
            types: TypesTypes_ = None,
            record_ids: RecordIdsTypes_ = None,
            interval: Optional[Interval] = None
            ) -> Optional[Hits]:
        pass

    def set_hits(self, hits: Hits, append: bool = True) -> None:
        pass

    def del_hits(
            self,
            types: TypesTypes_ = None,
            record_ids: RecordIdsTypes_ = None,
            interval: Optional[Interval] = None
            ) -> None:
        pass

    def get_sources(
            self,
            types: TypesTypes_ = None,
            record_ids: RecordIdsTypes_ = None,
            interval: Optional[Interval] = None
            ) -> Optional[Sources]:
        pass

    def set_sources(self, sources: Sources, append: bool = True) -> None:
        pass

    def del_sources(
            self,
            types: TypesTypes_ = None,
            record_ids: RecordIdsTypes_ = None,
            interval: Optional[Interval] = None
            ) -> None:
        pass

    def get_next_record_ids(self, n: int = 1) -> List[int]:
        pass

    def delete(self) -> None:
        pass

    def get_record_ids_with_hits(
            self,
            types: TypesTypes_ = None,
            record_ids: RecordIdsTypes_ = None,
            interval: Optional[Interval] = None
            ) -> pd.Series:
        pass

    def get_record_ids_with_sources(
            self,
            types: TypesTypes_ = None,
            record_ids: RecordIdsTypes_ = None,
            interval: Optional[Interval] = None
            ) -> pd.Series:
        pass


class HDF5CollectionStorage(AbstractCollectionStorage[HDF5StorageConfiguration]):
    """Implementation for collection storage using HDF5 file format."""

    def __init__(self, configuration: HDF5StorageConfiguration):
        """Constructor of HDF5 collection storage."""
        super(HDF5CollectionStorage, self).__init__(configuration=configuration)
        self.__store = None
        self.data_path = self.configuration.data_path

    @property
    def store(self) -> pd.HDFStore:
        """Gets the HDF5 store.

        Returns:
            HDF5 store object of storage.
        """
        if self.__store is None or not self.__store.is_open:
            raise ValueError("You forgot to open the storage")

        return self.__store

    def open(self) -> HDF5CollectionStorage:
        """Opens the file io connection.

        Returns:
            Itself to work with open storage
        """
        if self.__store is None:
            self.__store = self.__get_store()
        elif not self.__store.is_open:
            self.__store.open()

        return self

    def close(self) -> None:
        """Closes the file io connection."""
        self.__store.close()

    def delete(self) -> None:
        """Deletes the H5 file."""
        self.close()
        self.__raise_writable()
        if os.path.isfile(self.data_path):
            os.remove(self.data_path)

    def get_detector(self) -> Optional[Detector]:
        """Gets the detector from HDF5.

        Returns:
            Detector from file
        """
        return self.__get_data(key=StorageKeys.DETECTOR, facade_class=Detector)

    def set_detector(
        self,
        detector: Detector,
        append: bool = True,
    ) -> None:
        """Sets the detector to HDF5.

        Args:
            detector: detector to store
            append: append to current one
        """
        return self.__set_data(
            key=StorageKeys.DETECTOR, data=detector, append=append
        )

    def del_detector(self) -> None:
        """Deletes the detector from HDF5."""
        return self.__del_data(
            key=StorageKeys.DETECTOR,
        )

    def get_records(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> Optional[Records]:
        """Gets the records from HDF5.

        Args:
            types: Types to filter by.
            record_ids: Record Ids to filter by.
            interval: Interval to filter by.

        Returns:
            Records matching criteria.
        """
        return self.__get_data(
            key=StorageKeys.RECORDS,
            facade_class=Records,
            types=types,
            record_ids=record_ids,
            interval=interval,
        )

    def set_records(self, records: Records, append: bool = True) -> None:
        """Sets the records to HDF5.

        Args:
            records: records to store
            append: append to current one
        """
        return self.__set_data(
            key=StorageKeys.RECORDS,
            data=records,
            append=append,
            schema=FullRecordSchema,
        )

    def del_records(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> None:
        """Deletes the records matching criteria from HDF5.

        Args:
            types: Types to filter by.
            record_ids: Record Ids to filter by.
            interval: Interval to filter by.
        """
        return self.__del_data(
            key=StorageKeys.RECORDS,
            types=types,
            record_ids=record_ids,
            interval=interval,
        )

    def get_hits(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> Optional[Hits]:
        """Gets the hits from HDF5.

        Args:
            types: Types to filter by.
            record_ids: Record Ids to filter by.
            interval: Interval to filter by.

        Returns:
            Hits matching criteria.
        """
        return self.__get_data(
            key=StorageKeys.HITS,
            facade_class=Hits,
            types=types,
            record_ids=record_ids,
            interval=interval,
        )

    def set_hits(self, hits: Hits, append: bool = True) -> None:
        """Sets the hits to HDF5.

        Args:
            hits: hits to store
            append: append to current one
        """
        return self.__set_data(key=StorageKeys.HITS, data=hits, append=append)

    def del_hits(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> None:
        """Deletes the hits matching criteria from HDF5.

        Args:
            types: Types to filter by.
            record_ids: Record Ids to filter by.
            interval: Interval to filter by.
        """
        return self.__del_data(
            key=StorageKeys.HITS,
            types=types,
            record_ids=record_ids,
            interval=interval,
        )

    def get_sources(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> Optional[Sources]:
        """Gets the sources from HDF5.

        Args:
            types: Types to filter by.
            record_ids: Record Ids to filter by.
            interval: Interval to filter by.

        Returns:
            Sources matching criteria.
        """
        return self.__get_data(
            key=StorageKeys.SOURCES,
            facade_class=Sources,
            types=types,
            record_ids=record_ids,
            interval=interval,
        )

    def set_sources(self, sources: Sources, append: bool = True) -> None:
        """Sets the sources to HDF5.

        Args:
            sources: sources to store
            append: append to current one
        """
        return self.__set_data(
            key=StorageKeys.SOURCES,
            data=sources,
            append=append,
        )

    def del_sources(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> None:
        """Deletes the sources matching criteria from HDF5.

        Args:
            types: Types to filter by.
            record_ids: Record Ids to filter by.
            interval: Interval to filter by.
        """
        return self.__del_data(
            key=StorageKeys.SOURCES,
            types=types,
            record_ids=record_ids,
            interval=interval,
        )

    def __get_store(self) -> pd.HDFStore:
        """Gets the stored hdf object.

        Returns:
            stored hdf object.
        """
        mode = "a"
        if self._read_only:
            # TODO Make bulletproof on update of read only
            mode = "r"

        data_path = self.data_path

        if not os.path.isfile(data_path):
            if mode == "r":
                raise PermissionError(
                    "Cannot create collection in read_only mode. "
                    "Consider changing the configuration."
                )
            dir_path = os.path.dirname(data_path)
            if len(dir_path) > 0:
                os.makedirs(os.path.dirname(data_path), exist_ok=True)

        return pd.HDFStore(
            self.data_path,
            mode=mode,
            complevel=self.configuration.complevel,
            complib=self.configuration.complib,
        )

    def __get_data(
        self,
        key: StorageKeys,
        facade_class: Optional[Type[DataFrameFacade_]] = None,
        types: TypesTypes_ = None,
        record_ids: Optional[Union[int, List[int], pd.Series]] = None,
        interval: Optional[Interval] = None,
        columns: Optional[List[str]] = None,
    ) -> Optional[DataFrameFacade_]:
        """Gets data frame facade from file.

        Args:
            key: Key to get data by
            facade_class: Data frame facade class to instantiate
            types: Record types to filter by
            record_ids: Record ids to filter by
            interval: timeframe to filter by

        Returns:
            Data frame facade containing data or None
        """
        logging.debug(
            "Get {} with key {} at '{}'".format(facade_class, key, self.data_path)
        )

        str_key = str(key)

        wheres = self.__get_wheres(
            types=types, record_ids=record_ids, interval=interval
        )

        try:
            store = self.store
            dfs = [
                store.select(key=str_key, where=where, columns=columns)
                for where in wheres
            ]
            df = pd.concat(dfs)
            del dfs
            if df.empty:
                return None
            # Be careful of side effects
            df.reset_index(drop=True, inplace=True)
            if facade_class is not None:
                facade = facade_class(df=df)
                return facade

            return df
        except KeyError:
            return None

    def __del_data(
        self,
        key: StorageKeys,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> None:
        """Delete rows or the dataframe.

        If no criteria is passed, dataframe is deleted.

        Args:
            key: Key to delete data by
            types: Record types to filter by
            record_ids: Record ids to filter by
            interval: Interval to filter by
        """
        self.__raise_writable()

        str_key = str(key)

        wheres = self.__get_wheres(
            types=types, record_ids=record_ids, interval=interval
        )

        try:
            for where in wheres:
                self.store.remove(key=str_key, where=where)
        except KeyError:
            pass

    def __raise_writable(self) -> None:
        """Raises exception if not writable.

        Raises:
              ValueError: When class not writable
        """
        if self._read_only:
            raise PermissionError("Class cannot write as its opened in read only mode.")

    def __set_data(
        self,
        key: StorageKeys,
        data: DataFrameFacade,
        append: bool = True,
        schema: Optional[Type[pa.SchemaModel]] = None,
    ) -> None:
        """Sets data frame facade to file by a specific key.

        Args:
            key: Key to store data at
            data: Data frame facade to store
            append: Append data to existing
            schema: ensures all columns exist for later appending
        """
        self.__raise_writable()

        str_key = str(key.value)

        if schema is not None:
            types = schema.to_schema().dtypes
            for column, type_ in types.items():
                # TODO: Beautify this
                if column not in data.df.columns:
                    data.df[column] = np.NAN
                if type_.type == np.int64:
                    data.df[column] = data.df[column].fillna(-1)
                data.df[column] = data.df[column].astype(type_.type)

        logging.debug(
            "Set {} with key {} at '{}'".format(type(data), key, self.data_path)
        )

        # TODO: Test override

        self.store.put(
            key=str_key,
            value=data.df,
            format="t",
            append=append,
            complevel=self.configuration.complevel,
            complib=self.configuration.complib,
            data_columns=True,
            index=False,
        )

        # TODO: Make smart and encourage once per append
        if issubclass(type(data), RecordIds):
            self.store.create_table_index(
                key=str_key, columns=["record_id"], optlevel=self.configuration.optlevel
            )

    def __get_wheres(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
        max_wheres_number: int = 30,
    ) -> List[str]:
        """Gets the where clause to select records by.

        As numpy only accepts less than 32 conditions per query, wheres are separated
        in according lists.

        Args:
            types: Types to select
            record_ids: record ids to select
            interval: Interval to filter by
            max_wheres_number: Number of maximal wheres per batch (numpy 32 limit)

        Returns:
            string to be passed to hdf
        """
        type_interval_wheres: List[str] = []
        wheres_number = 0

        if types is not None:
            if not issubclass(type(types), list):
                types = [types]

            if len(types) == 0:

                class NoValueTypeEnum(Enum):
                    NO_VALUE_ENUM = -10000000

                # not a valid type id. should get nothing
                types = [NoValueTypeEnum.NO_VALUE_ENUM]
            wheres_number += len(types)
            types_wheres = [
                "type={}".format(current_type.value) for current_type in types
            ]
            type_interval_wheres.append("({})".format(" | ".join(types_wheres)))

        if interval is not None:
            wheres_number += 2
            type_interval_wheres.append(
                "(time>={} & time<{})".format(interval.start, interval.end)
            )

        if record_ids is not None:
            if isinstance(record_ids, np.ScalarType):
                record_ids = [int(record_ids)]
            if isinstance(record_ids, pd.Series):
                record_ids = record_ids.drop_duplicates().values

            if len(record_ids) == 0:
                # as record_ids should be positive int considered save enough
                record_ids = [-10000000]

            record_ids_wheres = [
                "record_id={}".format(record_id) for record_id in record_ids
            ]

            batch_size = max_wheres_number - wheres_number

            record_ids_wheres_batched = [
                record_ids_wheres[i : i + batch_size]
                for i in range(0, len(record_ids_wheres), batch_size)
            ]
            wheres = []
            for record_ids_batch in record_ids_wheres_batched:
                type_interval_copy = type_interval_wheres.copy()
                type_interval_copy.append("({})".format(" | ".join(record_ids_batch)))
                wheres.append(type_interval_copy)
        else:
            wheres = [type_interval_wheres]

        if len(wheres) == 0:
            wheres = [None]
        else:
            wheres = [
                "({})".format(" & ".join(where)) if len(where) > 0 else None
                for where in wheres
            ]

        return wheres

    def __get_unique_records_ids(
        self,
        key: StorageKeys,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> pd.Series:
        """Gets all unique record ids or empty series if empty.

        Args:
            key: Key to get data by
            types: Record types to filter by
            record_ids: Record ids to filter by
            interval: timeframe to filter by

        Returns:
            Unique record ids or empty series
        """
        record_ids = self.__get_data(
            key=key,
            types=types,
            record_ids=record_ids,
            interval=interval,
            columns=["record_id"],
        )
        if record_ids is None:
            record_ids_series = pd.Series([], dtype="int64")
        else:
            record_ids_series = record_ids["record_id"].drop_duplicates()
        return record_ids_series

    def get_next_record_ids(self, n: int = 1) -> List[int]:
        """Generates an auto increment based of the highest current record id.

        Args:
            n: Number of record ids to be generated

        Returns:
            List of integer ids
        """
        record_ids = self.__get_unique_records_ids(StorageKeys.RECORDS)
        if len(record_ids) == 0:
            start = 0
        else:
            start = record_ids.max() + 1
        return list(range(start, start + n))

    def get_record_ids_with_hits(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> pd.Series:
        """Gets all unique record ids of records with hits or empty series if empty.

        Args:
            types: Record types to filter by
            record_ids: Record ids to filter by
            interval: timeframe to filter by

        Returns:
            Unique record ids or empty series of records with hits
        """
        return self.__get_unique_records_ids(
            StorageKeys.HITS, types=types, record_ids=record_ids, interval=interval
        )

    def get_record_ids_with_sources(
        self,
        types: TypesTypes_ = None,
        record_ids: RecordIdsTypes_ = None,
        interval: Optional[Interval] = None,
    ) -> pd.Series:
        """Gets all unique record ids of records with sources or empty series if empty.

        Args:
            types: Record types to filter by
            record_ids: Record ids to filter by
            interval: timeframe to filter by

        Returns:
            Unique record ids or empty series of records with sources
        """
        return self.__get_unique_records_ids(
            StorageKeys.SOURCES,
            types=types,
            record_ids=record_ids,
            interval=interval,
        )

    def optimize(self) -> None:
        """Optimize HDF5 Storage by recompressing and recreating indices."""
        dir = os.path.dirname(self.data_path)
        self.logger.info("Starting to optimize HDF5.")
        tmp_file = os.path.join(dir, "{}.h5".format(str(uuid.uuid4())))
        indices_to_create_index = [
            StorageKeys.HITS,
            StorageKeys.SOURCES,
            StorageKeys.RECORDS,
        ]
        self.logger.debug("Starting to recreate indices.")
        file_keys = self.store.keys()
        for index in indices_to_create_index:
            current_index = str(index)
            if current_index in file_keys:
                self.store.create_table_index(
                    key=current_index,
                    columns=["record_id"],
                    optlevel=self.configuration.optlevel,
                )
        self.logger.debug("Finished recreating indices.")
        self.close()
        try:
            self.logger.debug("Starting to ptrepack files.")
            command = [
                "ptrepack",
                "-o",
                "--chunkshape=auto",
                "--propindexes",
                "--complevel={}".format(self.configuration.complevel),
                "--complib={}".format(self.configuration.complib),
                self.data_path,
                tmp_file,
            ]
            call(command)
            os.remove(self.data_path)
            shutil.move(tmp_file, self.data_path)
            self.logger.debug("Finished to ptrepack files.")
        except:  # noqa: E722
            logging.warning("PTRepack not working. Skipping compression")
        self.open()
        self.logger.info("Finished to optimize HDF5.")


class StorageFactory:
    """Class as factory for collection storages."""

    #: Mapping from configuration to actual storage class
    configuration_mapping: Dict[
        Type[StorageConfiguration], Type[AbstractCollectionStorage]
    ] = {HDF5StorageConfiguration: HDF5CollectionStorage}

    @classmethod
    def create(cls, configuration: StorageConfiguration) -> AbstractCollectionStorage:
        """Takes a configuration for a storage and returns according storage class.

        Args:
            configuration: Configuration for current storage

        Returns:
            Collection storage to get and retrieve data from
        """
        for configuration_type in cls.configuration_mapping.keys():
            if isinstance(configuration, configuration_type):
                return cls.configuration_mapping[configuration_type](configuration)

        raise ValueError("Configuration type '{}' is not supported")