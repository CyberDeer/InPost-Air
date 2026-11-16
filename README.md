# InPost Air

[![Latest release](https://img.shields.io/github/v/release/CyberDeer/InPost-Air)](https://github.com/CyberDeer/InPost-Air/releases)
[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://hacs.xyz/)
[![Downloads](https://img.shields.io/github/downloads/CyberDeer/InPost-Air/total?label=downloads)](https://github.com/CyberDeer/InPost-Air/releases)

Bring air-quality data from InPost parcel lockers into Home Assistant. Add one or more lockers to see their available pollutant and weather measurements, along with locally calculated air-quality indices.

## At a glance

- **Multiple lockers:** add each locker as a separate device under one integration.
- **Nearby selection:** find supported lockers sorted by distance from your Home Assistant location, or enter a locker code manually.
- **Air quality and weather:** view available particulate matter, gases, temperature, humidity, and pressure.
- **Air-quality indices:** calculate Polish and European index categories from recorded sensor history.
- **No InPost account required:** data comes from InPost's public points API.

> [!IMPORTANT]
> Not every InPost parcel locker provides air-quality data. Available measurements can also differ between lockers or change over time.

## Requirements

- Home Assistant **2025.12.4 or newer**.
- An internet connection to InPost's API.
- At least one InPost parcel locker with air-quality data.

## Installation

### HACS

1. Install [HACS](https://hacs.xyz/) if you haven't already.
2. In Home Assistant, open **HACS**, search for **InPost Air**, and select it.
3. Select **Download**, then restart Home Assistant.

If the integration is not listed, add `https://github.com/CyberDeer/InPost-Air` under **HACS → ⋮ → Custom repositories**, select **Integration**, and then download it.

### Manual

1. Download the [latest release](https://github.com/CyberDeer/InPost-Air/releases/latest).
2. Copy the `inpost_air` integration folder into your Home Assistant configuration directory so that its manifest is at:

   ```text
   <config>/custom_components/inpost_air/manifest.json
   ```

3. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & services → Add integration** and search for **InPost Air**.
2. Set up the integration, then open its integration page and select **Add parcel locker**.
3. Choose a locker from the distance-sorted list, or enter its code, such as `AJE01BAPP`.
4. Repeat **Add parcel locker** to add more lockers.

> [!NOTE]
> The locker list is sorted by distance from Home Assistant's configured latitude and longitude. It includes lockers for which InPost reports an air-quality index.

Manual entry is available for lockers not shown in the list; the integration checks whether air data is available before adding one.

## Sensors

Each locker becomes a device. The integration creates measurement entities for the data available when the locker is set up:

| Sensor | Description | Unit |
| --- | --- | --- |
| PM1, PM2.5, PM4, PM10 | Particulate matter concentrations | µg/m³ |
| NO₂, O₃ | Nitrogen dioxide and ozone concentrations | µg/m³ |
| PM2.5 norm, PM10 norm | Percentage of the WHO reference limit returned by the API, when available | % |
| Temperature | Air temperature | °C |
| Humidity | Relative humidity | % |
| Pressure | Atmospheric pressure | hPa |

### Air-quality indices

The integration also creates a **Polish Air Quality Index** and a **European Air Quality Index** sensor for each locker. These are calculated locally from available PM2.5, PM10, NO₂, and O₃ history, using the worst available pollutant category. They are not the index returned by InPost's API.

The Polish index uses the previous hour of recorded values. The European index uses the previous 24 hours for particulate matter and the previous hour for gases. These calculations depend on Home Assistant's Recorder history, so they may be unavailable until readings have been recorded. They are based on the linked index scales and may differ from official published indices.

- [European Air Quality Index](https://www.eea.europa.eu/themes/air/air-quality-index)
- [Polish Air Quality Index](https://powietrze.gios.gov.pl/pjp/content/health_informations)

## Troubleshooting

- **A locker isn't in the list:** enter its code manually. The list only includes lockers with a non-null air-quality index in the points API.
- **The locker has no air-quality data:** not all lockers provide readings. Availability can change; try another locker or try again later. A temporary API problem can also prevent validation.
- **Sensors are unavailable:** check your internet connection and the Home Assistant logs. The integration depends on InPost's API.
- **An air-quality index has no value:** check that relevant pollutant entities have data and are included in Recorder history.

For bugs and feature requests, [open an issue](https://github.com/CyberDeer/InPost-Air/issues).

## Development

The repository includes a [dev container](https://containers.dev/) with the development environment and recommended VS Code extensions. Open the repository in the container to install dependencies automatically.

Press **F5** in VS Code to launch Home Assistant with the debugger. Additional launch configurations are available for testing specific Home Assistant versions.

Run the tests that don't call the live InPost API with:

```bash
uv run pytest -m "not api"
```
