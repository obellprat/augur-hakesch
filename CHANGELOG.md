## 0.7.0-dev.2 (2025-11-20)

### Fix

- **frontend**: layout improvements on calculation page

## 0.7.0-dev.1 (2025-11-20)

### Feat

- **frontend**: Reorganization of the Hydrological Calculation Page. All fields below each other and new layout

### Fix

- **API,-NAM**: bug fixing cc_factor on rain in NAM
- **api,ClarkWSL**: bugfixing fraction lists missing items. It is a list
- **ClarkWSL**: Ensure that discharge types are handed over as strings
- **interpolation-koella**: Koella was not correctly passed for the loglog-interpolation without explicitly putting x=20 and x=100
- **api**: Fix for Koella's calculation with the new recurrence periods
- **koella**: Further add tolerance for TB conversion
- **koella**: Change parameters for TB conversion also in the second koella function
- **loglog-int**: fix isclose issue in function
- **loglog-int**: Log-log interpolation is not selecting properly 300 year period
- **koella**: Correct TB conversion parameters

## 0.6.0-dev.1 (2025-11-14)

### Feat

- **api,frontend**: New recurrence periods added (30, 100, 300)
- **api,frontend**: User can get the HADES data in the frontend. Takes the values from the provided netcdf file
- **frontend,api**: Update to clima scenarios of meteoschweiz
- **calibration**: Integrate results of the first calibration in the methods
- **Science**: Add science page, change light background, add marker to precipitation tool

### Fix

- **frontend**: sort results by annuality
- **climate-change-signal**: values were wrong and have adjusted according to new "note for estimating future changes in extreme precipitation return levels" from MeteoSwiss
- **api**: fixes strange bug with pysheds array with sizes of 160000... make the reading window a little bit smaller

## 0.5.0-dev.1 (2025-11-04)

### Feat

- **frontend,api**: climate change instagration
- **api**: faster catchment calculations
- **frontend,-api**: NAM hydrograph implementation

### Fix

- **api**: fixes strange bug with pysheds array with sizes of 160000... make the reading window a little bit smaller
- **TB-convergence**: Adjust parameters for TB convergence in MF and Koella to avoid failing convergence

## 0.4.0-dev.1 (2025-10-23)

### Feat

- **frontend**: Combine annualities and init hydrological processes

### Fix

- **frontend**: welcome text change

## 0.3.1-dev.1 (2025-10-21)

### Feat

- **darkmode-images**: Add functionality to show different images in dark mode as well as the logos

### Fix

- **frontend**: same height for all card-img-top
- **frontend**: fixes bugs in adding new calculations after saving

### Refactor

- **frontend**: Set and hide standard NAM parameters
- **frontend**: hide donation box
- **api,frontend**: small changes in spinner, translation and docker

## 0.3.0-beta.0 (2025-09-15)

### Feat

- **api,frontend**: User can upload his own soil type shapefile
- **api**: Possibility to add custom soil shapefile to calculate cn
- **frontend**: NAM integration into the frontend

## 0.3.0-alpha.1 (2025-09-11)

### Feat

- **api**: Use the Bodeneignungskarte in Switzerland to generate the curve numbers

### Fix

- **api**: Use a_crit 1000 and not 10000 for generating isozones
- **api,frontend**: Better error description, when the calculation is not working
- **api**: Use the correct cumulative length for the calculation and not the maximum length

## 0.3.0-alpha.0 (2025-09-10)

### Feat

- **frontend**: shows a spinner when loading data from database

### Fix

- **frontend**: Calculations cannot be performed if the geodata has not yet been calculated. The user will be informed of this. Fix #41
- **frontend**: The data for the calculations is saved before the calculations are performed
- **api**: change cumulative flow length in project-wide calculation
- **api**: send the Cumulative channel length in km and not in m
- **Additional-changes-to-Fliesszeitverfahren-and-Kölla**: Calculation corrections
- **discharge.py**: calculation corrections for koella and clark-wsl
- **frontend**: after saving calculation-data it was not possible to add other calculations. And fixes the decimal places bug
- **api,frontend**: Enable to download isozone, catchment and branches as tif and geojson

## 0.3.0-dev.5 (2025-08-10)

### Fix

- **api,frontend**: Calculation progress display fix

## 0.3.0-dev.4 (2025-07-28)

### Fix

- **frontend**: Displays an error message if there was an exception in the API functions

## 0.3.0-dev.3 (2025-07-27)

### Feat

- **frontend,api**: integration of clark-wsl calculation

## 0.3.0-dev.2 (2025-07-26)

### Feat

- **frontend**: Display the geodata in project overview
- **frontend**: Show the calculated river network

### Fix

- **frontend**: Frontend starts even the backend is not accessible

## 0.3.0-dev.1 (2025-07-25)

### Feat

- **api,frontend**: integrating version display in frontend and backend
- **frontend**: Show results as Plots

### Fix

- **frontend**: show version in frontend

### Refactor

- **api**: delete unused api calculation files
- **api,frontend**: Previously, semantic versioning was used. Commitizen is more widely used

## 0.2.0 (2025-07-25)

### Feat

- **frontend**: integrated discharge project navigation into main navigation
- **frontend**: Translation
- **frontend, api**: Koella calculation
- **frontend**: delete hydro calculations
- **frontend**: delete hydro calculations
- **api,frontend**: Implementation of Mod Fliesszeitverfahren
- **frontend**: geodata page and creation for hakesch 2 projects
- **api**: prisma integration in fastapi
- **frontend**: Prisma and HAKESCH2 project view
- **api**: updated isozones calculation
- **api**: authentification with keycloak
- **frontend**: User Page with api token
- **frontend**: New Augur frontend
- **frontend**: New Augur frontend
- **frontend**: New Augur frontend
- **api**: implementing isozonation
- **api**: isozones calculation
- **api**: show version in docs
- add automatic versioning

### Fix

- **api**: create all data directories
- add creation of dirs in Taskfile for downloading data
