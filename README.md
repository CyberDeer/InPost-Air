# InPost Air
[![landroid_cloud](https://img.shields.io/github/v/release/cyberdeer/inpost-air.svg?include_prereleases&label=Current%20release)](https://github.com/CyberDeer/InPost-Air) 
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![downloads](https://img.shields.io/github/downloads/cyberdeer/inpost-air/total?label=Total%20downloads)](https://github.com/CyberDeer/InPost-Air)

This component has been created to be used with Home Assistant.

### Installation:

#### HACS

- Ensure that HACS is installed.
- Add custom repository.
- Search for and install the "InPost Air" integration.
- Restart Home Assistant.
- Go to Integrations and add the InPost Air integration

#### Manual installation

- Download the latest release.
- Unpack the release and copy the custom_components/inpost_air directory into the custom_components directory of your Home Assistant installation.
- Restart Home Assistant.
- Go to Integrations and add the InPost Air integration

### Entities & Services

**This integration will set up the following platforms.**

Platform | Entity | Description
-- | -- | --
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_no2` | NO2 concentration
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_o3` | O3 concentration
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_pm1` | PM1 concentration
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_pm10` | PM10 concentration
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_pm10_norm` | PM10 concentration (normalized)
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_pm25` | PM2.5 concentration
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_pm25_norm` | PM2.5 concentration (normalized)
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_pm4` | PM4 concentration
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_pressure` | Pressure
`sensor` | `parcel_locker_[YOUR_PARCEL_ID]_temperature` | Temperature

