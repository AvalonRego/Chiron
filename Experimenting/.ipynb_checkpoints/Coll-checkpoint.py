from __future__ import annotations
import time

import logging
logging.basicConfig(level=logging.INFO)
import warnings

from enum import Enum
from typing import List, Optional, Type, TypeVar, Union

import numpy as np
import pandas as pd

from ananke.configurations.collection import (
    ExportConfiguration,
    MergeConfiguration,
    StorageConfiguration,
)
from ananke.configurations.events import (
    EventRedistributionMode,
    Interval,
    RedistributionConfiguration,
)
from ananke.models.event import Hits, RecordStatistics, Sources
from ananke.models.interfaces import DataFrameFacade
from ananke.schemas.event import EventType, Types
from ananke.services.collection.exporters import AbstractCollectionExporter
from ananke.services.collection.importers import AbstractCollectionImporter
from ananke.services.collection.storage import AbstractCollectionStorage, StorageFactory
from tables import NaturalNameWarning, PerformanceWarning
from tqdm import tqdm


class CollectionKeys(str, Enum):
    """Enum containing keys for the collection file."""

    RECORDS = "records"
    HITS = "hits"
    SOURCES = "sources"
    DETECTOR = "detector"


DataFrameFacade_ = TypeVar("DataFrameFacade_", bound=DataFrameFacade)


class Collection:
    """Collection storage facade for common interface."""

    def __init__(self, configuration: StorageConfiguration) -> None:
        """Constructor of collection."""
        self.storage = StorageFactory.create(configuration)
        self.logger = logging.getLogger(self.__class__.__name__)

    def __enter__(self) -> AbstractCollectionStorage:
        """Enters the storage (opens it) and returns it as context variable.

        Returns:
            Storage as context variable
        """
        return self.storage.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exits the storage (closes it)."""
        self.storage.__exit__(exc_type, exc_val, exc_tb)

    def open(self) -> AbstractCollectionStorage:
        """Opens the storage and returns it.

        Returns:
            Storage itself
        """
        return self.storage.open()

    def close(self) -> None:
        """Closes the storage."""
        self.storage.close()

    def copy(
        self,
        configuration: StorageConfiguration,
        record_types: Optional[Union[List[Types], Types]] = None,
        record_ids: Optional[Union[int, List[int], pd.Series]] = None,
        interval: Optional[Interval] = None,
        batch_size: int = 100,
    ) -> Collection:
        """Create a copy of current collection with new storage configuration.

        Args:
            configuration: Storage configuration of new collection
            record_types: Types to select
            record_ids: record ids to select
            interval: Interval to filter by
            batch_size: Number of records to do in one batch

        Returns:
            Copy of the collection given by its configuration
        """
        copy = self.__class__(configuration)
        copy.open()
        detector = self.storage.get_detector()
        if detector is not None:
            copy.storage.set_detector(self.storage.get_detector())
        copy_records = self.storage.get_records(
            types=record_types, record_ids=record_ids, interval=interval
        )
        logging.info('Copy')

        if copy_records is None:
            raise ValueError("Cannot copy empty collection")

        copy.storage.set_records(copy_records)

        with tqdm(total=len(copy_records)) as pbar:
            for record_batch in copy_records.iterbatches(batch_size=batch_size):
                record_ids = record_batch.record_ids
                current_sources = self.storage.get_sources(record_ids=record_ids)
                current_hits = self.storage.get_hits(record_ids=record_ids)
                if current_sources is not None:
                    copy.storage.set_sources(current_sources)
                if current_hits is not None:
                    copy.storage.set_hits(current_hits)
                pbar.update(batch_size)
        copy.close()
        return copy

    def import_data(
        self, importer: Type[AbstractCollectionImporter], **kwargs
    ) -> Optional[Collection]:
        """Export the current collection by a given exporter.

        Args:
            importer: importer to choose
            **kwargs: additional arguments for exporter
        """
        importer_instance = importer(collection=self)
        return importer_instance.import_data(**kwargs)

    def export(
        self,
        configuration: ExportConfiguration,
        exporter: Type[AbstractCollectionExporter],
        **kwargs,
    ) -> None:
        """Export the current collection by a given exporter.

        Args:
            configuration: configuration of the exporter.
            exporter: exporter to choose
            **kwargs: additional arguments for exporter
        """
        exporter_instance = exporter(configuration=configuration)
        exporter_instance.export(collection=self, **kwargs)

    def redistribute(
        self,
        redistribution_configuration: RedistributionConfiguration,
        record_types: Optional[Union[List[Types], Types]] = None,
    ) -> None:
        """Redistributes the events records according to the configuration.

        Args:
            redistribution_configuration: Configuration to redistribute by
            record_types: Record type to be redistributed.
        """
        
        start_time=time.time()
        rng = np.random.default_rng(redistribution_configuration.seed)

        if record_types is None:
            record_types = [e.value for e in EventType]
        else:
            record_types = [e.value for e in record_types]
        records = self.storage.get_records()

        mode = redistribution_configuration.mode
        interval = redistribution_configuration.interval
        self.logger.info("Starting to redistribute with mode: {}".format(mode))

        new_differences = []
        self.logger.debug(
            "Redistribution interval: [{},{})".format(interval.start, interval.end)
        )

        if records is None:
            raise ValueError("No records to redistribute")
        self.logger.info(f'preamble took {time.time()-start_time}')

        with tqdm(total=len(records), mininterval=0.5) as pbar:
            for record in records.df.itertuples():
                loop_start_time=time.time()
                current_record_id = getattr(record, "record_id")
                current_record_type = getattr(record, "type")
                current_sources = self.storage.get_sources(record_ids=current_record_id)
                current_hits = self.storage.get_hits(record_ids=current_record_id)
                current_time = getattr(record, "time")
                current_start = interval.start
                current_end = interval.end
                skip_record = False
                self.logger.info(f'line 199 {time.time()-loop_start_time}')

                if current_record_type not in record_types:
                    skip_record = True

                if current_hits is None:
                    skip_record = True
                    self.logger.info(
                        "No hits for event {}. Skipping!".format(current_record_id)
                    )

                if skip_record:
                    new_differences.append(0)
                    continue
                self.logger.info(f'line 213 {time.time()-loop_start_time}')

                if mode != EventRedistributionMode.START_TIME:
                    percentile = None
                    if mode == EventRedistributionMode.CONTAINS_PERCENTAGE:
                        percentile = redistribution_configuration.percentile

                    hits_statistics = current_hits.get_statistics(percentile=percentile)

                    current_min = hits_statistics.min
                    current_max = hits_statistics.max

                    if mode == EventRedistributionMode.CONTAINS_HIT:
                        current_start = interval.start - current_max + current_time
                        current_end = interval.end - current_min + current_time

                    if (
                        mode == EventRedistributionMode.CONTAINS_EVENT
                        or mode == EventRedistributionMode.CONTAINS_PERCENTAGE
                    ):
                        current_length = current_max - current_min
                        current_offset = current_min - current_time
                        current_start = interval.start - current_offset
                        current_end = interval.end - current_offset - current_length
                self.logger.info(f'line 237 {time.time()-loop_start_time}')

                # What happens when the event is having an error
                if current_end < current_start:
                    current_end = current_start + 1

                # What happens when the event is having an error
                new_time = rng.uniform(current_start, current_end)
                new_difference = new_time - current_time
                self.logger.info(f'line 246 {time.time()-loop_start_time}')
                current_hits.add_time(new_difference)
                self.logger.info(f'line 248 {time.time()-loop_start_time}')
                self.storage.del_hits(record_ids=current_record_id) #why is deleting taking so long
                self.logger.info(f'line 250 {time.time()-loop_start_time}')
                self.storage.set_hits(current_hits)
                self.logger.info(f'line 252 {time.time()-loop_start_time}')
                if current_sources is not None:
                    current_sources.add_time(new_difference)
                    self.logger.info(f'line 255 {time.time()-loop_start_time}')
                    self.storage.del_sources(record_ids=current_record_id)
                    self.logger.info(f'line 257 {time.time()-loop_start_time}')
                    self.storage.set_sources(current_sources)
                    self.logger.info(f'line 259 {time.time()-loop_start_time}')

                new_differences.append(new_difference)

                pbar.update()
                self.logger.info(f'for loop took {time.time()-loop_start_time}')

        records.add_time(new_differences)
        self.storage.set_records(records=records, append=False)
        self.logger.info(f'full redistribution took took {time.time()-start_time}')
        self.logger.info("Finished to redistribute with mode: {}".format(mode))

    def append(
        self,
        collection_to_append: Collection,
        with_hits_only: bool = True,
        interval: Optional[Interval] = None,
    ) -> None:
        """Concatenate multiple connections.

        Args:
            collection_to_append: Collection to append to current one.
            with_hits_only: Only take records with hits.
            interval: interval to consider for appending

        Returns:
            A single collection combining the previous ones.
        """
        self.logger.info("Starting to append collection.")

        collection_to_append.open()
        append_detector = collection_to_append.storage.get_detector()
        own_detector = self.storage.get_detector()

        if own_detector is not None and not append_detector == own_detector:
            raise ValueError("Cannot merge two collections with different detectors.")

        if own_detector is None and append_detector is not None:
            self.storage.set_detector(append_detector)

        if with_hits_only:
            records_ids_with_hits = (
                collection_to_append.storage.get_record_ids_with_hits()
            )
            append_records = collection_to_append.storage.get_records(
                record_ids=records_ids_with_hits
            )
        else:
            append_records = collection_to_append.storage.get_records()

        if append_records is not None:
            self.storage.set_records(append_records, append=True)

            with tqdm(total=len(append_records), mininterval=0.5) as pbar:
                for record_batch in append_records.iterbatches(
                    self.storage.configuration.batch_size
                ):
                    current_hits = collection_to_append.storage.get_hits(
                        record_ids=record_batch.record_ids, interval=interval
                    )
                    if current_hits is not None:
                        self.storage.set_hits(current_hits)

                    current_sources = collection_to_append.storage.get_sources(
                        record_ids=record_batch.record_ids, interval=interval
                    )
                    if current_sources is not None:
                        self.storage.set_sources(current_sources)

                    pbar.update(self.storage.configuration.batch_size)
        self.logger.info("Finished to append collection.")

    def drop_no_hit_records(self) -> None:
        """Deletes all the records without hits."""
        logging.info("Dropping no hit records")
        record_ids_with_hits = self.storage.get_record_ids_with_hits()
        if record_ids_with_hits is None:
            record_ids_with_hits = []

        records = self.storage.get_records()
        if records is not None:
            records_ids = records.record_ids
            records_ids_without_hits = records_ids[
                ~records_ids.isin(record_ids_with_hits)
            ]
            self.storage.del_sources(record_ids=records_ids_without_hits)
            self.storage.del_records(record_ids=records_ids_without_hits)
            logging.info("Dropped {} records".format(len(records_ids_without_hits)))

    def get_record_statistics(self) -> Optional[RecordStatistics]:
        """Gets all the statistics added to the current records.

        Returns:
            RecordStatistics enriched by counts and first and last sources and hits.
        """
        records = self.storage.get_records()
        if records is None:
            return None
        hits_counts = []
        sources_counts = []
        first_sources = []
        last_sources = []
        first_hits = []
        last_hits = []
        number_records = len(records)
        empty_hits = 0
        empty_sources = 0
        with tqdm(total=number_records, mininterval=0.5) as pbar:
            for index, record_id in records.record_ids.items():
                record_hits = self.storage.get_hits(record_ids=record_id)
                if record_hits is None:
                    hits_counts.append(0)
                    first_hits.append(np.nan)
                    last_hits.append(np.nan)
                    empty_hits += 1
                else:
                    hits_statistics = record_hits.get_statistics()
                    hits_counts.append(hits_statistics.count)
                    first_hits.append(hits_statistics.min)
                    last_hits.append(hits_statistics.max)
                record_sources = self.storage.get_sources(record_ids=record_id)
                if record_sources is None:
                    sources_counts.append(0)
                    first_sources.append(np.nan)
                    last_sources.append(np.nan)
                    empty_sources += 1
                else:
                    sources_statistics = record_sources.get_statistics()
                    sources_counts.append(sources_statistics.count)
                    first_sources.append(sources_statistics.min)
                    last_sources.append(sources_statistics.max)
                pbar.update()

        df: pd.DataFrame = records.df
        if empty_hits != number_records:
            df["hit_count"] = hits_counts
            df["first_hit"] = first_hits
            df["last_hit"] = last_hits
        if empty_sources != number_records:
            df["source_count"] = sources_counts
            df["first_source"] = first_sources
            df["last_source"] = last_sources

        return RecordStatistics(df=df)

    @classmethod
    def from_merge(cls, merge_configuration: MergeConfiguration) -> Collection:
        """Creates new collection based on merge configuration.

        Args:
            merge_configuration: Merge configuration to build new collection by.

        Returns:
            Merged collection.
        """
        start_time=time.time()
        logging.info("Starting to merge collections with config. ")
        collections = merge_configuration.in_collections
        logging.info(f"time at line 418 : {time.time()-start_time}")
        if len(collections) == 0:
            raise ValueError("No collections passed")
        rng = np.random.default_rng(merge_configuration.seed)
        first_collection = cls(collections[0])
        if merge_configuration.redistribution is not None or len(collections) > 1:
            with first_collection:
                logging.info(f"time at line 424 : {time.time()-start_time}")
                logging.info("Starting to create joined temporary collection.")
                tmp_collection = first_collection.copy(
                    merge_configuration.tmp_collection
                )
                logging.info(f"time at line 429 : {time.time()-start_time}")
        else:
            logging.info(f"time at line 430 : {time.time()-start_time}")
            logging.info("No redistribution else")
            collections[0].read_only = True
            tmp_collection = cls(collections[0])
        logging.info(f"time at line 434 : {time.time()-start_time}")
        if len(collections) > 1:
            tmp_collection.open()
            for sub_collection in collections[1:]:
                sub_collection = cls(configuration=sub_collection)
                tmp_collection.append(collection_to_append=sub_collection)
            tmp_collection.close()
            logging.info(f"time at line 441 : {time.time()-start_time}")
            logging.info("after some for loop")
            logging.info("Finished creating joined temporary collection.")

        if merge_configuration.redistribution is not None:
            tmp_collection.open()
            tmp_collection.redistribute(
                redistribution_configuration=merge_configuration.redistribution
            )
            tmp_collection.close()

        tmp_collection.read_only = True

        tmp_collection.open()
        logging.info("redistribution is none")
        logging.info(f"time at line 392 : {time.time()-start_time}")

        if merge_configuration.content is None:
            logging.info(f"time at line 442 : {time.time()-start_time}")
            logging.info('merge_configuration.content is None')
            new_collection = tmp_collection.copy(merge_configuration.out_collection)
            logging.info(f"time at line 445 : {time.time()-start_time}")
            logging.info('copy time')
        else:
            logging.info(f"time at line 447 : {time.time()-start_time}")
            logging.info('merge_configuration.content is not None')
            new_collection = cls(merge_configuration.out_collection)
            new_collection.open()
            tmp_detector = tmp_collection.storage.get_detector()
            
            if tmp_detector is not None:
                new_collection.storage.set_detector(tmp_detector)
                
            logging.info(f"time at line 454 : {time.time()-start_time}")
            logging.info('merge_configuration.content for loop start')
            
            for content in merge_configuration.content:
                logging.info(
                    "Starting to create {} {} records".format(
                        content.number_of_records, content.primary_type
                    )
                )
                if content.secondary_types is not None:
                    logging.info(
                        "Secondary types: {}".format(
                            ", ".join(
                                [
                                    str(secondary_type.value)
                                    for secondary_type in content.secondary_types
                                ]
                            )
                        )
                    )
                # Collect for duplicate ID
                new_collection_records = new_collection.storage.get_records()
                if new_collection_records is not None:
                    new_collection_record_ids = new_collection_records.record_ids
                else:
                    new_collection_record_ids = []
                # First load all primary records
                if content.number_of_records is not None:
                    number_of_records = content.number_of_records
                else:
                    number_of_records = len(new_collection_records)
                interval = content.interval
                primary_type = content.primary_type
                primary_records = tmp_collection.storage.get_records(types=primary_type)
                if primary_records is None or len(primary_records) < number_of_records:
                    raise ValueError(
                        "Not enough primary records of type {} given".format(
                            primary_type
                        )
                    )

                # Now all secondary records
                secondary_records_list = []
                if content.secondary_types is not None:
                    for secondary_type in content.secondary_types:
                        secondary_records_list.append(
                            tmp_collection.storage.get_records(types=secondary_type)
                        )

                added_record_ids = []
                misses = 0
                misses_break_number = 50
                if content==merge_configuration.content[0]:
                    logging.info(f"time at line 459 : {time.time()-start_time}")
                    logging.info('Time for a bunch of if statements')

                with tqdm(total=number_of_records, mininterval=0.5) as pbar:
                    # TODO: Check Performance
                    logging.info('start of while so might be slow')
                    whilestart=time.time()
                    count=0
                    while (
                        len(added_record_ids) < number_of_records
                        and misses < misses_break_number
                    ):
                        count+=1#############
                        current_primary_record = primary_records.sample(
                            n=1, random_state=rng
                        )
                        current_primary_record_id = (
                            current_primary_record.record_ids.iloc[0]
                        )
                        # First set the primary hits and sources
                        primary_hits = tmp_collection.storage.get_hits(
                            record_ids=current_primary_record_id, interval=interval
                        )

                        current_sources_list: List[Sources] = []
                        current_hits_list: List[Hits] = []

                        # skip primary records without hits
                        if primary_hits is None and content.filter_no_hits:
                            misses += 1
                            continue
                        else:
                            current_hits_list.append(primary_hits)
                            primary_sources = tmp_collection.storage.get_sources(
                                record_ids=current_primary_record_id, interval=interval
                            )
                            if primary_sources is not None:
                                current_sources_list.append(primary_sources)

                        for secondary_records in secondary_records_list:
                            if secondary_records is None:
                                continue
                            current_secondary_record_id = secondary_records.sample(
                                n=1, random_state=rng
                            ).record_ids.iloc[0]

                            current_sources = tmp_collection.storage.get_sources(
                                record_ids=current_secondary_record_id,
                                interval=interval,
                            )
                            current_hits = tmp_collection.storage.get_hits(
                                record_ids=current_secondary_record_id,
                                interval=interval,
                            )
                            if current_hits is not None:
                                current_hits_list.append(current_hits)
                            if current_sources is not None:
                                current_sources_list.append(current_sources)

                        combined_current_sources = Sources.concat(current_sources_list)
                        combined_current_hits = Hits.concat(current_hits_list)

                        if (
                            current_primary_record_id in added_record_ids
                            or current_primary_record_id in new_collection_record_ids
                        ):
                            # TODO: Discuss what happens if record_id already added?
                            new_record_id = new_collection.storage.get_next_record_ids(
                                1
                            )[0]
                            logging.debug(
                                "Record id {} already added: Renaming to {}".format(
                                    current_primary_record_id, new_record_id
                                )
                            )
                        else:
                            new_record_id = current_primary_record_id

                        new_record_id = int(new_record_id)

                        # Set all ids
                        current_primary_record.df["record_id"] = new_record_id
                        combined_current_hits.df["record_id"] = new_record_id

                        new_collection.storage.set_records(
                            records=current_primary_record, append=True
                        )
                        new_collection.storage.set_hits(combined_current_hits)

                        if combined_current_sources is not None:
                            combined_current_sources.df["record_id"] = new_record_id
                            new_collection.storage.set_sources(combined_current_sources)

                        added_record_ids.append(new_record_id)
                        misses = 0

                        pbar.update()
                    logging.info('end of while')
                    logging.info(f"number of iterations: {count}")
                    logging.info(f'took: {time.time()-whilestart} for while loop')

                if misses == misses_break_number:
                    raise ValueError(
                        "Not enough primary records of type {} with hits".format(
                            content.primary_type
                        )
                    )

                logging.info(
                    "Finished to create {} {} records".format(
                        content.number_of_records, content.primary_type
                    )
                )

        tmp_collection.close()

        # TODO: Delete temporary collection
        logging.info("Finished to merge collections with config.")
        return new_collection