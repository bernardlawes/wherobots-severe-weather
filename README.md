# Severe Weather Power Infrastructure Exposure

A Wherobots proof of concept that identifies critical power infrastructure exposed to National Weather Service severe-weather warnings.

The workflow combines NOAA NWS warning polygons with Overture Maps infrastructure using Apache Sedona spatial operations, then persists asset-warning exposure records to managed Havasu/Iceberg storage.

## Customer Question

Which critical power assets were exposed to severe thunderstorm and tornado warnings during a selected period, and what warning characteristics can help utility operations teams prioritize those assets?

## Architecture

NOAA NWS Warnings
        +
Overture Power Infrastructure
        |
        v
Geographic Pre-filter
        |
        v
Apache Sedona ST_Intersects
        |
        v
Asset-Warning Exposure Records
        |
        v
Managed Havasu / Iceberg
        |
        +--> Downstream SQL / Analytics
        |
        +--> Exposure Explorer

## Repository Contents

- `notebooks/severe_weather_power_exposure_panel.ipynb` — exploratory analysis and customer-facing results.
- `wherobots_weather_exposure_job.py` — parameterized Wherobots analysis job.
- `submit_wherobots_job.py` — Illinois scale run.
- `submit_wherobots_job_medium.py` — five-state Midwest scale run.
- `submit_wherobots_job_large.py` — larger Midwest scale run.
- `app/` — optional interactive exposure explorer built from persisted job output.

## Job Parameters

The analysis job accepts:

- `--regions` — comma-separated U.S. region codes, e.g. `US-IL,US-IN`
- `--year` — analysis year
- `--warning-types` — NWS phenomena, default `SV,TO`
- `--asset-classes` — infrastructure classes to analyze
- `--output-table` — managed output table

Example:

```text
--regions US-IL \
--year 2026 \
--warning-types SV,TO \
--asset-classes power_tower,power_line,substation,generator \
--output-table org_catalog.severe_weather.power_infrastructure_exposure