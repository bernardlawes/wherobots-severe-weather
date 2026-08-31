"""
Severe Weather Exposure for Critical Power Infrastructure

Parameterized Wherobots job that identifies power infrastructure assets
intersecting National Weather Service severe-weather warning polygons.

Workflow:
    1. Load NOAA warnings and Overture power infrastructure
    2. Pre-filter both datasets to the selected regions
    3. Identify asset-warning exposure with ST_Intersects
    4. Persist results to managed Havasu/Iceberg
"""

import argparse
import time

from sedona.spark import SedonaContext
from pyspark.sql.functions import col, expr, lit, current_timestamp
from pyspark.storagelevel import StorageLevel


def parse_args():
    """Parse command-line parameters for the exposure analysis."""

    parser = argparse.ArgumentParser(
        description="Analyze severe-weather exposure for power infrastructure."
    )

    parser.add_argument(
        "--regions",
        required=True,
        help="Comma-separated Overture region codes, e.g. US-IL or US-IL,US-IN",
    )

    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="NWS warning year to analyze (default: 2026)",
    )

    parser.add_argument(
        "--warning-types",
        default="SV,TO",
        help="Comma-separated NWS phenomena (default: SV,TO)",
    )

    parser.add_argument(
        "--asset-classes",
        default="power_tower,power_line,substation,generator",
        help="Comma-separated Overture power infrastructure classes",
    )

    # add an output table to manage Iceberg output in org_catalog.severe_weather namespace
    parser.add_argument(
        "--output-table",
        default="org_catalog.severe_weather.power_infrastructure_exposure",
        help=(
            "Fully qualified managed Iceberg output table "
            "(default: org_catalog.severe_weather.power_infrastructure_exposure)"
        ),
    )

    return parser.parse_args()



"""
parse args
validate inputs
initialize Sedona
load source tables
validate regions
spatially pre-filter
count + time
asset-warning join
count + time
write Havasu/Iceberg
print run summary
"""

def main():
    job_start = time.perf_counter()
    args = parse_args()

    regions = [x.strip() for x in args.regions.split(",") if x.strip()]
    warning_types = [x.strip() for x in args.warning_types.split(",") if x.strip()]
    asset_classes = [x.strip() for x in args.asset_classes.split(",") if x.strip()]

    if not regions:
        raise ValueError("At least one region is required.")

    if not warning_types:
        raise ValueError("At least one warning type is required.")

    if not asset_classes:
        raise ValueError("At least one asset class is required.")
    
    if args.year < 2000 or args.year > 2100:
        raise ValueError(f"Unexpected analysis year: {args.year}")

    print("=== Severe Weather Power Infrastructure Exposure ===")
    print(f"Regions: {regions}")
    print(f"Year: {args.year}")
    print(f"Warning types: {warning_types}")
    print(f"Asset classes: {asset_classes}")
    print(f"Output table: {args.output_table}")

    # Initialize Apache Sedona
    config = SedonaContext.builder().getOrCreate()
    sedona = SedonaContext.create(config)

    print("SedonaContext initialized successfully.")



    """ ------------------------------------------------------------
        Load data from WherobotsDB tables for the exposure analysis.
        ------------------------------------------------------------
    """
    
    regions_sql = ", ".join(f"'{region}'" for region in regions)
    warning_types_sql = ", ".join(f"'{warning_type}'" for warning_type in warning_types)
    asset_classes_sql = ", ".join(f"'{asset_class}'" for asset_class in asset_classes)

    print("Loading selected state/region boundaries...")

    regions_df = sedona.sql(
        f"""
        SELECT
            id,
            names.primary AS region_name,
            region AS region_code,
            geometry
        FROM wherobots_open_data.overture_maps_foundation.divisions_division_area
        WHERE country = 'US'
          AND subtype = 'region'
          AND admin_level = 1
          AND class = 'land'
          AND region IN ({regions_sql})
        """
    )

    #print(f"Matched regions: {regions_df.count()}")
    matched_region_count = regions_df.count()
    print(f"Matched regions: {matched_region_count}")

    if matched_region_count != len(regions):
        raise ValueError(
            f"Expected {len(regions)} region(s), but matched {matched_region_count}. "
            f"Check region codes: {regions}"
        )

    print("Loading severe-weather warnings...")

    warnings_df = sedona.sql(
        f"""
        SELECT
            PRODUCT_ID,
            PHENOM,
            ISSUED,
            EXPIRED,
            WINDTAG,
            HAILTAG,
            TORNADOTAG,
            DAMAGETAG,
            IS_EMERGENCY,
            geometry
        FROM wherobots_open_data.noaa.nws_watch_warnings
        WHERE VTEC_YEAR = {args.year}
          AND PHENOM IN ({warning_types_sql})
          AND SIG = 'W'
        """
    )

    print("Loading selected power infrastructure classes...")

    power_df = sedona.sql(
        f"""
        SELECT
            id AS asset_id,
            class AS asset_class,
            names.primary AS asset_name,
            geometry
        FROM wherobots_open_data.overture_maps_foundation.base_infrastructure
        WHERE subtype = 'power'
          AND class IN ({asset_classes_sql})
        """
    )


    """ 
    1 Geographic pre-filtering reduces the number of geometries passed to
    2 the final spatial join. Deduplication prevents warnings or assets that
    3 cross multiple selected regions from producing duplicate records.
    """

    filter_start = time.perf_counter()
    print("Filtering warnings to selected regions...")

    """
    regional_warnings_df = (
        warnings_df.alias("w")
        .join(
            regions_df.alias("r"),
            expr("ST_Intersects(w.geometry, r.geometry)")
        )
        .select("w.*")
        .dropDuplicates(["PRODUCT_ID"])
    )
    """

    # Cache spatial results because subsequent count and write actions would
    # otherwise recompute the joins.
    regional_warnings_df = (
        warnings_df.alias("w")
        .join(
            regions_df.alias("r"),
            expr("ST_Intersects(w.geometry, r.geometry)")
        )
        .select("w.*")
        .dropDuplicates(["PRODUCT_ID"])
        .persist(StorageLevel.MEMORY_AND_DISK)
    )

    #print(f"Regional warnings: {regional_warnings_df.count()}")
    regional_warning_count = regional_warnings_df.count()
    print(f"Regional warnings: {regional_warning_count:,}")

    print("Filtering power infrastructure to selected regions...")

    """
    regional_power_df = (
        power_df.alias("a")
        .join(
            regions_df.alias("r"),
            expr("ST_Intersects(a.geometry, r.geometry)")
        )
        .select("a.*")
        .dropDuplicates(["asset_id"])
    )
    """

    regional_power_df = (
        power_df.alias("a")
        .join(
            regions_df.alias("r"),
            expr("ST_Intersects(a.geometry, r.geometry)")
        )
        .select("a.*")
        .dropDuplicates(["asset_id"])
        .persist(StorageLevel.MEMORY_AND_DISK)
    )

    #print(f"Regional power assets: {regional_power_df.count()}")
    regional_power_count = regional_power_df.count()
    print(f"Regional power assets: {regional_power_count:,}")

    filter_elapsed = time.perf_counter() - filter_start
    print(f"Geographic filtering time: {filter_elapsed:.1f} seconds")

    """ ------------------------------------------------------------
        Add the core exposure join — this is the operationalized version of the analysis from your notebook.
        ------------------------------------------------------------
    """
    exposure_start = time.perf_counter()
    print("Calculating asset-warning exposures...")

    exposure_df = (
        regional_power_df.alias("a")
        .join(
            regional_warnings_df.alias("w"),
            expr("ST_Intersects(a.geometry, w.geometry)")
        )
        .select(
            lit(",".join(regions)).alias("analysis_regions"),
            lit(args.year).alias("analysis_year"),
            current_timestamp().alias("run_timestamp"),

            col("a.asset_id"),
            col("a.asset_class"),
            col("a.asset_name"),
            col("a.geometry").alias("asset_geometry"),
            col("w.PRODUCT_ID").alias("warning_id"),
            col("w.PHENOM").alias("warning_type"),
            col("w.ISSUED").alias("warning_issued"),
            col("w.EXPIRED").alias("warning_expired"),
            col("w.WINDTAG").alias("wind_tag"),
            col("w.HAILTAG").alias("hail_tag"),
            col("w.TORNADOTAG").alias("tornado_tag"),
            col("w.DAMAGETAG").alias("damage_tag"),
            col("w.IS_EMERGENCY").alias("is_emergency"),
        )
        # enable persistence to avoid recomputation of the spatial join during the job run. This is especially important for the exposure_df, which is the result of a spatial join and can be expensive to compute.
        .persist(StorageLevel.MEMORY_AND_DISK)
    )

    exposure_count = exposure_df.count()


    """ ------------------------------------------------------------
        Add the persistence step to write the exposure_df to the specified Iceberg table
        This gives us idempotent reruns at the output-table level
        ------------------------------------------------------------
    """


    print(f"Asset-warning exposures: {exposure_count:,}")
    exposure_elapsed = time.perf_counter() - exposure_start
    print(f"Exposure analysis time: {exposure_elapsed:.1f} seconds")

    # Add the persistence step to write the exposure_df to the specified Iceberg table
    print(f"Writing exposure results to: {args.output_table}")


    #sedona.sql("CREATE DATABASE IF NOT EXISTS org_catalog.severe_weather")

    # Parameterizing the database creation - rather than hardcoding the catalog and database, we can 
    # parse the output_table parameter to get them dynamically

    output_parts = args.output_table.split(".")

    if len(output_parts) != 3:
        raise ValueError(
            "Output table must use the format catalog.database.table, "
            f"got: {args.output_table}"
        )

    output_catalog, output_database, _ = output_parts

    sedona.sql(
        f"CREATE DATABASE IF NOT EXISTS {output_catalog}.{output_database}"
    )

    write_start = time.perf_counter()

    (   
        exposure_df.writeTo(args.output_table)
        .using("havasu.iceberg")
        .createOrReplace()
    )

    write_elapsed = time.perf_counter() - write_start

    total_elapsed = time.perf_counter() - job_start

    """ -------------------------------------------------------
        # Each POC run represents the complete result for the supplied parameters.
        # Replacement avoids duplicate asset-warning records on reruns. A production
        # workflow could instead retain history using partitions, snapshots, or MERGE.
        -------------------------------------------------------
    """
    print("Exposure table written successfully.")


    # Release cached Spark DataFrames now that the output has been persisted
    # Because the scale test records intermediate counts before the final write, I persisted the expensive spatial results with MEMORY_AND_DISK so Spark wouldn't recompute the same joins for each action.

    exposure_df.unpersist()
    regional_power_df.unpersist()
    regional_warnings_df.unpersist()

    print("\n=== Run Summary ===")
    print(f"Regions: {len(regions)}")
    #print(f"Regional warnings: {regional_warnings_df.count():,}")
    #print(f"Regional power assets: {regional_power_df.count():,}")
    print(f"Regional warnings: {regional_warning_count:,}")
    print(f"Regional power assets: {regional_power_count:,}")
    print(f"Asset-warning exposures: {exposure_count:,}")
    print(f"Geographic filtering time: {filter_elapsed:.1f} seconds")
    print(f"Exposure analysis time: {exposure_elapsed:.1f} seconds")
    print(f"Output write time: {write_elapsed:.1f} seconds")
    print(f"Total job time: {total_elapsed:.1f} seconds")


if __name__ == "__main__":
    main()